
import logging
from argparse import ArgumentParser, RawDescriptionHelpFormatter

from binstar_client import __version__ as version
from repo_cli import commands as command_module
from .commands import login, logout, upload, channel
from .utils import _setup_logging, file_or_token, config
from . import errors

logger = logging.getLogger('repo_cli')


def add_default_arguments(parser, version=None):
    output_group = parser.add_argument_group('output')
    output_group.add_argument('--disable-ssl-warnings', action='store_true', default=False,
                              help='Disable SSL warnings (default: %(default)s)')
    output_group.add_argument('--show-traceback', action='store_true',
                              help='Show the full traceback for chalmers user errors (default: %(default)s)')
    output_group.add_argument('-v', '--verbose',
                              action='store_const', help='print debug information on the console',
                              dest='log_level',
                              default=logging.INFO, const=logging.DEBUG)
    output_group.add_argument('-q', '--quiet',
                              action='store_const', help='Only show warnings or errors on the console',
                              dest='log_level', const=logging.WARNING)

    if version:
        parser.add_argument('-V', '--version', action='version',
                            version="%%(prog)s Command line client (version %s)" % (version,))


def _main(sub_command_module, args=None, exit=True, description=None, version=None, epilog=None):
    parser = ArgumentParser(description=description, epilog=epilog,
                            formatter_class=RawDescriptionHelpFormatter)

    add_default_arguments(parser, version)

    subparsers = parser.add_subparsers(help='sub-command help')
    login.add_parser(subparsers)
    logout.add_parser(subparsers)
    upload.add_parser(subparsers)
    channel.add_parser(subparsers)
    # login_parser = subparsers.add_parser('login', help='login help')


    bgroup = parser.add_argument_group('rpoa-client options')
    bgroup.add_argument('-t', '--token', type=file_or_token,
                        help="Authentication token to use. "
                             "May be a token or a path to a file containing a token")
    bgroup.add_argument('-s', '--site',
                        help='select the anaconda-client site to use', default=config.DEFAULT_SITE)

    # add_subparser_modules(parser, sub_command_module, 'conda_server.subcommand')

    _args = parser.parse_args(args)


    _setup_logging(logger, log_level=_args.log_level, show_traceback=_args.show_traceback,
                   disable_ssl_warnings=_args.disable_ssl_warnings)

    site_config = config.get_config(site=_args.site)

    if not _args.token:
        # we don't have a valid token... try to get it from local files
        _args.token = login.load_token(_args.site)

    try:
        try:
            if not hasattr(_args, 'main'):
                parser.error("A sub command must be given. "
                             "To show all available sub commands, run:\n\n\t anaconda -h\n")
            return _args.main(_args)
        except errors.Unauthorized:
            # if not sys.stdin.isatty() or args.token:
            #     # Don't try the interactive login
            #     # Just exit
            #     raise

            logger.info('The action you are performing requires authentication, '
                        'please sign in:')
            _args.token = login.interactive_login(_args)
            return _args.main(_args)
    except errors.ShowHelp:
        args.sub_parser.print_help()
        if exit:
            raise SystemExit(1)
        else:
            return 1


def main(args=None, exit=True):
    _main(command_module, args, exit, description=__doc__, version=version)


if __name__ == '__main__':
    main()
