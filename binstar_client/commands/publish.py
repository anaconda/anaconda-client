'''
Publish your packages to a common repository
'''
from binstar_client import Unauthorized
from binstar_client.utils import get_binstar, parse_specs
import logging
import sys

def publish(args):
    
    binstar = get_binstar()
    spec = args.spec[0]
    if args.test:
        print binstar.published(spec.user, spec.package)
        return
        
    binstar.publish(spec.user, spec.package)
    
    if not args.quiet:
        package = binstar.package(spec.user, spec.package)
        if 'pypi' in package['package_types']:
            if sys.platform.startswith('win'):
                pypirc = '%HOME%\pip\pip.ini'
            else:
                pypirc = '$HOME/.pip/pip.conf'
            print 
            print 'Package is added to public pypi repository:'
            print 'Please add the following lines to your pip config file (%r)' % (pypirc,)
            print '''[install]
    find-links =
        https://pypi.binstar.org/simple
            '''
        if 'conda' in package['package_types']:
            print 
            print 'Package is added to public conda repository:'
            print 'Please run the following command to add the public chanel to your conda search path'
            print 'conda config --add channel https://conda.binstar.org/public'
    
def unpublish(args):
    
    binstar = get_binstar()
    spec = args.spec[0]
    binstar.unpublish(spec.user, spec.package)
    

def add_parser(subparsers):
    parser1 = subparsers.add_parser('publish',
                                      help='Publish your packages to a common repository',
                                      description=__doc__)
    parser1.add_argument('spec', nargs=1, type=parse_specs, help='Package spec <user>/<package>')
    parser1.add_argument('-q', '--quiet', action='store_true', help="Don't show output")
    parser1.add_argument('-t', '--test', action='store_true', help='test if a package is already published')
    parser1.set_defaults(main=publish)
    
    parser2 = subparsers.add_parser('unpublish',
                                      help='Un-publish your packages from the common repository',
                                      description=__doc__)
    parser2.add_argument('spec', nargs=1, type=parse_specs, help='Package spec <user>/<package>')
    parser2.set_defaults(main=unpublish)
    
