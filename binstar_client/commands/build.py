'''
Build command
'''
from binstar_client.utils import get_binstar, parse_specs
import logging, yaml
from os.path import abspath, join
from binstar_client.errors import UserError
import tempfile
import tarfile
from contextlib import contextmanager
import os
from binstar_client.utils import package_specs
from argparse import ArgumentParser

log = logging.getLogger('binstar.build')

@contextmanager
def mktemp(suffix=".tar.gz", prefix='binstar', dir=None):
    tmp = tempfile.mktemp(suffix, prefix, dir)
    log.debug('Creating temp file: %s' % tmp)
    try:
        yield tmp
    finally:
        log.debug('Removing temp file: %s' % tmp)
        os.unlink(tmp)
        
    
def main(args):
    
    binstar = get_binstar()
    
    # Force user auth
    binstar.user()
    
    # Force package to exist
    _ = binstar.package(args.package.user, args.package.name)
    
    if args.list:
        log.info('Getting builds:')
        fmt = '%(id)24s | %(status)15s'
        log.info(fmt % {'id':'Build Id', 'status':'Status'})
        log.info(fmt.replace('|', '+') % {'id':'-' * 24, 'status':'-' * 15})
        for build in binstar.builds(args.package.user, args.package.name):
            log.info(fmt % build)
        log.info('')
        return
    if args.halt:
        binstar.stop_build(args.package.user, args.package.name, args.halt)
        if args.halt == 'all':
            log.info('Stopping all builds')
        else:
            log.info('Stopping build %s' % args.halt)
        return
    
    path = abspath(args.path)
    log.info('Getting build product: %s' % abspath(args.path))
    
    with open(join(path, '.binstar.yml')) as cfg:
        data = yaml.load(cfg)
        
    if 'build' not in data:
        raise UserError('build instruction is not specified in .binstar.yml')
    if 'build-targets' not in data:    
        raise UserError('build-targets instruction is not specified in .binstar.yml')
    
    with mktemp() as tmp:
        with tarfile.open(tmp, mode='w|bz2') as tf:
            tf.add(path, '.')
            
        with open(tmp, mode='r') as fd:
            binstar.submit_for_build(args.package.user, args.package.name, fd)
    log.info('Build submitted')
    
def add_parser(subparsers):
    
    parser = subparsers.add_parser('build',
                                      help='Build command',
                                      
                                      description=__doc__)
    
    parser.add_argument('package', metavar='OWNER/PACKAGE',
                       help='build to the package OWNER/PACKAGE',
                       type=package_specs)
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-l', '--list', action='store_true',
                       help='List all builds for this package')
    group.add_argument('--halt', '--stop', metavar='build_id', dest='halt',
                       help='Stop a build for this package')
    group.add_argument('--halt-all', '--stop-all', action='store_const', const='all', dest='halt',
                       help='Stop all builds')
    group.add_argument('path', default='.', nargs='?')

    parser.set_defaults(main=main)
    
