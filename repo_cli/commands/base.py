from argparse import ArgumentParser, RawDescriptionHelpFormatter
from os.path import dirname
import logging
import pkgutil
from six.moves.urllib.parse import urlparse

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
                        help='select the anaconda-client site to use')

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

    def register_sub_command(self, sub_command):
        sub_cmd = sub_command(self)
        self._sub_commands[sub_cmd.name] = sub_cmd
        sub_cmd.add_parser(self.subparsers)

        if sub_cmd.manages_auth:
            self.auth_manager = sub_cmd


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


class BulkActionCommand(SubCommandBase):
    name = None

    def main(self):

        for spec in self.args.specs:
            try:
                if spec._filename:
                    self.exec_bulk_action(spec.channel, self.args.family, spec.package, spec.version, spec.filename, spec)
                elif spec._version:
                    self.exec_bulk_action(spec.channel, self.args.family, spec.package, spec.version, spec=spec)
                elif spec._package:
                    self.exec_bulk_action(spec.channel, self.args.family, spec.package, spec=spec)
                else:
                    self.log.error('Invalid package specification: %s', spec)

            except errors.NotFound:
                if self.args.force:
                    self.log.warning('', exc_info=True)
                    continue
                else:
                    raise

    def exec_bulk_action(self, channel, family, artifact, version=None, filename=None, spec=None):
        base_item = {
                "name": artifact,
                "family": family,
        }

        target_description = ''
        if hasattr(self.args, 'destination'):
            target_channel = self.args.destination
            if not target_channel:
                # destination channel not specified.. we need to get the user default channel and use it
                pass
            if target_channel:
                target_description = 'to channel %s ' % target_channel
        items = []
        if version or filename:
            packages = self.api.get_channel_artifacts_files(channel, family, artifact, version, filename)

            if not packages:
                self.log.warning('No files matches were found for the provided spec: %s\n' % (spec))
                return

            files_descr = []
            for filep in packages:
                files_descr.append('PACKAGE: {name}:{version}-{ckey}; PLATFORM: {platform}; FILENAME: {fn}'.format(**filep))
                item = dict(base_item)
                item['ckey'] = filep['ckey']
                items.append(item)

            affected_files = '\n'.join(files_descr)

            msg = 'Are you sure you want to %s the package release %s %s? The following ' \
                  'will be affected: \n\n %s\n\nConfirm?' % (self.name, target_description, spec, affected_files)
        else:
            msg = 'Conform action %s on spec %s ? (and all data with it?)' % (self.name, spec)
            items = [base_item]
        force = getattr(self.args, 'force', False)
        if force or bool_input(msg, False):
            data = self.api.channel_artifacts_bulk_actions(channel, self.name, items, target_channel=target_channel)
            self.log.info('%s action successful\n' % self.name)
        else:
            self.log.info('%s action not executed\n' % self.name)

    def add_parser(self, subparsers):
        raise NotImplementedError




class PackageSpec(object):
    def __init__(self, channel, package=None, version=None, filename=None, attrs=None, spec_str=None):
        self._user = channel
        self._package = package
        self._version = version
        self._filename = filename
        self.attrs = attrs
        if spec_str:
            self.spec_str = spec_str
        else:
            spec_str = str(channel)
            if package:
                spec_str = '%s/%s' % (spec_str, package)
            if version:
                spec_str = '%s/%s' % (spec_str, version)
            if filename:
                spec_str = '%s/%s' % (spec_str, filename)
            self.spec_str = spec_str

    @classmethod
    def from_string(cls, spec_string):
        channel = spec_string
        package = version = filename = None
        attrs = {}
        if '::' in channel:
            channel, package = channel.split('::', 1)
        if package and '/' in package:
            package, version = package.split('/', 1)

        if version and '/' in version:
            version, filename = version.split('/', 1)

        if filename and '?' in filename:
            filename, qsl = filename.rsplit('?', 1)
            attrs = dict(urlparse.parse_qsl(qsl))

        return PackageSpec(channel, package, version, filename, attrs, spec_string)

    def __str__(self):
        return self.spec_str

    def __repr__(self):
        return '<PackageSpec %r>' % (self.spec_str)

    @property
    def channel(self):
        if self._user is None:
            raise errors.UserError('user not given (got %r expected <username> )' % (self.spec_str,))
        return self._user

    @property
    def name(self):
        if self._package is None:
            raise errors.UserError('package not given in spec (got %r expected <username>/<package> )' % (self.spec_str,))
        return self._package

    @property
    def package(self):
        if self._package is None:
            raise errors.UserError('package not given in spec (got %r expected <username>/<package> )' % (self.spec_str,))
        return self._package

    @property
    def version(self):
        if self._version is None:
            raise errors.UserError('version not given in spec (got %r expected <username>/<package>/<version> )' % (self.spec_str,))
        return self._version

    @property
    def filename(self):
        if self._filename is None:
            raise errors.UserError('filename not given in spec (got %r expected <username>/<package>/<version>/<filename> )' % (self.spec_str,))
        return self._filename


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