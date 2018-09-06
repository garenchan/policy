# -*- coding: utf-8 -*-
"""
    policy._utils
    ~~~~~~~~~~~~~~~

    Policy's utils for internal user.

"""

_sentinel = object()


def dict_from_object(obj: object):
    """Convert a object into dictionary with all of its readable attributes."""

    # If object is a dict instance, no need to convert.
    return (obj if isinstance(obj, dict)
            else {attr: getattr(obj, attr)
                  for attr in dir(obj) if not attr.startswith('_')})


def xgetattr(obj: object, name: str, default=_sentinel, getitem=False):
    """Get attribute value from object.

    :param obj: object
    :param name: attribute or key name
    :param default: when attribute or key missing, return default; if obj is a
        dict and use getitem, default will not be used.
    :param getitem: when object is a dict, use getitem or get
    :return: attribute or key value, or raise KeyError/AttributeError
    """

    if isinstance(obj, dict):
        if getitem:
            # In tune with `dict.__getitem__` method.
            return obj[name]
        else:
            # In tune with `dict.get` method.
            val = obj.get(name, default)
            return None if val is _sentinel else val
    else:
        # If object is not a dict, in tune with `getattr` method.
        val = getattr(obj, name, default)
        if val is _sentinel:
            msg = '%r object has no attribute %r' % (obj.__class__, name)
            raise AttributeError(msg)
        else:
            return val
