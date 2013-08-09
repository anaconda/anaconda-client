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

import logging
from binstar_client.utils.pprint import pprint_user, pprint_packages,\
    pprint_orgs, pprint_collections

log = logging.getLogger('binstar.show')

def main(args):
    
    binstar = get_binstar(args)
    
    spec = args.spec
    if spec._basename:
        dist = binstar.distribution(spec.user, spec.package, spec.version, spec.basename)
        log.info(dist.pop('basename'))
        log.info(dist.pop('description') or 'no description')
        log.info()
        metadata = dist.pop('attrs', {})
        for key_value in dist.items():
            log.info('%-25s: %r' % key_value)
        log.info('Metadata:')
        for key_value in metadata.items():
            log.info('    + %-25s: %r' % key_value)
            
    elif args.spec._version:
        log.info('version %s' % spec.version)
        release = binstar.release(spec.user, spec.package, spec.version)
        for dist in release['distributions']:
            log.info('   + %(basename)s' % dist)
        log.info()
        log.info('%(description)s' % release['public_attrs'])
        
    elif args.spec._package:
        package = binstar.package(spec.user, spec.package)
        package['permission'] = 'public' if package['public'] else 'private'
        log.info('- %(name)s: [%(permission)s] %(summary)s' % package)
        for release in package['releases']:
            log.info('   + %(version)s' % release)
            
    elif args.spec._user:
        user_info = binstar.user(spec.user)
        pprint_user(user_info)
        pprint_packages(binstar.user_packages(spec.user))
        if user_info['user_type'] == 'user':
            pprint_orgs(binstar.user_orgs(spec.user))
        else:
            pprint_collections(binstar.collections(spec.user))
        
    else:
        log.info(args.spec)

def add_parser(subparsers):
    
    parser = subparsers.add_parser('show',
                                      help='Show information about an object',
                                      description=__doc__, formatter_class=RawTextHelpFormatter)
    
    parser.add_argument('spec', help='Package written as <user>[/<package>[/<version>[/<filename>]]]', type=parse_specs)
    
    parser.set_defaults(main=main)
