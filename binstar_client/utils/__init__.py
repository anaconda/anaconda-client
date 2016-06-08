from __future__ import print_function, absolute_import, unicode_literals

import base64
import collections
import getpass
from hashlib import md5
import json
import logging
import os
from os.path import exists, join, dirname, expanduser, isfile, isdir
import stat
import sys
import time

from pkg_resources import parse_version as pv
import yaml

from binstar_client.utils.appdirs import AppDirs, EnvAppDirs

import warnings

from .spec import PackageSpec, package_specs, parse_specs


if 'BINSTAR_CONFIG_DIR' in os.environ:
    dirs = EnvAppDirs('binstar', 'ContinuumIO', os.environ['BINSTAR_CONFIG_DIR'])
else:
    dirs = AppDirs('binstar', 'ContinuumIO')



try:
    import urlparse
    from urllib import quote_plus
except ImportError:
    from urllib import parse as urlparse
    from urllib.parse import quote_plus


try:
    input = raw_input
except NameError:
    input = input

log = logging.getLogger('binstar')


def jencode(*E, **F):
    payload = dict(*E, **F)
    return json.dumps(payload), {'Content-Type': 'application/json'}


def load_token(url):
    tokenfile = join(dirs.user_data_dir, '%s.token' % quote_plus(url))
    if isfile(tokenfile):
        log.debug("Found login token: {}".format(tokenfile))
        with open(tokenfile) as fd:
            token = fd.read().strip()

        if not token:
            log.debug("Token file is empty: {}".format(tokenfile))
            log.debug("Removing file: {}".format(tokenfile))
            os.unlink(tokenfile)
            token = None
    else:
        token = None
    return token


def get_server_api(token=None, site=None, log_level=logging.INFO, cls=None, **kwargs):
    """
    Get the anaconda server api class
    """

    if not cls:
        from binstar_client import Binstar
        cls = Binstar
    config = get_config(remote_site=site)
    url = config.get('url', DEFAULT_URL)

    if log_level >= logging.INFO:
        sys.stderr.write("Using Anaconda API: %s\n" % url)
    if token:
        log.debug("Using token from command line args")
    elif 'BINSTAR_API_TOKEN' in os.environ:
        log.debug("Using token from environment variable BINSTAR_API_TOKEN")
        token = os.environ['BINSTAR_API_TOKEN']
    elif 'ANACONDA_API_TOKEN' in os.environ:
        log.debug("Using token from environment variable ANACONDA_API_TOKEN")
        token = os.environ['ANACONDA_API_TOKEN']

    else:
        token = load_token(url)

    verify = config.get('verify_ssl', True)
    return cls(token, domain=url, verify=verify, **kwargs)

def get_binstar(args=None, cls=None):
    """
    DEPRECATED METHOD,


    use `get_server_api`
    """

    warnings.warn(
      'method get_binstar is deprecated, please use `get_server_api`',
      DeprecationWarning
    )

    token = getattr(args, 'token', None)
    log_level = getattr(args, 'log_level', logging.INFO)
    site = getattr(args, 'site', None)

    aserver_api = get_server_api(token, site, log_level, cls)
    return aserver_api


def store_token(token, args):
    config = get_config(remote_site=args and args.site)

    url = config.get('url', DEFAULT_URL)

    if not isdir(dirs.user_data_dir):
        os.makedirs(dirs.user_data_dir)
    tokenfile = join(dirs.user_data_dir, '%s.token' % quote_plus(url))

    if isfile(tokenfile):
        os.unlink(tokenfile)
    with open(tokenfile, 'w') as fd:
        fd.write(token)
    os.chmod(tokenfile, stat.S_IWRITE | stat.S_IREAD)


def remove_token(args):
    config = get_config(remote_site=args and args.site)
    url = config.get('url', DEFAULT_URL)
    tokenfile = join(dirs.user_data_dir, '%s.token' % quote_plus(url))

    if isfile(tokenfile):
        os.unlink(tokenfile)


def load_config(config_file):
    if exists(config_file):
        with open(config_file) as fd:
            data = yaml.load(fd)
            if data:
                return data

    return {}

SITE_CONFIG = join(dirs.site_data_dir, 'config.yaml')
USER_CONFIG = join(dirs.user_data_dir, 'config.yaml')
USER_LOGDIR = dirs.user_log_dir

def recursive_update(d, u):
    for k, v in u.items():
        if isinstance(v, collections.Mapping):
            r = recursive_update(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d

DEFAULT_URL = 'https://api.anaconda.org'
ALPHA_URL = 'http://api.alpha.binstar.org'
DEFAULT_CONFIG = {
                  'sites': {'binstar': {'url': DEFAULT_URL},
                            'alpha': {'url': ALPHA_URL},
                            }
                  }

def get_config(user=True, site=True, remote_site=None):
    config = DEFAULT_CONFIG.copy()
    if site:
        recursive_update(config, load_config(SITE_CONFIG))
    if user:
        recursive_update(config, load_config(USER_CONFIG))

    remote_site = remote_site or config.get('default_site')
    sites = config.get('sites', {})

    if remote_site:
        remote_site = str(remote_site)
        if remote_site not in sites:
            log.warn("Remote site alias %s does not exist in the config file" % remote_site)
        else:
            recursive_update(config, sites.get(remote_site, {}))

    return config

def set_config(data, user=True):

    config_file = USER_CONFIG if user else SITE_CONFIG

    data_dir = dirname(config_file)
    if not exists(data_dir):
        os.makedirs(data_dir)

    with open(config_file, 'w') as fd:
        yaml.dump(data, fd)



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
