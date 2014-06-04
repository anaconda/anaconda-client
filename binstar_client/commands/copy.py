'''
Copy packages from one account to another
'''
from __future__ import unicode_literals
from binstar_client.utils import get_binstar, parse_specs
import logging

log = logging.getLogger('binstar.whoami')

def main(args):
    bs = get_binstar(args)

    spec = args.spec

    result = bs.copy(spec.user, spec.package, spec.version, spec._basename,
                     to_owner=args.to_owner, from_channel=args.from_channel, to_channel=args.to_channel)
    print result


def add_parser(subparsers):
    parser = subparsers.add_parser('copy',
                                      help='Copy packages from one account to another',
                                      description=__doc__)

    parser.add_argument('spec', help=('Package - written as user/package/version[/filename] '
                                      'If filename is not given, copy all files in the version'), type=parse_specs)
    parser.add_argument('--to-owner', help='User account to copy package to (default: your account)')
    parser.add_argument('--from-channel', help='Channel to copy packages from', default='main')
    parser.add_argument('--to-channel', help='Channel to put all packages into', default='main')
    parser.set_defaults(main=main)

