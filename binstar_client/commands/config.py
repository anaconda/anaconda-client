'''
Binstar configuration

Get, Set, Remove or Show the binstar configuration.

###### Binstar Sites

Binstar sites are a mechanism to allow users to quickly switch
between binstar instances. This is primarily used for testing
the binstar alpha site. But also has applications for the
on-site [Anaconda Server](http://continuum.io/anaconda-server).

Binstar comes with two pre-configured sites `alpha` and
`binstar` you may use these in one of two ways:

  * Invoke the binstar command with the `-s/--site` option
    e.g. to use the aplha testing site:

        binstar -s alpha whoami

  * Set a site as the default:

        binstar config --set default_site alpha
        binstar whoami

###### Add a Binstar Site

After installing a [Anaconda Server](http://continuum.io/anaconda-server)
you can add a site named **site_name** like this:

    binstar config --set sites.site_name.url "http://<anaconda-server-ip>:<port>/api"
    binstar config --set default_site site_name

###### Site Options VS Global Options

All options can be set as global options - affecting all sites,
or site options - affecting only one site

By default options are set gobaly e.g.:

    binstar config --set OPTION VALUE

If you want the option to be limited to a single site,
prefix the option with `sites.site_name` e.g.

    binstar config --set sites.site_name.OPTION VALUE

###### Common binstar configuration options

  * `url`: Set the binstar api url (default: https://api.anaconda.org)
  * `verify_ssl`: Perform ssl validation on the https requests.
    verify_ssl may be `True`, `False` or a path to a root CA pem file.
'''
from __future__ import print_function

from argparse import RawDescriptionHelpFormatter
from ast import literal_eval
import logging

from binstar_client.errors import ShowHelp
from binstar_client.utils import get_config, set_config, SITE_CONFIG, \
    USER_CONFIG
import yaml


log = logging.getLogger('binstar.config')

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
    description = 'Binstar configuration'
    parser = subparsers.add_parser('config',
                                      help=description,
                                      description=description,
                                      epilog=__doc__,
                                      formatter_class=RawDescriptionHelpFormatter
                                      )

    parser.add_argument('--type', default=yaml.safe_load,
                        help='The type of the values in the set commands')

    agroup = parser.add_argument_group('actions')

    agroup.add_argument('--set', nargs=2, action='append', default=[],
                        help='sets a new variable: name value', metavar=('name', 'value'))
    agroup.add_argument('--get', metavar='name',
                        help='get value: name')
    agroup.add_argument('--remove', action='append', default=[],
                        help='removes a variable')
    agroup.add_argument('--show', action='store_true', default=False,
                        help='show all variables')
    agroup.add_argument('-f', '--files', action='store_true',
                        help='show the config file names')
    lgroup = parser.add_argument_group('location')
    lgroup.add_argument('-u', '--user', action='store_true', dest='user', default=True,
                        help='set a variable for this user')
    lgroup.add_argument('-s', '--site', action='store_false', dest='user',
                        help='set a variable for all users on this machine')


    parser.set_defaults(main=main, sub_parser=parser)

