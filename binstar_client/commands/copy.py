"""
Copy packages from one account to another
"""
from __future__ import unicode_literals, print_function
from binstar_client.utils import get_server_api, parse_specs
import logging
from binstar_client import errors

logger = logging.getLogger('binstar.copy')


def main(args):
    aserver_api = get_server_api(args.token, args.site)

    spec = args.spec

    channels = aserver_api.list_channels(spec.user)
    label_text = 'label' if (args.from_label and args.to_label) else 'channel'

    from_label = args.from_label
    to_label = args.to_label
    if from_label not in channels:
        raise errors.UserError(
            "{} {} does not exist\n\tplease choose from: {}".format(
                label_text.title(),
                from_label,
                ', '.join(channels)
            ))

    files = aserver_api.copy(
        spec.user, spec.package, spec.version, spec._basename,
        to_owner=args.to_owner, from_label=from_label, to_label=to_label
    )

    for binstar_file in files:
        print("Copied file: %(basename)s" % binstar_file)

    if files:
        logger.info("Copied %i files" % len(files))
    else:
        logger.warning("Did not copy any files. Please check your inputs with\n\n\tanaconda show %s" % spec)


def add_parser(subparsers):
    parser = subparsers.add_parser('copy',
                                      help='Copy packages from one account to another',
                                      description=__doc__)

    parser.add_argument('spec', help=('Package - written as user/package/version[/filename] '
                                      'If filename is not given, copy all files in the version'), type=parse_specs)
    parser.add_argument('--to-owner', help='User account to copy package to (default: your account)')

    _from = parser.add_mutually_exclusive_group()
    _to = parser.add_mutually_exclusive_group()

    _from.add_argument('--from-label', help='Label to copy packages from', default='main')
    _to.add_argument('--to-label', help='Label to put all packages into', default='main')
    parser.set_defaults(main=main)
