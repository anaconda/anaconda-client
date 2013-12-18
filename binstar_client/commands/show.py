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
from binstar_client.utils.pprint import pprint_user, pprint_packages, \
    pprint_orgs, pprint_collections

log = logging.getLogger('binstar.show')


def install_info(package, package_type):
    if package_type == 'pypi':
        log.info('To install this package with %s run:' % package_type)
        if package['public']:
            url = 'https://pypi.binstar.org/%s/simple' % package['owner']['login']
        else:
            url = 'https://pypi.binstar.org/t/$TOKEN/%s/simple' % package['owner']['login']
        
        log.info('     pip install -i %s %s' % (url, package['name']))
        if package.get('published'):
            log.info('OR: (because it is published)')
            url = 'https://pypi.binstar.org/public/simple'
            log.info('     pip install -i %s %s' % (url, package['name']))
    if package_type == 'conda':
        log.info('To install this package with %s run:' % package_type)
        if package['public']:
            url = 'https://conda.binstar.org/%s' % package['owner']['login']
        else:
            url = 'https://conda.binstar.org/t/$TOKEN/%s' % package['owner']['login']
        
        log.info('     conda install --channel %s %s' % (url, package['name']))
        if package.get('published'):
            log.info('OR: (because it is published)')
            url = 'https://conda.binstar.org/public'
            log.info('     conda install --channel %s %s' % (url, package['name']))


def main(args):

    binstar = get_binstar(args)

    spec = args.spec
    if spec._basename:
        dist = binstar.distribution(spec.user, spec.package, spec.version, spec.basename)
        log.info(dist.pop('basename'))
        log.info(dist.pop('description') or 'no description')
        log.info('')
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
        log.info('%(description)s' % release['public_attrs'])

    elif args.spec._package:
        package = binstar.package(spec.user, spec.package)
        package['access'] = 'published' if package.get('published') else 'public' if package['public'] else 'private'
        log.info('Name:    %(name)s' % package)
        log.info('Summary: %(summary)s' % package)
        log.info('Access:  %(access)s' % package)
        log.info('Package Types:  %s' % ', '.join(package.get('package_types')))
        log.info('Versions:' % package)
        for release in package['releases']:
            log.info('   + %(version)s' % release)
        
        log.info('')
        for package_type in package.get('package_types'):
            install_info(package, package_type)
            
        if not package['public']:
            log.info('To generate a $TOKEN run:')
            log.info('    TOKEN=$(binstar auth --create --name <TOKEN-NAME>)')
            
            

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
