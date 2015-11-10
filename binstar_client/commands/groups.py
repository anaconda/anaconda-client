from binstar_client.utils import get_server_api, parse_specs
from argparse import FileType, ArgumentError
from os.path import basename
import tarfile
import json
from warnings import warn
from pprint import pprint
import re
from binstar_client.pprintb import package_list, user_list

def group_spec(spec):
    '''
    Spec
    '''
    pat = re.compile('^(?P<org>[a-z][a-z0-9_-]+)(/:(?P<group_name>[a-z][a-z0-9_-]+)(/(?P<member>[a-z][a-z0-9_-]+))?)?$')
    mat = pat.match(spec)
    if mat is None:
        raise ArgumentError('dfasdf')

    return mat.groupdict()

def main(args):

    aserver_api = get_server_api(args.token, args.site, args.log_level)

    if args.action == 'add':
        result = aserver_api.add_group(args.spec['org'], args.spec['group_name'], args.perms)
        pprint(result)
    elif args.action == 'show':
        if args.spec['group_name']:
            result = aserver_api.group(args.spec['org'], args.spec['group_name'])
            pprint(result)
        else:
            result = aserver_api.groups(args.spec['org'])
            pprint(result)

    elif args.action == 'members':
        if not args.spec['group_name']:
            raise ArgumentError('must specify group_name in spec')
        result = aserver_api.group_members(args.spec['org'], args.spec['group_name'])
        user_list(result, args.verbose)
    elif args.action == 'add_member':
        if not args.spec['group_name']:
            raise ArgumentError('must specify group_name in spec')
        if not args.spec['member']:
            raise ArgumentError('must specify group_name in spec')
        aserver_api.add_group_member(args.spec['org'], args.spec['group_name'], args.spec['member'])
    elif args.action == 'remove_member':
        if not args.spec['group_name']:
            raise ArgumentError('must specify group_name in spec')
        if not args.spec['member']:
            raise ArgumentError('must specify group_name in spec')
        aserver_api.remove_group_member(args.spec['org'], args.spec['group_name'], args.spec['member'])
    elif args.action == 'packages':
        if not args.spec['group_name']:
            raise ArgumentError('must specify group_name in spec')
        result = aserver_api.group_packages(args.spec['org'], args.spec['group_name'])
        package_list(result, args.verbose)

    elif args.action == 'add_package':
        if not args.spec['group_name']:
            raise ArgumentError('must specify group_name in spec')
        if not args.spec['member']:
            raise ArgumentError('must specify group_name in spec')
        aserver_api.add_group_package(args.spec['org'], args.spec['group_name'], args.spec['member'])
    elif args.action == 'remove_package':
        if not args.spec['group_name']:
            raise ArgumentError('must specify group_name in spec')
        if not args.spec['member']:
            raise ArgumentError('must specify group_name in spec')
        aserver_api.remove_group_package(args.spec['org'], args.spec['group_name'], args.spec['member'])
    else:
        raise NotImplementedError(args.action)

def add_parser(subparsers):

    parser = subparsers.add_parser('groups',
                                    help='Manage Groups',
                                    description=__doc__)

    parser.add_argument('action', help='asdf',
                        choices=['add', 'show', 'members', 'add_member', 'remove_member',
                                 'packages', 'add_package', 'remove_package'], nargs='?')
    parser.add_argument('spec', help=group_spec.__doc__, nargs='?', type=group_spec)
    parser.add_argument('--perms', help='group permissions', choices=['read', 'write', 'admin'], default='read')


    parser.set_defaults(main=main)
