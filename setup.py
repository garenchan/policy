#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import re

try:
    # Use setuptools if available
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup

    def find_packages():
        return ['policy', 'policy.tests']


# Check python version info
if sys.version_info < (3, 0, 0):
    raise Exception('Policy only support Python 3.0.0+')

version = re.compile(r"__version__\s*=\s*'(.*?)'")


def get_package_version():
    """return package version without importing it"""
    base = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(base, 'policy', '__init__.py'),
              mode='rt',
              encoding='utf-8') as initf:
        for line in initf:
            m = version.match(line.strip())
            if not m:
                continue
            return m.groups()[0]


def get_long_description():
    """return package's long description"""
    base = os.path.abspath(os.path.dirname(__file__))
    readme_file = os.path.join(base, 'README.md')
    with open(readme_file, mode='rt', encoding='utf-8') as readme:
        return readme.read()


def get_classifiers():
    return [
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Operating System :: OS Independent',
    ]


def get_install_requires():
    """return package's install requires"""
    base = os.path.abspath(os.path.dirname(__file__))
    requirements_file = os.path.join(base, 'requirements.txt')
    if not os.path.exists(requirements_file):
        return []
    with open(requirements_file, mode='rt', encoding='utf-8') as f:
        return f.read().splitlines()


if __name__ == '__main__':
    setup(
        name='policy',
        version=get_package_version(),
        description='A Policy library provides support for RBAC policy enforcement.',
        long_description=get_long_description(),
        long_description_content_type='text/markdown',
        author='garenchan',
        author_email='1412950785@qq.com',
        url='https://github.com/garenchan/policy.git',
        license='http://www.apache.org/licenses/LICENSE-2.0',
        classifiers=get_classifiers(),
        packages=find_packages(),
        install_requires=get_install_requires(),
    )
