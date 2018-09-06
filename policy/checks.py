# -*- coding: utf-8 -*-
"""
    policy.checkers
    ~~~~~~~~~~~~~~~

    Various checkers to check policy.

"""

import abc
import ast
from collections import Iterable

from policy import _utils


registered_checks = {}


class BaseCheck(metaclass=abc.ABCMeta):
    """Abstract base class for Check classes."""

    @abc.abstractmethod
    def __str__(cls):
        """String representation of the check"""
        pass

    @abc.abstractmethod
    def __call__(self, target, cred, enforcer):
        """Triggers if instance of the class is called.

        Performs check. Returns False to reject the access or a
        true value (not necessary True) to accept the access.
        """
        pass


class FalseCheck(BaseCheck):
    """A policy checker that always return ``False`` (disallow) """

    def __str__(self):
        """Return a string representation of this checker."""

        return '!'

    def __call__(self, target, cred, enforcer):
        """Check the policy"""

        return False


class TrueCheck(BaseCheck):
    """A policy checker that always return ``True`` (allow) """

    def __str__(self):
        """Return a string representation of this checker."""

        return '@'

    def __call__(self, target, cred, enforcer):
        """Check the policy"""

        return True


class Check(BaseCheck):

    def __init__(self, kind, match):
        self.kind = kind
        self.match = match

    def __str__(self):
        """Return a string representation of this checker."""

        return '%s:%s' % (self.kind, self.match)


class NotCheck(BaseCheck):

    def __init__(self, rule):
        self.rule = rule

    def __str__(self):
        """Return a string representation of this checker."""

        return 'not %s' % self.rule

    def __call__(self, target, cred, enforcer):
        """Check the policy.

        Returns the logical inverse of the wrapped check.
        """

        return not self.rule(target, cred, enforcer)


class AndCheck(BaseCheck):

    def __init__(self, *rules):
        self.rules = list(rules)

    def __str__(self):
        """Return a string representation of this checker."""

        return '(%s)' % ' and '.join(str(rule) for rule in self.rules)

    def __call__(self, target, cred, enforcer):
        """Check the policy.

        Returns the logical AND of the wrapped checks.
        """

        for rule in self.rules:
            if not rule(target, cred, enforcer):
                return False
        else:
            return True

    def add_check(self, rule):
        """Adds rule to be checked.

        Allow addition of another rule to the list of rules that will
        be checked.

        :return: self
        :rtype: :class:`.AndChecker`
        """

        self.rules.append(rule)


class OrCheck(BaseCheck):

    def __init__(self, *rules):
        self.rules = list(rules)

    def __str__(self):
        """Return a string representation of this checker."""

        return '(%s)' % ' or '.join(str(rule) for rule in self.rules)

    def __call__(self, target, cred, enforcer):
        """Check the policy.

        Returns the logical OR of the wrapped checks.
        """

        for rule in self.rules:
            if rule(target, cred, enforcer):
                return True
        else:
            return False

    def add_check(self, rule):
        """Adds rule to be checked.

        Allow addition of another rule to the list of rules that will
        be checked.

        :return: self
        :rtype: :class:`.AndChecker`
        """

        self.rules.append(rule)

    def pop_check(self):
        """Pops the last checker from the list and returns it.

        :return: self, poped checker
        :rtype: :class:`.OrChecker`, class:`.Checker`
        """

        checker = self.rules.pop()
        return self, checker


def register(name, _callable=None):
    """A decorator used for register custom check.

    :param name: name of check
    :type: str
    :param _callable: check class or a function which return check instance
    :return: _callable or a decorator
    """
    def wrapper(_callable):
        registered_checks[name] = _callable
        return _callable

    # If function or class is given, do the registeration
    if _callable:
        return wrapper(_callable)

    return wrapper


@register('rule')
class RuleCheck(Check):

    def __call__(self, target, creds, enforcer):
        try:
            return enforcer.rules[self.match](target, creds, enforcer)
        except KeyError:
            # We don't have any matching rule; fail closed
            return False


@register('role')
class RoleCheck(Check):
    """Check whether thers is a matched role in the ``creds`` dict."""
    ROLE_ATTRIBUTE = 'roles'

    def __call__(self, target, creds, enforcer):
        try:
            match = self.match % _utils.dict_from_object(target)
        except KeyError:
            # if key not present in target return False
            return False
        roles = _utils.xgetattr(creds, self.ROLE_ATTRIBUTE, None)
        return (match.lower() in (role.lower() for role in roles)
                if roles else False)


@register(None)
class GenericChecker(Check):
    """Check an individual match.

    Matches look like:

        - tenant:%(tanant_id)s
        - role:compute:admin
        - True:%(user.enabled)s
        - 'Member':%(role.name)s
    """

    def _find_in_object(self, test_value, path_segments, match):
        if len(path_segments) == 0:
            return match == str(test_value)

        key, path_segments = path_segments[0], path_segments[1:]
        try:
            test_value = _utils.xgetattr(test_value, key, getitem=True)
        except (KeyError, AttributeError):
            return False
        if (isinstance(test_value, Iterable) and
                not isinstance(test_value, (str, bytes))):
            for val in test_value:
                if self._find_in_object(val, path_segments, match):
                    return True
            else:
                return False
        else:
            return self._find_in_object(test_value, path_segments, match)

    def __call__(self, target, creds, enforcer):
        try:
            match = self.match % _utils.dict_from_object(target)
        except KeyError:
            # if key not present in target return False
            return False
        try:
            test_value = ast.literal_eval(self.kind)
            return match == str(test_value)
        except ValueError:
            pass

        path_segments = self.kind.split('.')
        return self._find_in_object(creds, path_segments, match)
