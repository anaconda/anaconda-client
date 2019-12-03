from argparse import ArgumentParser, RawDescriptionHelpFormatter
from os.path import dirname
import logging
import pkgutil

from ..utils.api import RepoApi
from ..utils.config import store_token, get_config, load_token, DEFAULT_URL
from ..utils import _setup_logging, file_or_token, config
from .. import errors

def create_parser(description=None, epilog=None, version=None):
    parser = ArgumentParser(
        description=description,
        epilog=epilog,
        formatter_class=RawDescriptionHelpFormatter)

    add_parser_default_arguments(parser, version)
    return parser


def add_parser_default_arguments(parser, version):
    output_group = parser.add_argument_group('output')
    output_group.add_argument('--disable-ssl-warnings', action='store_true', default=False,
                              help='Disable SSL warnings (default: %(default)s)')
    output_group.add_argument('--show-traceback', action='store_true',
                              help='Show the full traceback for chalmers user errors (default: %(default)s)')
    output_group.add_argument('-v', '--verbose',
                              action='store_const', help='print debug information on the console',
                              dest='log_level', default=logging.INFO, const=logging.DEBUG)
    output_group.add_argument('-q', '--quiet',
                              action='store_const', help='Only show warnings or errors on the console',
                              dest='log_level', const=logging.WARNING)
    # version = self.metadata.get('version')
    if version:
        parser.add_argument('-V', '--version', action='version',
                            version="%%(prog)s Command line client (version %s)" % (version,))

    #
    bgroup = parser.add_argument_group('repo-client options')
    bgroup.add_argument('-t', '--token', type=file_or_token,
                        help="Authentication token to use. "
                             "May be a token or a path to a file containing a token")
    bgroup.add_argument('-s', '--site',
                        help='select the anaconda-client site to use', default=config.DEFAULT_SITE)

    # add_subparser_modules(parser, sub_command_module, 'conda_server.subcommand')


def get_sub_command_names(module):
    return [name for _, name, _ in pkgutil.iter_modules([dirname(module.__file__)]) if not name.startswith('_')]


def get_sub_commands(module):
    names = get_sub_command_names(module)
    this_module = __import__(module.__package__ or module.__name__, fromlist=names)
    for name in names:
        subcmd_module = getattr(this_module, name)
        if hasattr(subcmd_module, 'SubCommand'):
            yield getattr(subcmd_module, 'SubCommand')


class RepoCommand:
    parser = create_parser()
    description = ''
    epilog = ''
    version = ''
    log = logging.getLogger('repo_cli')

    def __init__(self, commands_module, args, metadata=None):
        # (command_module, args, exit, description=__doc__, version=version)
        self._args = args
        self._access_token = None
        self.auth_manager = None
        self._commands_module = commands_module
        self.metadata = metadata or {}
        self.init_parser()
        self.args = self.parser.parse_args(args)
        _setup_logging(self.log, log_level=self.args.log_level, show_traceback=self.args.show_traceback,
                       disable_ssl_warnings=self.args.disable_ssl_warnings)
        self.config = config.get_config(site=self.args.site)

        self.url = self.config.get('url', DEFAULT_URL)
        self.api = RepoApi(base_url=self.url)


    def run(self):
        self.check_token()
        try:
            try:
                if not hasattr(self.args, 'main'):
                    self.parser.error("A sub command must be given. "
                                 "To show all available sub commands, run:\n\n\t anaconda -h\n")
                return self.args.main()

            except errors.Unauthorized:
                # if not sys.stdin.isatty() or args.token:
                #     # Don't try the interactive login
                #     # Just exit
                #     raise

                self.log.info('The action you are performing requires authentication, '
                            'please sign in:')
                self._access_token = self.auth_manager.login()
                return self.args.main()

        except errors.ShowHelp:
            self.args.sub_parser.print_help()
            if exit:
                raise SystemExit(1)
            else:
                return 1


    @property
    def site(self):
        return self.args.site

    def check_token(self):
        if not self._access_token:
            # we don't have a valid token... try to get it from local files
            self.api._access_token = self._access_token = config.load_token(self.site)
        return self._access_token

    def init_config(self):
        pass

    def init_parser(self):
        self.parser = create_parser(self.description, self.epilog, self.version)
        self.add_parser_subcommands()


    def add_parser_subcommands(self):
        self._sub_commands = {}
        self.subparsers = self.parser.add_subparsers(help='sub-command help')
        for sub_cmd in get_sub_commands(self._commands_module):
            self.register_sub_command(sub_cmd)

        # for
        # login.add_parser(subparsers)
        # logout.add_parser(subparsers)
        # upload.add_parser(subparsers)
        # channel.add_parser(subparsers)

        # def add_subparser_modules(parser, module=None, entry_point_name=None):

        # subparsers = parser.add_subparsers(title='Commands', metavar='')
        #
        # if module:  # LOAD sub parsers from module
        #     for command_module in get_sub_commands(module):
        #         command_module.add_parser(subparsers)
        #
        # if entry_point_name:  # LOAD sub parsers from setup.py entry_point
        #     for entry_point in iter_entry_points(entry_point_name):
        #         add_parser = entry_point.load()
        #         add_parser(subparsers)
        #
        # for key, sub_parser in subparsers.choices.items():
        #     sub_parser.set_defaults(sub_command_name=key)
        #     sub_parser.add_argument('--json-help', action=json_help)

    def register_sub_command(self, sub_command):
        sub_cmd = sub_command(self)
        self._sub_commands[sub_cmd.name] = sub_cmd
        sub_cmd.add_parser(self.subparsers)

        if sub_cmd.manages_auth:
            self.auth_manager = sub_cmd



    # def register_from_module(self, subcommand):
    #     subcommand = getattr(module, 'Command')(self)
    #     self._subcommands[subcommand.name] = subcommand
    #     if subcommand.manages_auth:
    #         # TODO: We should handle the case where we already have an auth manager
    #         self.auth_manager = subcommand


class SubCommandBase:
    manages_auth = False

    def __init__(self, parent):
        self.parent = parent

    @property
    def args(self):
        return self.parent.args

    @property
    def api(self):
        return self.parent.api

    @property
    def log(self):
        return self.parent.log

    @property
    def access_token(self):
        return self.parent._access_token
