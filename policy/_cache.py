# -*- coding: utf-8 -*-
"""
    policy._cache
    ~~~~~~~~~~~~~~~

    Cache for policy file.

"""

import os
import logging

LOG = logging.getLogger(__name__)

# Global file cache
CACHE = {}


def read_file(filename: str, force_reload=False):
    """Read a file if it has been modified.

    :param filename: File name which want to be read from.
    :param force_reload: Whether to reload the file.
    :returns: A tuple with a boolean specifying if the data is fresh or not.
    """

    if force_reload:
        _delete_cached_file(filename)

    reloaded = False
    mtime = os.path.getmtime(filename)
    cache_info = CACHE.setdefault(filename, {})

    if not cache_info or mtime > cache_info.get('mtime', 0):
        LOG.debug('Reloading cached file %s', filename)
        with open(filename) as fp:
            cache_info['data'] = fp.read()
        cache_info['mtime'] = mtime
        reloaded = True

    return reloaded, cache_info['data']


def _delete_cached_file(filename: str):
    """Delete cached file if present.

    :param filename: Filename to delete
    """
    try:
        del CACHE[filename]
    except KeyError:
        pass
