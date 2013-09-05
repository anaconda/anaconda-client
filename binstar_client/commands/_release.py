'''
Add a new package to your account.
'''
from binstar_client.utils import get_binstar
from argparse import FileType
def main(args):

    binstar = get_binstar()

    user, package, version = args.spec.split('/', 2)

    if args.announce:
        announce = args.announce.read()
    else:
        announce = ''
    if args.description:
        description = args.description.read()
    else:
        description = ''

    if args.action == 'add':
        binstar.add_release(user, package, version, {}, announce, description)
    elif args.action == 'show':
        release = binstar.release(user, package, version)
        print release
    else:
        raise NotImplementedError(args.action)


def add_parser(subparsers):

    parser = subparsers.add_parser('release',
                                      help='Add a release',
                                      description=__doc__)

    parser.add_argument('action', help='Adde remove or update an existing release',
                        choices=['add', 'remove', 'update', 'show'])
    parser.add_argument('spec', help='Package written as <user>/<package>/<version>')
    parser.add_argument('--requirements', help='TODO')
    parser.add_argument('--announce', help='markdown announcement to notify watchers of a new release',
                        type=FileType('r'))
    parser.add_argument('--description', help='markdown long description of the package',
                        type=FileType('r'))



    parser.set_defaults(main=main)
