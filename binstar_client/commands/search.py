'''
Search Anaconda Cloud for packages
'''
from binstar_client.utils import get_server_api
from binstar_client.utils.pprint import pprint_packages
import logging
log = logging.getLogger('binstar.search')

def search(args):

    aserver_api = get_server_api(args.token, args.site, args.log_level)

    log.info("Run 'anaconda show <USER/PACKAGE>' to get more details:")
    packages = aserver_api.search(args.name, package_type=args.package_type)
    pprint_packages(packages, access=False)
    log.info("Found %i packages" % len(packages))


def add_parser(subparsers):
    parser1 = subparsers.add_parser('search',
                                      help='Search Anaconda Cloud',
                                      description='Search Anaconda Cloud',
                                      epilog=__doc__)
    parser1.add_argument('name', nargs=1, help='Search string')
    parser1.add_argument('-t', '--package-type', choices=['conda', 'pypi'],
                         help='only search for packages of this type')
    parser1.set_defaults(main=search)
