'''
Attach a private key file
'''

from binstar_client.utils import get_binstar
from binstar_client.utils import package_specs
import logging
from argparse import FileType

log = logging.getLogger('binstar.build')

def set_keyfile(args):
    binstar = get_binstar()
    if args.remove:
        binstar.remove_keyfile(args.package.user, args.package.name,
                               getattr(args, 'remote-filename'))
    else:
        content = args.upload.read()
        remote = getattr(args, 'remote-filename')
        binstar.set_keyfile(args.package.user, args.package.name,
                            remote, content)
    
def keyfiles(args):
    binstar = get_binstar()
    for key in binstar.keyfiles(args.package.user, args.package.name):
        print key
    
    
def add_parser(subparsers):
    parser = subparsers.add_parser('keyfiles',
                                      help='list the builds for package',
                                      description=__doc__,
                                      )
    
    parser.add_argument('package', metavar='OWNER/PACKAGE',
                       help='build to the package OWNER/PACKAGE',
                       type=package_specs)
    
    parser.set_defaults(main=keyfiles)
    
    parser = subparsers.add_parser('keyfile',
                                      help='list the builds for package',
                                      description=__doc__,
                                      )
    
    parser.add_argument('package', metavar='OWNER/PACKAGE',
                       help='build to the package OWNER/PACKAGE',
                       type=package_specs)

    parser.add_argument('remote-filename',
                       help='The filename on the build machine')
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-u', '--upload',
                       help='The file', type=FileType('r'))
    group.add_argument('-r', '--remove', action='store_true')
    
    parser.set_defaults(main=set_keyfile)


