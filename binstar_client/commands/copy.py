'''
Copy packages from one account to another
'''
from __future__ import unicode_literals, print_function
from binstar_client.utils import get_binstar, parse_specs
import logging
from binstar_client import errors

log = logging.getLogger('binstar.whoami')

def main(args):
    bs = get_binstar(args)

    spec = args.spec
    channels = bs.list_channels(spec.user)
    if args.from_channel not in channels:
        raise errors.UserError("Channel %s does not exist\n\tplease choose from: %s" % (args.from_channel, ', '.join(channels)))
    files = bs.copy(spec.user, spec.package, spec.version, spec._basename,
                    to_owner=args.to_owner, from_channel=args.from_channel, to_channel=args.to_channel)
    for binstar_file in files:
        print("Copied file: %(basename)s" % binstar_file)

    if files:
        log.info("Copied %i files" % len(files))
    else:
        log.warning("Did not copy any files. Please check your inputs with\n\n\tbinstar show %s" % spec)


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

