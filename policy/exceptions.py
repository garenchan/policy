# -*- coding: utf-8 -*-
"""
    policy.exceptions
    ~~~~~~~~~~~~~~~

    Policy related exceptions.

"""


class PolicyException(Exception):
    """Base exception of policy related."""

    pass


class InvalidRuleException(PolicyException):
    """Invalid rule exception"""

    def __init__(self, rule):
        self.rule = rule

    def __str__(self):
        return 'Invalid rule %r' % self.rule

    def __repr__(self):
        return '<%s: %r>' % (self.__class__.__name__, self.rule)


class PolicyNotAuthorized(PolicyException):
    """Default exception raised for policy enforcement failure."""

    def __init__(self, rule, target, creds):
        msg = ('%(rule)s on %(target)s by %(creds)s disallowed by policy' %
               {'rule': rule, 'target': target, 'creds': creds})
        super().__init__(msg)
