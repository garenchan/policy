# Policy
A Policy library provides support for RBAC policy enforcement.


## Preface

When I used ``Flask`` to write a ``RESTful web service``, I didn't find a suitable extension to handle endpoints' permission control. Because I really like the permission control method of ``OpenStack`` services which based on a policy file. So I want to implement a more generic library similar to ``oslo.policy``.


## Demo

### Generate Policy File

Suppose there are two roles: **user** and **admin**, and two resources: **article** and **user**. We have 3 policies:

- Only user can update article
- Creating new user requires admin permission.
- Only article owners or admin-role user can delete articles.

Based on the previous description, we generate the following policy file ``policy.json``:

    {
      "is_admin": "role:admin",
      "is_user": "role:user or role:admin",

      "article:update": "rule:is_user",
      "article:delete": "role:admin or id:%(user_id)s",
      "user:create": "rule:is_admin"
    }


### Enforce Policy With Flask Application

Suppose we have a simple ``Flask`` application which provides two api: creating new user and deleting article and we run it:

```
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import functools

from flask import Flask, request, g

from policy import Enforcer
from policy.exceptions import PolicyNotAuthorized

app = Flask(__name__)
enforcer = Enforcer('policy.json', raise_error=True)


@app.errorhandler(PolicyNotAuthorized)
def handle_policy_exception(error):
    return str(error)


users = {
    'lily': {
        'id': 'd55a4192eb3b489589d5ee95dcf3af7d',
        'roles': ['user', 'admin']
    },
    'kate': {
        'id': '1a535309687244e2aa434b25ef4bfb59',
        'roles': ['user']
    },
    'lucy': {
        'id': '186977181e7f4a9e85104ca017e845f3',
        'roles': ['user']
    }
}

articles = {
    'python': {
        'id': 'e6e31ad693734b269099d9acac2cb800',
        'user_id': '1a535309687244e2aa434b25ef4bfb59'  # owned  by kate
    }
}


def login_required(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        username = request.args.get('me')
        credential = users.get(username)
        if not credential:
            raise Exception('login required')
        else:
            g.cred = credential
        return func(*args, **kwargs)

    return wrapped


def enforce_policy(rule):
    """Enforce a policy to a API."""
    def wrapper(func):
        """Decorator used for wrap API."""
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            if enforcer.enforce(rule, {}, g.cred):
                return func(*args, **kwargs)

        return wrapped

    return wrapper


@app.route('/user', methods=['GET'])
@login_required
@enforce_policy('user:create')
def create_user():
    # do create action here
    return 'user created'


@app.route('/article', methods=['GET'])
@login_required
def delete_article():
    article_name = request.args.get('name')
    article = articles.get(article_name)

    # do fine-grained permission check here
    enforcer.enforce('article:delete', article, g.cred)
    # do delete action here
    return 'arcticle %s deleted' % article['id']


if __name__ == '__main__':
    app.run(port=8888, debug=True)
```

#### View-Level

We provide a ``enforce_policy`` decorator to enforce policy on views ``create_user``.

We head to http://127.0.0.1:8888/user?me=kate to simulate ``kate``'s creating user and get a error:

    user:create on {} by {'roles': ['user'], 'id': '1a535309687244e2aa434b25ef4bfb59'} disallowed by policy

Then we head to http://127.0.0.1:8888/user?me=lily to simulate ``lily``'s creating user and get a successful response:

    user created

#### Fine-Grained

In some scenarios we want a fine-grained permission check. We enforce policy inside view ``delete_article``, because outside of it we can't know which article the user wants to delete.

We head to http://127.0.0.1:8888/article?me=lucy&name=python to simulate ``lucy``'s deleting article and get a error:

    article:delete on {'user_id': '1a535309687244e2aa434b25ef4bfb59', 'id': 'e6e31ad693734b269099d9acac2cb800'} by {'roles': ['user'], 'id': '186977181e7f4a9e85104ca017e845f3'} disallowed by policy

Then we head to http://127.0.0.1:8888/article?me=kate&name=python to simulate ``kate``'s deleting article and get a successful response because ``kate`` is the article's owner:

    arcticle e6e31ad693734b269099d9acac2cb800 deleted

Finally we head to http://127.0.0.1:8888/article?me=lily&name=python to simulate ``lily``'s deleting article and get a successful response because ``lily`` is a admin-role user:

    arcticle e6e31ad693734b269099d9acac2cb800 deleted
