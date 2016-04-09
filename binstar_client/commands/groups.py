from argparse import FileType, ArgumentError
import json
import logging
from os.path import basename
from pprint import pprint
import re
import tarfile
from warnings import warn

from binstar_client.pprintb import package_list, user_list
from binstar_client.utils import get_server_api, parse_specs
from binstar_client.utils.spec import group_spec



def main(args):

    aserver_api = get_server_api(args.token, args.site, args.log_level)
    spec = args.spec
    action = args.action
    verbose = args.log_level == logging.DEBUG

    if action == 'add':
        aserver_api.add_group(spec.org, spec.group_name, args.perms)
        print('Created the group %s' % (spec,))
    elif action == 'show':
        if spec._group_name:
            result = aserver_api.group(spec.org, spec.group_name)
            pprint(result)
        else:
            result = aserver_api.groups(spec.org)
            pprint(result)

    elif action == 'members':
        result = aserver_api.group_members(spec.org, spec.group_name)
        user_list(result, verbose)
    elif action == 'add_member':
        aserver_api.add_group_member(spec.org, spec.group_name, spec.member)
        print('Added the user "{spec.member}" to the group "{spec.org}/{spec.group_name}"'.format(spec=spec))
    elif action == 'remove_member':
        aserver_api.remove_group_member(spec.org, spec.group_name, spec.member)
        print('Removed the user "{spec.member}" from the group "{spec.org}/{spec.group_name}"'.format(spec=spec))
    elif action == 'packages':
        result = aserver_api.group_packages(spec.org, spec.group_name)
        package_list(result, verbose)
    elif action == 'add_package':
        aserver_api.add_group_package(spec.org, spec.group_name, spec.member)
        print('Added the package "{spec.member}" to the group "{spec.org}/{spec.group_name}"'.format(spec=spec))
    elif action == 'remove_package':
        aserver_api.remove_group_package(spec.org, spec.group_name, spec.member)
        print('Removed the package "{spec.member}" from the group "{spec.org}/{spec.group_name}"'.format(spec=spec))
    else:
        raise NotImplementedError(args.action)

def add_parser(subparsers):

    parser = subparsers.add_parser('groups',
                                    help='Manage Groups',
                                    description=__doc__)

    parser.add_argument('action',
                        choices=['add', 'show', 'members', 'add_member',
                                 'remove_member', 'packages', 'add_package',
                                 'remove_package'],
                        help='The group management command to execute')
    parser.add_argument('spec', type=group_spec,
                        help=group_spec.__doc__)
    parser.add_argument('--perms', choices=['read', 'write', 'admin'], default='read',
                        help='The permission the group should provide')

    parser.set_defaults(main=main)
