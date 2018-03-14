from __future__ import print_function, absolute_import, unicode_literals

import base64
import json
import logging
import os
import sys
import time

from hashlib import md5

# re-export parse_version
from pkg_resources import parse_version as pv
from .spec import PackageSpec, package_specs, parse_specs

# Re-export config
from .config import (get_server_api, dirs, load_token, store_token,
                     remove_token, get_config, set_config, load_config,
                     get_binstar,
                     USER_CONFIG, USER_LOGDIR, SITE_CONFIG, DEFAULT_CONFIG)

from six.moves import input


logger = logging.getLogger('binstar')


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

    b64encode = getattr(base64, 'encodebytes', base64.encodestring)
    base64_digest = b64encode(hash_obj.digest())
    if base64_digest[-1] == '\n':
        base64_digest = base64_digest[0:-1]
    # data_size based on bytes read.
    data_size = fp.tell() - spos
    fp.seek(spos)
    return (hex_digest, base64_digest, data_size)


class upload_in_chunks(object):
    def __init__(self, fd, chunksize=1 << 13):
        self.fd = fd
        self.chunksize = chunksize
        self.totalsize = os.fstat(fd.fileno()).st_size
        self.readsofar = 0

    def __iter__(self):
        sys.stderr.write('Progress:\n')
        while True:
            data = self.fd.read(self.chunksize)
            if not data:
                sys.stderr.write("\n")
                break
            self.readsofar += len(data)
            percent = self.readsofar * 1e2 / self.totalsize
            sys.stderr.write("\r{percent:3.0f}%".format(percent=percent))
            yield data

    def __len__(self):
        return self.totalsize


def upload_with_progress(fd):
    it = upload_in_chunks(fd)
    IterableToFileAdapter(it)


class IterableToFileAdapter(object):
    def __init__(self, iterable):
        self.iterator = iter(iterable)
        self.length = len(iterable)

    def read(self, size=-1):  # TBD: add buffer for `len(data) > size` case
        return next(self.iterator, b'')

    def __len__(self):
        return self.length


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


def upload_print_callback(args):
    start_time = time.time()
    if args.no_progress or args.log_level > logging.INFO:

        def callback(curr, total):
            perc = 100.0 * curr / total if total else 0

            if (time.time() - callback.last_output) > WAIT_SECONDS:
                print('| %.2f%% ' % (perc), end='')
                sys.stdout.flush()
                callback.last_output = time.time()

        callback.last_output = time.time()

        return callback

    def callback(curr, total):
        curr_time = time.time()
        time_delta = curr_time - start_time

        remain = total - curr
        if curr and remain:
            eta = 1.0 * time_delta / curr * remain / 60.0
        else:
            eta = 0

        curr_kb = curr // 1024
        total_kb = total // 1024
        perc = 100.0 * curr / total if total else 0

        msg = '\r uploaded %(curr_kb)i of %(total_kb)iKb: %(perc).2f%% ETA: %(eta).1f minutes'
        sys.stderr.write(msg % locals())
        sys.stderr.flush()
        if curr == total:
            sys.stderr.write('\n')

    return callback
