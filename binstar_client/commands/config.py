'''
Binstar configuration

Get, Set, Remove or Show the binstar configuration.


'''
from __future__ import print_function

from ast import literal_eval
import logging
from pprint import pprint

from binstar_client.errors import ShowHelp
from binstar_client.utils import get_config, set_config, SITE_CONFIG, \
    USER_CONFIG

log = logging.getLogger('binstar.config')

def try_eval(item):
    try:
        return literal_eval(item)
    except SyntaxError:
        return item

def recursive_set(config_data, key, value, ty):
    while '.' in key:
        prefix, key = key.split('.', 1)
        config_data = config_data.setdefault(prefix, {})

    config_data[key] = ty(value)

def recursive_remove(config_data, key):
    while '.' in key:
        if not config_data:
            return
        prefix, key = key.split('.', 1)
        config_data = config_data.get(prefix, {})

    del config_data[key]



def main(args):
    config = get_config()

    if args.show:
        fmt = ' + %s: %r'
        log.info('Site Config: %s' % SITE_CONFIG)
        for key_value in get_config(user=False).items():
            log.info(fmt % key_value)
        log.info("")
        log.info('User Config: %s' % USER_CONFIG)
        for key_value in get_config(site=False).items():
            log.info(fmt % key_value)
        log.info("")
        return

    if args.get:
        log.info(config[args.get])
        return

    if args.files:
        log.info('User Config: %s' % USER_CONFIG)
        log.info('Site Config: %s' % SITE_CONFIG)
        return

    config = get_config(args.user, not args.user)

    for key, value in args.set:
        recursive_set(config, key, value, args.type)
        config[key] = args.type(value)

    for key in args.remove:
        try:
            recursive_remove(config, key)
        except KeyError:
            log.error("Key %s does not exist" % key)

    if not (args.set or args.remove):
        raise ShowHelp()

    set_config(config, args.user)


def add_parser(subparsers):
    parser = subparsers.add_parser('config',
                                      help='Binstar configuration',
                                      description=__doc__)

    parser.add_argument('--type', type=try_eval, default=str, help='The type of the values in the set commands')
    parser.add_argument('--set', nargs=2, action='append', default=[], help='sets a new variable: name value', metavar=('name', 'value'))
    parser.add_argument('--get', help='get value: name', metavar='name')
    parser.add_argument('--remove', action='append', default=[], help='removes a variable')
    parser.add_argument('--show', action='store_true', default=False, help='show all variables')
    parser.add_argument('-u', '--user', action='store_true', dest='user', default=True, help='set a variable for this user')
    parser.add_argument('-s', '--site', action='store_false', dest='user', help='set a variable for all users on this machine')
    parser.add_argument('-f', '--files', action='store_true', help='show the config file names')


    parser.set_defaults(main=main, sub_parser=parser)

