'''
Binstar package utilities
'''
from binstar_client.utils import get_binstar, parse_specs

def main(args):

    binstar = get_binstar()
    spec = args.spec

    owner = spec.user
    package = spec.package

    if args.add_collaborator:
        collaborator = args.add_collaborator
        binstar.package_add_collaborator(owner, package, collaborator)
        args.add_collaborator
    if args.list_collaborators:
        print ':Collaborators:'
        for collab in binstar.package_collaborators(owner, package):
            print '   +', collab['login']

def add_parser(subparsers):

    parser = subparsers.add_parser('package',
                                      help='Package utils',
                                      description=__doc__)

    parser.add_argument('spec', help='Package to operate on', type=parse_specs)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--add-collaborator', metavar='user', help='username of the collaborator you want to add')
    group.add_argument('--list-collaborators', action='store_true', help='list all of the collaborators in a package')

    parser.set_defaults(main=main)
