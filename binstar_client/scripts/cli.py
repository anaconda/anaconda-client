"""
Anaconda repository command line manager
"""
from __future__ import print_function, unicode_literals

import logging
import sys

import requests

from argparse import ArgumentParser, RawDescriptionHelpFormatter
from os import makedirs
from os.path import join, exists, isfile
from logging.handlers import RotatingFileHandler

from clyent import add_subparser_modules
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from six import PY2

from binstar_client import __version__ as version
from binstar_client import commands as command_module
from binstar_client.commands.login import interactive_login
from binstar_client import errors
from binstar_client.utils import USER_LOGDIR

logger = logging.getLogger('binstar')


def file_or_token(value):
    """
    If value is a file path and the file exists its contents are stripped and returned,
    otherwise value is returned.
    """
    if isfile(value):
        with open(value) as fd:
            return fd.read().strip()

    if any(char in value for char in '/\\.'):
        # This chars will never be in a token value, but may be in a path
        # The error message will be handled by the parser
        raise ValueError()

    return value


def _custom_excepthook(logger, show_traceback=False):
    def excepthook(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt) or not issubclass(exc_type, errors.ServerError):
            return

        if show_traceback:
            logger.error('', exc_info=(exc_type, exc_value, exc_traceback))
        else:
            logger.error('%s', exc_value)

    return excepthook


class ConsoleFormatter(logging.Formatter):
    def format(self, record):
        fmt = '%(message)s' if record.levelno == logging.INFO \
            else '[%(levelname)s] %(message)s'
        if PY2:
            self._fmt = fmt
        else:
            self._style._fmt = fmt
        return super(ConsoleFormatter, self).format(record)


def _setup_logging(logger, log_level=logging.INFO, show_traceback=False, disable_ssl_warnings=False):
    logger.setLevel(logging.DEBUG)

    if not exists(USER_LOGDIR):
        makedirs(USER_LOGDIR)

    log_file = join(USER_LOGDIR, 'cli.log')

    file_handler = RotatingFileHandler(log_file, maxBytes=10 * (1024 ** 2), backupCount=5)
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)

    console_handler.setFormatter(ConsoleFormatter())
    file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s %(name)-15s %(message)s'))

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    sys.excepthook = _custom_excepthook(logger, show_traceback=show_traceback)

    if disable_ssl_warnings:
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


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


def binstar_main(sub_command_module, args=None, exit=True, description=None, version=None, epilog=None):
    parser = ArgumentParser(description=description, epilog=epilog,
                            formatter_class=RawDescriptionHelpFormatter)

    add_default_arguments(parser, version)
    bgroup = parser.add_argument_group('anaconda-client options')
    bgroup.add_argument('-t', '--token', type=file_or_token,
                        help="Authentication token to use. "
                             "May be a token or a path to a file containing a token")
    bgroup.add_argument('-s', '--site',
                        help='select the anaconda-client site to use', default=None)

    add_subparser_modules(parser, sub_command_module, 'conda_server.subcommand')

    args = parser.parse_args(args)

    _setup_logging(logger, log_level=args.log_level, show_traceback=args.show_traceback,
                   disable_ssl_warnings=args.disable_ssl_warnings)

    try:
        try:
            if not hasattr(args, 'main'):
                parser.error("A sub command must be given. "
                             "To show all available sub commands, run:\n\n\t anaconda -h\n")
            return args.main(args)
        except errors.Unauthorized:
            if not sys.stdin.isatty() or args.token:
                # Don't try the interactive login
                # Just exit
                raise

            logger.info('The action you are performing requires authentication, '
                        'please sign in:')
            interactive_login(args)
            return args.main(args)
    except errors.ShowHelp:
        args.sub_parser.print_help()
        if exit:
            raise SystemExit(1)
        else:
            return 1


def main(args=None, exit=True):
    binstar_main(command_module, args, exit,
                 description=__doc__, version=version)


if __name__ == '__main__':
    main()
