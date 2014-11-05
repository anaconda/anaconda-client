'''
Binstar command line utility
'''
from __future__ import print_function, unicode_literals

from argparse import ArgumentParser, RawDescriptionHelpFormatter
import logging
from os import makedirs
from os.path import join, exists, isfile

from binstar_client import __version__ as version
from binstar_client import commands as command_module
from binstar_client.commands.login import interactive_login
from binstar_client import errors
from binstar_client.utils import USER_LOGDIR
from binstar_client.utils.handlers import syslog_handler

from clyent import add_default_arguments, add_subparser_modules
from clyent.logs import setup_logging
import argparse


logger = logging.getLogger('binstar')


def add_syslog_handler():
    hndlr = syslog_handler('binstar-client')

    binstar_logger = logging.getLogger()
    binstar_logger.setLevel(logging.INFO)
    binstar_logger.addHandler(hndlr)

def file_or_token(value):

    if isfile(value):
        with open(value) as fd:
            return fd.read().strip()
    if any(char in value for char in '/\\.'):
        # This chars will never be in a token value, but may be in a path
        # The error message will be handled by the parser
        raise ValueError()
    return value




def binstar_main(sub_command_module, args=None, exit=True, description=None, version=None, epilog=None):

    parser = ArgumentParser(description=description, epilog=epilog,
                            formatter_class=RawDescriptionHelpFormatter)

    add_default_arguments(parser, version)
    bgroup = parser.add_argument_group('binstar options')
    bgroup.add_argument('-t', '--token', type=file_or_token,
                        help="Authentication token to use. "
                             "May be a token or a path to a file containing a token")
    bgroup.add_argument('-s', '--site',
                        help='select the binstar site to use', default=None)

    add_subparser_modules(parser, sub_command_module)

    if not exists(USER_LOGDIR): makedirs(USER_LOGDIR)
    logfile = join(USER_LOGDIR, 'cli.log')

    args = parser.parse_args(args)

    setup_logging(logger, args.log_level, use_color=args.color,
                  logfile=logfile, show_tb=args.show_traceback)

    add_syslog_handler()

    try:
        try:
            if not hasattr(args, 'main'):
                parser.error("A sub command must be given. To show all available sub commands, run:\n\n\t binstar -h\n")
            return args.main(args)
        except errors.Unauthorized:
            if not args.token:
                logger.info('The action you are performing requires authentication, please sign in:')
                interactive_login(args)
                return args.main(args)
            else:
                raise

    except errors.ShowHelp:
        args.sub_parser.print_help()
        if exit:
            raise SystemExit(1)
        else:
            return 1

def main(args=None, exit=True):
    binstar_main(command_module, args, exit,
                 description=__doc__, version=version)

