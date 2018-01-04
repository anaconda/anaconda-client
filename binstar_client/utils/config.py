from __future__ import print_function, absolute_import, unicode_literals

import glob
import json
from os.path import exists, join, dirname, isfile, isdir, basename, abspath, expanduser
import collections
import logging
import os
import stat
import sys
import warnings
import itertools
from string import Template

try:
    from urllib import quote_plus
except ImportError:
    from urllib.parse import quote_plus

from binstar_client.utils.conda import CONDA_PREFIX, CONDA_ROOT
from binstar_client.utils.appdirs import AppDirs, EnvAppDirs
from binstar_client.errors import BinstarError

from .yaml import yaml_load, yaml_dump


logger = logging.getLogger('binstar')


def expandvars(path):
    environ = dict(CONDA_ROOT=CONDA_ROOT, CONDA_PREFIX=CONDA_PREFIX)
    environ.update(os.environ)
    return Template(path).safe_substitute(**environ)


def expand(path):
    return abspath(expanduser(expandvars(path)))


if 'BINSTAR_CONFIG_DIR' in os.environ:
    dirs = EnvAppDirs('binstar', 'ContinuumIO', os.environ['BINSTAR_CONFIG_DIR'])
    USER_CONFIG = join(dirs.user_data_dir, 'config.yaml')
else:
    dirs = AppDirs('binstar', 'ContinuumIO')
    USER_CONFIG = expand('~/.continuum/anaconda-client/config.yaml')

USER_LOGDIR = dirs.user_log_dir
SITE_CONFIG = expand('$CONDA_ROOT/etc/anaconda-client/config.yaml')
SYSTEM_CONFIG = SITE_CONFIG


DEFAULT_URL = 'https://api.anaconda.org'
ALPHA_URL = 'http://api.alpha.binstar.org'
DEFAULT_CONFIG = {
    'sites': {
        'binstar': {'url': DEFAULT_URL},
        'alpha': {'url': ALPHA_URL},
    }
}
CONFIGURATION_KEYS = [
    'auto_register',
    'default_site',
    'sites',
    'url',
    'verify_ssl',
    'ssl_verify',
]
SEARCH_PATH = (
    dirs.site_data_dir,
    '/etc/anaconda-client/',
    '$CONDA_ROOT/etc/anaconda-client/',
    dirs.user_data_dir,
    '~/.continuum/anaconda-client/',
    '$CONDA_PREFIX/etc/anaconda-client/',
)


def recursive_update(d, u):
    for k, v in u.items():
        if isinstance(v, collections.Mapping):
            r = recursive_update(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d


def get_server_api(token=None, site=None, cls=None, **kwargs):
    """
    Get the anaconda server api class
    """

    if not cls:
        from binstar_client import Binstar
        cls = Binstar
    config = get_config(remote_site=site)
    url = config.get('url', DEFAULT_URL)

    logger.info("Using Anaconda API: %s", url)

    if token:
        logger.debug("Using token from command line args")
    elif 'BINSTAR_API_TOKEN' in os.environ:
        logger.debug("Using token from environment variable BINSTAR_API_TOKEN")
        token = os.environ['BINSTAR_API_TOKEN']
    elif 'ANACONDA_API_TOKEN' in os.environ:
        logger.debug("Using token from environment variable ANACONDA_API_TOKEN")
        token = os.environ['ANACONDA_API_TOKEN']

    else:
        token = load_token(url)

    verify = config.get('ssl_verify', config.get('verify_ssl', True))
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
    site = getattr(args, 'site', None)

    aserver_api = get_server_api(token, site, cls)
    return aserver_api


TOKEN_DIRS = [
    dirs.user_data_dir,
    join(dirname(USER_CONFIG), 'tokens'),
]
TOKEN_DIR = TOKEN_DIRS[-1]


def store_token(token, args):
    config = get_config(remote_site=args and args.site)

    for token_dir in TOKEN_DIRS:
        url = config.get('url', DEFAULT_URL)
        if not isdir(token_dir):
            os.makedirs(token_dir)
        tokenfile = join(token_dir, '%s.token' % quote_plus(url))

        if isfile(tokenfile):
            os.unlink(tokenfile)
        with open(tokenfile, 'w') as fd:
            fd.write(token)
        os.chmod(tokenfile, stat.S_IWRITE | stat.S_IREAD)


def load_token(url):
    for token_dir in TOKEN_DIRS:
        tokenfile = join(token_dir, '%s.token' % quote_plus(url))
        if isfile(tokenfile):
            logger.debug("Found login token: {}".format(tokenfile))
            with open(tokenfile) as fd:
                token = fd.read().strip()

            if token:
                return token
            else:
                logger.debug("Token file is empty: {}".format(tokenfile))
                logger.debug("Removing file: {}".format(tokenfile))
                os.unlink(tokenfile)


def remove_token(args):
    config = get_config(remote_site=args and args.site)
    url = config.get('url', DEFAULT_URL)
    for token_dir in TOKEN_DIRS:
        tokenfile = join(token_dir, '%s.token' % quote_plus(url))
        if isfile(tokenfile):
            os.unlink(tokenfile)


def load_config(config_file):
    if exists(config_file):
        with open(config_file) as fd:
            data = yaml_load(fd)
            if data:
                return data

    return {}


def load_file_configs(search_path):
    def _file_yaml_loader(fullpath):
        assert fullpath.endswith(".yml") or fullpath.endswith(".yaml") or fullpath.endswith("anacondarc"), fullpath
        yield fullpath, load_config(fullpath)

    def _dir_yaml_loader(fullpath):
        for filename in os.listdir(fullpath):
            if filename.endswith(".yml") or filename.endswith(".yaml"):
                filepath = join(fullpath, filename)
                yield filepath, load_config(filepath)

    # map a stat result to a file loader or a directory loader
    _loader = {
        stat.S_IFREG: _file_yaml_loader,
        stat.S_IFDIR: _dir_yaml_loader,
    }

    def _get_st_mode(path):
        # stat the path for file type, or None if path doesn't exist
        try:
            return stat.S_IFMT(os.stat(path).st_mode)
        except OSError:
            return None

    expanded_paths = [expand(path) for path in search_path]
    stat_paths = (_get_st_mode(path) for path in expanded_paths)
    load_paths = (_loader[st_mode](path)
                  for path, st_mode in zip(expanded_paths, stat_paths)
                  if st_mode is not None)
    raw_data = collections.OrderedDict(kv for kv in itertools.chain.from_iterable(load_paths))
    return raw_data


def get_config(user=True, site=True, remote_site=None):
    config = DEFAULT_CONFIG.copy()
    file_configs = load_file_configs(SEARCH_PATH)
    for fn in file_configs:
        recursive_update(config, file_configs[fn])

    remote_site = remote_site or config.get('default_site')
    sites = config.get('sites', {})

    if remote_site:
        remote_site = str(remote_site)
        if remote_site not in sites:
            logger.warning("Remote site alias %s does not exist in the config file" % remote_site)
        else:
            recursive_update(config, sites.get(remote_site, {}))

    return config


def save_config(data, config_file):
    data_dir = dirname(config_file)

    try:
        if not exists(data_dir):
            os.makedirs(data_dir)

        with open(config_file, 'w') as fd:
            yaml_dump(data, stream=fd)
    except EnvironmentError as exc:
        raise BinstarError('%s: %s' % (exc.filename, exc.strerror,))


def set_config(data, user=True):
    warnings.warn('Use save_config instead of set_config', DeprecationWarning)
    save_config(data, USER_CONFIG if user else SYSTEM_CONFIG)
