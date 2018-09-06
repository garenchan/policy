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
