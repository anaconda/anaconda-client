'''
Manage your binstar channels

'''
from __future__ import unicode_literals, print_function
from binstar_client.utils import get_binstar
import logging
import argparse

log = logging.getLogger('binstar.channel')

def main(args):
    binstar = get_binstar(args)
    if args.organization:
        owner = args.organization
    else:
        current_user = binstar.user()
        owner = current_user['login']

    if args.copy:
        binstar.copy_channel(args.copy[0], owner, args.copy[1])
        log.info("Copied channel %s to %s" % tuple(args.copy))
    elif args.remove:
        binstar.remove_channel(args.remove, owner)
        log.info("Removed channel %s" % args.remove)
    elif args.list:
        log.info('Channels')
        for channel, info in binstar.list_channels(owner).items():
            if isinstance(info, int):  # OLD API
                log.info((' + %s ' % channel))
            else:
                log.info((' + %s ' % channel) + ('[locked]' if info['is_locked'] else ''))

    elif args.show:
        info = binstar.show_channel(args.show, owner)
        log.info(('Channel %s ' % args.show) + ('[locked]' if info['is_locked'] else ''))
        for f in info['files']:
            log.info('  + %(full_name)s' % f)
    elif args.lock:
        binstar.lock_channel(args.lock, owner)
        log.info("Channel %s is now locked" % args.lock)
    elif args.unlock:
        binstar.unlock_channel(args.unlock, owner)
        log.info("Channel %s is now unlocked" % args.unlock)
    else:
        raise NotImplementedError()

def add_parser(subparsers):
    subparser = subparsers.add_parser('channel',
                                      help='Manage your binstar channels',
                                      formatter_class=argparse.RawDescriptionHelpFormatter,
                                      description=__doc__)

    subparser.add_argument('-o', '--organization',
                           help="Manage an organizations channels")

    group = subparser.add_mutually_exclusive_group(required=True)
    group.add_argument('--copy', nargs=2, metavar='CHANNEL')
    group.add_argument('--list', action='store_true',
                       help="list all channels for a user")
    group.add_argument('--show', metavar='CHANNEL',
                       help="Show all of the files in a channel")
    group.add_argument('--lock', metavar='CHANNEL',
                       help="Lock a channel")
    group.add_argument('--unlock', metavar='CHANNEL',
                       help="Unlock a channel")

    group.add_argument('--remove', metavar='CHANNEL',
                       help="Remove a channel")

    subparser.set_defaults(main=main)
