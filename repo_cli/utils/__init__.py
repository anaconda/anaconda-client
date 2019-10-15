"""
Utilities functions for Anaconda repository command line manager
"""
from __future__ import print_function, unicode_literals

from os import makedirs
from os.path import exists, join, isfile
from six import PY2
import logging
from logging.handlers import RotatingFileHandler

import sys

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from binstar_client.utils import USER_LOGDIR


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
        if issubclass(exc_type, KeyboardInterrupt):
            logger.error('execution interrupted')
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
