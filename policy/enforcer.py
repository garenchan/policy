# -*- coding: utf-8 -*-
"""
    policy.enforcer
    ~~~~~~~~~~~~~~~

    Policy enforcer.

"""

import json
import threading
import logging

from policy import checks, _parser, _cache
from policy.exceptions import PolicyNotAuthorized

LOG = logging.getLogger(__name__)


class Rules(dict):
    """A store for rules."""

    def __init__(self, rules=None, default_rule=None):
        """Initialize the Rules store."""

        super().__init__(rules or {})
        self.default_rule = default_rule

    @classmethod
    def load_json(cls, data, default_rule=None, raise_error=False):
        """Allow loading of JSON rule data."""

        rules = {k: _parser.parse_rule(v, raise_error)
                 for k, v in json.loads(data).items()}

        return cls(rules, default_rule)

    @classmethod
    def from_dict(cls, rules_dict: dict, default_rule=None, raise_error=False):
        """Allow loading of rule data from a dictionary."""

        # Parse the rules stored in the dictionary
        rules = {k: _parser.parse_rule(v, raise_error)
                 for k, v in rules_dict.items()}

        return cls(rules, default_rule)

    def __missing__(self, key):
        """Implements the default rule handling."""

        # If the default rule isn't actually defined, do something
        # reasonably intelligent
        if not self.default_rule or isinstance(self.default_rule, dict):
            raise KeyError(key)

        if isinstance(self.default_rule, checks.BaseCheck):
            return self.default_rule

        # We need not check this or we will fall into infinite recursion.
        if self.default_rule not in self:
            raise KeyError(key)
        elif isinstance(self.default_rule, str):
            return self[self.default_rule]
        else:
            return None

    def __str__(self):
        """Dumps a string representation of the rules."""

        out_rules = {}
        for key, value in self.items():
            if isinstance(value, checks.TrueCheck):
                out_rules[key] = ''
            else:
                out_rules[key] = str(value)

        return json.dumps(out_rules, indent=4)


class Enforcer(object):
    """Responsible for loading and enforcing rules."""

    def __init__(self, policy_file, rules=None, default_rule=None,
                 raise_error=False, load_once=True):
        """
        :param policy_file: the filename of policy file
        :param rules: default rules
        :param default_rule: default rule
        :param raise_error: raise error on parsing rule and enforcing
                            policy or not
        :param load_once: load policy file just once
        """
        self.default_rule = default_rule
        self.rules = Rules(rules, default_rule)
        self.policy_file = policy_file
        self.raise_error = raise_error

        self.load_once = load_once
        self._policy_loaded = False
        # Make rules loading thread-safe
        self._load_lock = threading.Lock()

    def _set_rules(self, rules: dict, overwrite=True):
        """Created a new Rules object based on the provided dict of rules."""

        if not isinstance(rules, dict):
            raise TypeError('rules must be an instance of dict or Rules,'
                            'got %r instead' % type(rules))

        if overwrite:
            self.rules = Rules(rules, self.default_rule)
        else:
            self.rules.update(rules)

    def load_rules(self, force_reload=False, overwrite=True):
        """Load rules from policy file or cache."""

        # double-checked locking
        if self.load_once and self._policy_loaded:
            return
        with self._load_lock:
            if self.load_once and self._policy_loaded:
                return

            reloaded, data = _cache.read_file(
                self.policy_file, force_reload=force_reload)
            self._policy_loaded = True
            if reloaded or not self.rules:
                rules = Rules.load_json(data, self.default_rule, self.raise_error)
                self._set_rules(rules, overwrite=overwrite)
                LOG.debug('Reload policy file: %s', self.policy_file)

    def enforce(self, rule, target, creds, exc=None, *args, **kwargs):
        """Checks authorization of a rule against the target and credentials."""

        self.load_rules()

        if isinstance(rule, checks.BaseCheck):
            result = rule(target, creds, self)
        elif not self.rules:
            # No rules means we're going to fail closed.
            result = False
        else:
            try:
                # Evaluate the rule
                result = self.rules[rule](target, creds, self)
            except KeyError:
                LOG.debug('Rule [%s] does not exist', rule)
                # If the rule doesn't exist, fail closed
                result = False

        if self.raise_error and not result:
            if exc:
                raise exc(*args, **kwargs)
            else:
                raise PolicyNotAuthorized(rule, target, creds)

        return result


if __name__ == '__main__':
    enforcer = Enforcer('policy.json')
    enforcer.load_rules()
    print(enforcer.rules)
