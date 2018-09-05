# Policy
A Policy library provides support for RBAC policy enforcement.


## Preface

When I used ``Flask`` to write a ``RESTful web service``, I didn't find a suitable extension to handle endpoints' permission control. Because I really like the permission control method of ``OpenStack`` services which based on a policy file. So I want to implement a more generic library similar to ``oslo.policy``.


## Demo

``policy.json`` as follows, suppose we have two roles: **user** and **admin**, and two resources: **article** and **user**:

    {
      "is_admin": "role:admin",
      "is_user": "role:user or role:admin",

      "article:update": "rule:is_user",
      "user:create": "rule:is_admin"
    }

Creating new users requires ``admin`` permission!

The demo script as follows, suppose we have a ``Authentication Center``, and we enforce ``user:create`` policy for UserResource's post RESTful API.

```
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

```

Now we use a common user to access the API, we will be forbidden because only admin user is allowed:

    >python demo.py hanmeimei
    Traceback (most recent call last):
      File "E:/workspace/github/policy/policy/tests/test_base.py", line 53, in <module>
        result = UserResource.post(username='kate', password='passwd')
      File "E:/workspace/github/policy/policy/tests/test_base.py", line 34, in wrapped
        if enforcer.enforce(rule, {}, get_cred(), raise_error=True):
      File "E:\workspace\github\policy\policy\enforcer.py", line 131, in enforce
        raise PolicyNotAuthorized(rule, target, creds)
    policy.exceptions.PolicyNotAuthorized: user:create on {} by {'token': 'token2', 'roles': ['user']} disallowed by policy

When we use a admin user, the API returns **success**:

    >python demo.py lily
    success
