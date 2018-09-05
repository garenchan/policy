#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import functools

from policy import Enforcer


users = {
    'lily': {
        'token': 'token1',
        'roles': ['admin']
    },
    'hanmeimei': {
        'token': 'token2',
        'roles': ['user']
    }
}
current_user = None
policy_file = 'policy.json'
enforcer = Enforcer(policy_file)


def get_cred():
    return users.get(current_user)


def enforce_policy(rule):
    """Enforce a policy to a API."""
    def wrapper(func):
        """Decorator used for wrap API."""
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            if enforcer.enforce(rule, {}, get_cred(), raise_error=True):
                return func(*args, **kwargs)

        return wrapped

    return wrapper


class UserResource(object):

    @classmethod
    @enforce_policy('user:create')
    def post(self, *args, **kwargs):
        # do something here
        return 'success'


if __name__ == '__main__':
    current_user = sys.argv[1]
    result = UserResource.post(username='kate', password='passwd')
    print(result)
