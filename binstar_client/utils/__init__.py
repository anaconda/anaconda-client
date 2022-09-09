from __future__ import print_function, absolute_import, unicode_literals

import base64
import json
import logging
import sys

from hashlib import md5

# re-export parse_version
from .spec import PackageSpec, package_specs, parse_specs

# Re-export config
from .config import (get_server_api, dirs, load_token, store_token,
                     remove_token, get_config, set_config, load_config,
                     get_binstar,
                     USER_CONFIG, USER_LOGDIR, SITE_CONFIG, DEFAULT_CONFIG)

from six.moves import input


logger = logging.getLogger('binstar')


# Compatibility layer for :func:`base64.encodestring` / :func:`base64.encodebytes` function
#
# :func:`~base64.encodestring` was replaced by :func:`~base64.encodebytes` in Python 3.1, as well as deprecated.
# In addition, since Python 3.1 result type is changed to :class:`bytes` instead of :class:`str`. Wrapper functions
# ensure :class:`str` output.

if sys.version_info[:3] < (3, 1, 0):
    def b64encode(content):
        """
        Convert bytes-like `content` into base64-encoded string with new lines after every 76 characters.

        :param content: Source object to convert.
        :type content: Union[bytes, bytearray]
        :return: Base64-encoded string.
        :rtype: str
        """
        return base64.encodestring(content)

else:
    def b64encode(content):
        """
        Convert bytes-like `content` into base64-encoded string with new lines after every 76 characters.

        :param content: Source object to convert.
        :type content: Union[bytes, bytearray]
        :return: Base64-encoded string.
        :rtype: str
        """
        return base64.encodebytes(content).decode('ascii')


def jencode(*E, **F):
    payload = dict(*E, **F)
    return json.dumps(payload), {'Content-Type': 'application/json'}


def compute_hash(fp, buf_size=8192, size=None, hash_algorithm=md5):
    hash_obj = hash_algorithm()
    spos = fp.tell()
    if size and size < buf_size:
        s = fp.read(size)
    else:
        s = fp.read(buf_size)
    while s:
        hash_obj.update(s)
        if size:
            size -= len(s)
            if size <= 0:
                break
        if size and size < buf_size:
            s = fp.read(size)
        else:
            s = fp.read(buf_size)
    hex_digest = hash_obj.hexdigest()

    base64_digest = b64encode(hash_obj.digest()).rstrip('\n')

    # data_size based on bytes read.
    data_size = fp.tell() - spos
    fp.seek(spos)
    return (hex_digest, base64_digest, data_size)


def bool_input(prompt, default=True):
    default_str = '[Y|n]' if default else '[y|N]'
    while 1:
        inpt = input('%s %s: ' % (prompt, default_str))
        if inpt.lower() in ['y', 'yes'] and not default:
            return True
        elif inpt.lower() in ['', 'n', 'no'] and not default:
            return False
        elif inpt.lower() in ['', 'y', 'yes']:
            return True
        elif inpt.lower() in ['n', 'no']:
            return False
        else:
            sys.stderr.write('please enter yes or no\n')


WAIT_SECONDS = 15
