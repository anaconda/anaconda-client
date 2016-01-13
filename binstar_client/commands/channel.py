'''
Manage your Anaconda Cloud channels

'''
from __future__ import unicode_literals, print_function
from binstar_client.utils import get_server_api
import functools
import logging
import argparse

log = logging.getLogger('binstar.channel')


def main(args, name, deprecated=False):
    aserver_api = get_server_api(args.token, args.site, args.log_level)

    if args.organization:
        owner = args.organization
    else:
        current_user = aserver_api.user()
        owner = current_user['login']

    if deprecated:
        log.warn('channel command is deprecated in favor of label')

    if args.copy:
        aserver_api.copy_channel(args.copy[0], owner, args.copy[1])
        log.info("Copied {} {} to {}".format(name, *tuple(args.copy)))
    elif args.remove:
        aserver_api.remove_channel(args.remove, owner)
        log.info("Removed {} {}".format(name, args.remove))
    elif args.list:
        log.info('{}s'.format(name.title()))
        for channel, info in aserver_api.list_channels(owner).items():
            if isinstance(info, int):  # OLD API
                log.info((' + %s ' % channel))
            else:
                log.info((' + %s ' % channel) + ('[locked]' if info['is_locked'] else ''))

    elif args.show:
        info = aserver_api.show_channel(args.show, owner)
        log.info('{} {} {}'.format(
            name.title(),
            args.show,
            ('[locked]' if info['is_locked'] else '')
        ))
        for f in info['files']:
            log.info('  + %(full_name)s' % f)
    elif args.lock:
        aserver_api.lock_channel(args.lock, owner)
        log.info("{} {} is now locked".format(name.title(), args.lock))
    elif args.unlock:
        aserver_api.unlock_channel(args.unlock, owner)
        log.info("{} {} is now unlocked".format(name.title(), args.unlock))
    else:
        raise NotImplementedError()

def _add_parser(subparsers, name, deprecated=False):
    deprecated_warn = ""
    if deprecated:
        deprecated_warn = "[DEPRECATED in favor of label] \n"

    subparser = subparsers.add_parser(
        name,
        help='{}Manage your Anaconda Cloud {}s'.format(deprecated_warn, name),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__)

    subparser.add_argument('-o', '--organization',
                           help="Manage an organizations {}s".format(name))

    group = subparser.add_mutually_exclusive_group(required=True)

    group.add_argument('--copy', nargs=2, metavar=name.upper())

    group.add_argument(
        '--list',
        action='store_true',
        help="{}list all {}s for a user".format(deprecated_warn, name)
    )
    group.add_argument(
        '--show',
        metavar=name.upper(),
        help="{}Show all of the files in a {}".format(deprecated_warn, name)
    )
    group.add_argument(
        '--lock',
        metavar=name.upper(),
        help="{}Lock a {}".format(deprecated_warn, name))
    group.add_argument(
        '--unlock',
        metavar=name.upper(),
        help="{}Unlock a {}".format(deprecated_warn, name)
    )

    group.add_argument(
        '--remove',
        metavar=name.upper(),
        help="{}Remove a {}".format(deprecated_warn, name)
    )
    subparser.set_defaults(main=functools.partial(main, name=name, deprecated=deprecated))

def add_parser(subparsers):
    _add_parser(subparsers, name="label")
    _add_parser(subparsers, name="channel", deprecated=True)
