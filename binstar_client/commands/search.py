'''
Search binstar for packages
'''
from binstar_client.utils import get_binstar
from binstar_client.utils.pprint import pprint_packages
import logging
log = logging.getLogger('binstar.search')

def search(args):

    binstar = get_binstar(args)

    log.info("Run 'binstar show <USER/PACKAGE>' to get more details:")
    packages = binstar.search(args.name, package_type=args.package_type)
    pprint_packages(packages, access=False)
    log.info("Found %i packages" % len(packages))


def add_parser(subparsers):
    parser1 = subparsers.add_parser('search',
                                      help='Search binstar',
                                      description='Search binstar',
                                      epilog=__doc__)
    parser1.add_argument('name', nargs=1, help='Search string')
    parser1.add_argument('-t', '--package-type', choices=['conda', 'pypi'],
                         help='only search for packages of this type')
    parser1.set_defaults(main=search)


