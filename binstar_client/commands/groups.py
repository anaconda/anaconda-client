from binstar_client.utils import get_server_api, parse_specs
from argparse import FileType, ArgumentError
from os.path import basename
import tarfile
import json
from warnings import warn
from pprint import pprint
import re
from binstar_client.pprintb import package_list, user_list

from binstar_client.utils.spec import group_spec



def main(args):

    aserver_api = get_server_api(args.token, args.site, args.log_level)
    spec = args.spec
    action = args.action

    if action == 'add':
        result = aserver_api.add_group(spec.org, spec.group_name, args.perms)
        pprint(result)
    elif action == 'show':
        if spec.group_name:
            result = aserver_api.group(spec.org, spec.group_name)
            pprint(result)
        else:
            result = aserver_api.groups(spec.org)
            pprint(result)

    elif action == 'members':
        result = aserver_api.group_members(spec.org, spec.group_name)
        user_list(result, args.verbose)
    elif action == 'add_member':
        aserver_api.add_group_member(spec.org, spec.group_name, spec.member)
    elif action == 'remove_member':
        aserver_api.remove_group_member(spec.org, spec.group_name, spec.member)
    elif action == 'packages':
        result = aserver_api.group_packages(spec.org, spec.group_name)
        package_list(result, args.verbose)
    elif action == 'add_package':
        aserver_api.add_group_package(spec.org, spec.group_name, spec.member)
    elif action == 'remove_package':
        aserver_api.remove_group_package(spec.org, spec.group_name, spec.member)
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
