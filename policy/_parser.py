# -*- coding: utf-8 -*-
"""
    policy._parser
    ~~~~~~~~~~~~~~~

    Parser for parse policy file.

"""

import re
import logging

from policy import checks
from policy.exceptions import InvalidRuleException

LOG = logging.getLogger(__name__)


def reducer(*tokens):
    """Decorator for reduction methods.

    Arguments are a sequence of tokens, which should trigger running
    this reduction method.
    """

    def wrapper(func):
        # Make sure that we have a list of reducer sequences
        if not hasattr(func, 'reducers'):
            func.reducers = []

        # Add the token to the list of reducer sequences
        func.reducers.append(list(tokens))

        return func

    return wrapper


class ParserMeta(type):
    """Meta class for the :class:`.Parser` class.

    Facilitates identifying reduction methods.
    """

    def __new__(mcs, name: str, bases: tuple, attrs: dict):
        """Create the class.

        Injects the 'reducers' attribute, a list of tuple matching token
        sequences to the name of the corresponding reduction methods.
        """
        reducers = []

        for key, value in attrs.items():
            if not hasattr(value, 'reducers'):
                continue
            for reduction in value.reducers:
                reducers.append((reduction, key))

        attrs['reducers'] = reducers

        return super().__new__(mcs, name, bases, attrs)


class Parser(metaclass=ParserMeta):

    # used for tokenizing the policy language
    _TOKENIZE_RE = re.compile(r'\s+')

    def __init__(self, raise_error: bool):
        self.raise_error = raise_error
        # Internal states
        self.tokens = []
        self.values = []

    def _reduce(self):
        """Perform a greedy reduction of token stream.

        If a reducer method matches, it will be executed, then the
        :meth:`reduce` method will be called recursively to search
        for any more possible reductions.
        """

        for reduction, methname in self.reducers:
            token_num = len(reduction)
            if (len(self.tokens) >= token_num and
                    self.tokens[-token_num:] == reduction):
                # Get the reduction method
                meth = getattr(self, methname)

                # Reduce the token stream
                results = meth(*self.values[-token_num:])

                self.tokens[-token_num:] = [r[0] for r in results]
                self.values[-token_num:] = [r[1] for r in results]

                # Check for any more reductions
                return self._reduce()

    def _shift(self, token, value):
        self.tokens.append(token)
        self.values.append(value)

        self._reduce()

    @property
    def result(self):
        """Obtain the final result of the parse.

        :return: check instance
        :raises ValueError: If the parse failed to reduce to a single result.
        """

        if len(self.values) != 1:
            raise ValueError('Could not parse rule')
        return self.values[0]

    def _parse_check(self, rule):
        """Parse a single base check rule into an appropriate Check object."""

        # Handle the special constant-type checks
        for check_cls in (checks.FalseCheck, checks.TrueCheck):
            check = check_cls()
            if rule == str(check):
                return check

        try:
            kind, match = rule.split(':', 1)
        except Exception:
            if self.raise_error:
                raise InvalidRuleException(rule)
            else:
                LOG.exception('Failed to understand rule %r', rule)
                # If the rule is invalid, we'll fail closed
                return checks.FalseCheck()

        if kind in checks.registered_checks:
            return checks.registered_checks[kind](kind, match)
        elif None in checks.registered_checks:
            return checks.registered_checks[None](kind, match)
        elif self.raise_error:
            raise InvalidRuleException(rule)
        else:
            LOG.error('No handler for matches of kind %r', kind)
            # If the rule is invalid, we'll fail closed
            return checks.FalseCheck()

    def _parse_tokenize(self, rule):
        """Tokenizer for the policy language."""

        for token in self._TOKENIZE_RE.split(rule):
            # Skip empty tokens
            if not token or token.isspace():
                continue

            # Handle leading parens on the token
            clean = token.lstrip('(')
            for i in range(len(token) - len(clean)):
                yield '(', '('

            # If it was only parentheses, continue
            if not clean:
                continue
            else:
                token = clean

            # Handle trailing parens on the token
            clean = token.rstrip(')')
            trail = len(token) - len(clean)

            # Yield the cleaned token
            lowered = clean.lower()
            if lowered in ('and', 'or', 'not'):
                # Special tokens
                yield lowered, clean
            elif clean:
                # Not a special token, but not composed solely of ')'
                if len(token) >= 2 and ((token[0], token[-1]) in
                                        [('"', '"'), ("'", "'")]):
                    # It's a quoted string
                    yield 'string', token[1:-1]
                else:
                    yield 'check', self._parse_check(clean)

            # Yield the trailing parens
            for i in range(trail):
                yield ')', ')'

    def parse(self, rule: str):
        """Parses policy to tree.

        Translate a policy written in the policy language into a tree of
        Check objects.
        """

        # Empty rule means always accept
        if not rule:
            return checks.TrueCheck()

        for token, value in self._parse_tokenize(rule):
            self._shift(token, value)

        try:
            return self.result
        except ValueError:
            LOG.exception('Failed to understand rule %r', rule)
            # Fail closed
            return checks.FalseCheck()

    @reducer('(', 'check', ')')
    @reducer('(', 'and_expr', ')')
    @reducer('(', 'or_expr', ')')
    def _wrap_check(self, _p1, check, _p2):
        """Turn parenthesized expression into a 'check' token"""
        return [('check', check)]

    @reducer('check', 'and', 'check')
    def _make_and_expr(self, check1, _and, check2):
        """Create an 'and_expr'

        Join two checks by the 'and' operator.
        """

        return [('and_expr', checks.AndCheck(check1, check2))]

    @reducer('or_expr', 'and', 'check')
    def _mix_or_and_expr(self, or_expr, _and, check):
        """Modify the case 'A or B and C'

        AND operator's priority is higher than OR operator.
        """

        or_expr, check1 = or_expr.pop_check()
        if isinstance(check1, checks.AndCheck):
            and_expr = check1
            and_expr.add_check(check)
        else:
            and_expr = checks.AndCheck(check1, check)
        return [('or_expr', or_expr.add_check(and_expr))]

    @reducer('and_expr', 'and', 'check')
    def _extend_and_expr(self, and_expr, _and, check):
        """Extend an 'and_expr' by adding another check."""

        return [('and_expr', and_expr.add_check(check))]

    @reducer('check', 'or', 'check')
    @reducer('and_expr', 'or', 'check')
    def _make_or_expr(self, check1, _or, check2):
        """Create an 'or_expr'

        Join two checks by the 'or' operator.
        """

        return [('or_expr', checks.OrCheck(check1, check2))]

    @reducer('or_expr', 'or', 'check')
    def _extend_or_expr(self, or_expr, _or, check):
        """Extend an 'or_expr' by adding another check."""

        return [('or_expr', or_expr.add_check(check))]

    @reducer('not', 'check')
    def _make_not_expr(self, _not, check):
        """Invert the result of a check."""

        return [('check', checks.NotCheck(check))]


def parse_rule(rule: str, raise_error=False):
    """Parses policy to a tree of Check objects."""

    parser = Parser(raise_error)
    return parser.parse(rule)
