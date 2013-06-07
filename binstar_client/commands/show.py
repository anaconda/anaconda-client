'''
Show information about an object:

example::

    * binstar show continuumio
    * binstar show continuumio/python
    * binstar show continuumio/python/2.7.5

    binstar show sean/meta/1.2.0/meta.tar.gz
    
     
'''
from binstar_client.utils import get_binstar, PackageSpec, parse_specs
from argparse import FileType, RawTextHelpFormatter
def main(args):
    
    binstar = get_binstar()
    
    spec = args.spec
    if spec._basename:
        print 'file'
    elif args.spec._version:
        print 'version', spec.version
        release = binstar.release(spec.user, spec.package, spec.version)
        for dist in release['distributions']:
            print '   + %(basename)s' % dist, ' platform:%(platform)-10s arch:%(arch)-10s' % dist['attrs']
        print 
        print '%(description)s' % release['public_attrs']
        
    elif args.spec._package:
        package = binstar.package(spec.user, spec.package)
        package['permission'] = 'public' if package['public'] else 'private'
        print '- %(name)s: [%(permission)s] %(summary)s'  % package
        for release in package['releases']:
            print '   + %(version)s' % release
            
    elif args.spec._user:
        print binstar.user(spec.user)
        for package in binstar.user_packages(spec.user):
            package['permission'] = 'public' if package['public'] else 'private'
            print '   + %(name)25s: [%(permission)s] %(summary)s'  % package
    else:
        print args.spec

def add_parser(subparsers):
    
    parser = subparsers.add_parser('show',
                                      help='Show information about an object',
                                      description=__doc__, formatter_class=RawTextHelpFormatter)
    
    parser.add_argument('spec', help='Package written as <user>[/<package>[/<version>[/<filename>]]]', type=parse_specs)
    
    
    
    parser.set_defaults(main=main)
    
    


