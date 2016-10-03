from __future__ import print_function, absolute_import, unicode_literals

from os.path import exists, join, dirname, isfile, isdir
import collections
import logging
import os
import stat
import sys
import warnings

try:
    from urllib import quote_plus
except ImportError:
    from urllib.parse import quote_plus

import yaml

from binstar_client.utils.appdirs import AppDirs, EnvAppDirs


log = logging.getLogger('binstar')

if 'BINSTAR_CONFIG_DIR' in os.environ:
    dirs = EnvAppDirs('binstar', 'ContinuumIO', os.environ['BINSTAR_CONFIG_DIR'])
else:
    dirs = AppDirs('binstar', 'ContinuumIO')

SITE_CONFIG = join(dirs.site_data_dir, 'config.yaml')
USER_CONFIG = join(dirs.user_data_dir, 'config.yaml')
USER_LOGDIR = dirs.user_log_dir

DEFAULT_URL = 'https://api.anaconda.org'
ALPHA_URL = 'http://api.alpha.binstar.org'
DEFAULT_CONFIG = {
    'sites': {
        'binstar': {'url': DEFAULT_URL},
        'alpha': {'url': ALPHA_URL},
    }
}


def recursive_update(d, u):
    for k, v in u.items():
        if isinstance(v, collections.Mapping):
            r = recursive_update(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d


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
