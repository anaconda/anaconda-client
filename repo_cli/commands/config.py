'''
`conda repo` configuration

Get, Set, Remove or Show the `conda repo` configuration.

###### `conda repo` sites

`conda repo` sites are a mechanism to allow users to quickly switch
between Anaconda repository instances, from anaconda.org to on-site
[Anaconda Repo](http://continuum.io/anaconda-server) installations.

`conda repo` comes one two pre-configured site: `anaconda`. If you
have configured more than one site, you can operate between them
in 2 ways:

  * Invoke the `conda repo` command with the `-s/--site` option
    e.g. to use the alpha testing site:

        conda repo -s mysite whoami

  * Set a site as the default:

        anaconda config --set default_site mysite
        anaconda whoami

###### Add a `conda repo` site

You can add a site named **site_name** like this:

    anaconda config --set sites.site_name.url "http://url_of_new_site/api"
    anaconda config --set default_site site_name

###### Site Options VS Global Options

All options can be set as global options - affecting all sites,
or site options - affecting only one site

By default options are set globally e.g.:

    conda repo config --set OPTION VALUE

If you want the option to be limited to a single site,
prefix the option with `sites.site_name` e.g.

    conda repo config --set sites.site_name.OPTION VALUE

###### Common `conda repo` configuration options

  * `url`: Set the conda repo api url (default: https://api.anaconda.org)
  * `ssl_verify`: Perform ssl validation on the https requests.
    ssl_verify may be `True`, `False` or a path to a root CA pem file.


###### Other `conda repo` configuration options
  * `auto_register`: Toggle auto_register when doing conda repo upload
  * 'default_site': Default site set to be used by default
  * 'sites': Sites namespace that can be used to add new sites (for
    more information, check the dedicated section above.


###### Toggle auto_register when doing conda repo upload

The default is yes, automatically create a new package when uploading.
If no, then an upload will fail if the package name does not already exist on the server.

    anaconda config --set auto_register yes|no

'''
from __future__ import print_function

from argparse import RawDescriptionHelpFormatter

from .. import errors
from ..utils.config import (SEARCH_PATH, USER_CONFIG, SYSTEM_CONFIG, CONFIGURATION_KEYS,
                            get_config, save_config, load_config, load_file_configs)
from ..utils.yaml import yaml_dump, safe_load

from .base import SubCommandBase


DEPRECATED = {}


class SubCommand(SubCommandBase):
    name = "config"

    def main(self):

        config = get_config()

        if self.args.show:
            self.log.info(yaml_dump(config))
            return

        if self.args.show_sources:
            config_files = load_file_configs(SEARCH_PATH)
            for path in config_files:
                self.log.info('==> %s <==', path)
                self.log.info(yaml_dump(config_files[path]))
            return

        if self.args.get:
            if self.args.get in config:
                self.log.info(config[self.args.get])
            else:
                self.log.info("The value of '%s' is not set." % self.args.get)
            return

        if self.args.files:
            self.log.info('User Config: %s' % USER_CONFIG)
            self.log.info('System Config: %s' % SYSTEM_CONFIG)
            return

        config_file = USER_CONFIG if self.args.user else SYSTEM_CONFIG

        config = load_config(config_file)

        for key, value in self.args.set:
            self.recursive_set(config, key, value, self.args.type)

        for key in self.args.remove:
            try:
                self.recursive_remove(config, key)
            except KeyError:
                self.log.error("Key %s does not exist" % key)

        if not (self.args.set or self.args.remove):
            raise errors.ShowHelp()

        save_config(config, config_file)

    def recursive_remove(self, config_data, key):
        while '.' in key:
            if not config_data:
                return
            prefix, key = key.split('.', 1)
            config_data = config_data.get(prefix, {})

        del config_data[key]

    def recursive_set(self, config_data, key, value, type_):
        while '.' in key:
            prefix, key = key.split('.', 1)
            config_data = config_data.setdefault(prefix, {})

        if key not in CONFIGURATION_KEYS:
            self.log.warning('"%s" is not a known configuration key', key)

        if key in DEPRECATED.keys():
            message = "{} is deprecated: {}".format(key, DEPRECATED[key])
            self.log.warning(message)

        config_data[key] = type_(value)

    def add_parser(self, subparsers):
        description = 'Anaconda client configuration'
        parser = subparsers.add_parser('config',
                                       help=description,
                                       description=description,
                                       epilog=__doc__,
                                       formatter_class=RawDescriptionHelpFormatter)

        parser.add_argument('--type', default=safe_load,
                            help='The type of the values in the set commands. NOTE: This'
                                 'argument is only used when combined with the `--set`'
                                 'command and is ignored otherwise.')

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
        agroup.add_argument('--show-sources', action='store_true',
                            help='Display all identified config sources')
        lgroup = parser.add_argument_group('location')
        lgroup.add_argument('-u', '--user', action='store_true', dest='user', default=True,
                            help='set a variable for this user')
        lgroup.add_argument('-s', '--system', '--site', action='store_false', dest='user',
                            help='set a variable for all users on this machine')

        parser.set_defaults(main=self.main, sub_parser=parser)
