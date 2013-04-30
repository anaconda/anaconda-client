'''
Add a new package to your account.
'''
from binstar_client.utils import get_binstar
import json
def main(args):
    
    binstar = get_binstar()
    
    if '/' in args.spec: 
        user, package = args.spec.split('/', 1)
    else:
        user = binstar.user().get('login')
        package = args.spec
        
    if args.attrs:
        with open(args.attrs) as fd:
            attrs = json.load(fd)
    else:
        attrs = {}
    
    if args.action == 'add':
        binstar.add_package(user, package, args.type, 
                            args.summary, args.license, args.license_url, 
                            args.public, attrs)
    elif args.action == 'show':
        print binstar.package(user, package)
    else:
        raise NotImplementedError(args.action)


def add_parser(subparsers):
    
    parser = subparsers.add_parser('package',
                                      help='Add a package',
                                      description=__doc__)
    
    parser.add_argument('action', help='Package name written as either <user>/<package> or just <package>',
                        choices=['add','show'])
    parser.add_argument('spec', help='Package name written as either <user>/<package> or just <package>')
    parser.add_argument('-t', '--type', help='package type (conda, pypi, etc)')
    parser.add_argument('-s', '--summary', help='Summary')
    parser.add_argument('-l', '--license', help='license name default:$(default)s', default='BSD')
    parser.add_argument('--license-url', help='license url', default='http://opensource.org/licenses/BSD-3-Clause')
    parser.add_argument('--public', help='Allow anyone to view and download this package',
                        action='store_true', dest='public', default=True)
    parser.add_argument('--private', help='You choose who can view has access to this package',
                        action='store_false', dest='public')
    parser.add_argument('--attrs', help='a json file containing any extra attributes you want this package to have')
    
    
    
    parser.set_defaults(main=main)
    
    


