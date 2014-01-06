'''
Build command
'''
from binstar_client.utils import get_binstar
import logging, yaml
from os.path import abspath, join
from binstar_client.errors import UserError
import tempfile
import tarfile
from contextlib import contextmanager
import os
from binstar_client.utils import package_specs
import time

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
        
    
def tail(binstar, args):
    log_items = binstar.tail_build(args.package.user, args.package.name, args.tail, limit=args.n)
    for log_item in log_items['log']:
        print log_item.get('msg')
        
    last_entry = log_items['last_entry']
    while args.f and not log_items.get('finished'):
        time.sleep(4)
        log_items = binstar.tail_build(args.package.user, args.package.name, args.tail,
                                       after=last_entry)
        for log_item in log_items['log']:
            print log_item.get('msg')
        
        last_entry = log_items['last_entry'] or last_entry
    
    if log_items.get('finished'):
        if log_items['failed']:
            log.error('Build Failed')
        else:
            log.info('Build Succedded')
    else:
        log.info('... Build still running ...')
    

def list_builds(binstar, args):
    log.info('Getting builds:')
    fmt = '%(build_no)15s | %(status)15s | %(platform)15s | %(engine)15s | %(env)15s'
    header = {'build_no':'Build #', 'status':'Status',
              'platform':'Platform',
              'engine':'Engine',
              'env':'Env',
              }
    log.info(fmt % header)
    
    log.info(fmt.replace('|', '+') % dict.fromkeys(header, '-' * 15))
    for build in binstar.builds(args.package.user, args.package.name):
        for item in build['items']:
            item.setdefault('status', build.get('status', '?'))
            item['build_no'] = '%s.%s' % (build['build_no'], item['sub_build_no'])
            log.info(fmt % item)
    log.info('')
    return

def halt_build(binstar, args):
    binstar.stop_build(args.package.user, args.package.name, args.halt)
    if args.halt == 'all':
        log.info('Stopping all builds')
    else:
        log.info('Stopping build %s' % args.halt)
    return


def submit_build(binstar, args):
    path = abspath(args.path)
    log.info('Getting build product: %s' % abspath(args.path))
    
    with open(join(path, '.binstar.yml')) as cfg:
        data = yaml.load(cfg)
        
    if 'script' not in data:
        raise UserError('build instruction is not specified in .binstar.yml')
#     if 'build-targets' not in data:    
#         raise UserError('build-targets instruction is not specified in .binstar.yml')
    
    l = lambda item: item if isinstance(item, list) else [item]
    
    platforms = l(data.get('platform', []))
    envs = l(data.get('env', []))
    engines = l(data.get('engine', []))
    
    with mktemp() as tmp:
        with tarfile.open(tmp, mode='w|bz2') as tf:
            tf.add(path, '.')
            
        with open(tmp, mode='r') as fd:
            build_no = binstar.submit_for_build(args.package.user, args.package.name, fd,
                                                platforms=platforms, envs=envs, engines=engines,
                                                )
            
    log.info('Build %s submitted' % build_no)



def main(args):
    
    binstar = get_binstar()
    
    # Force user auth
    binstar.user()
    
    # Force package to exist
    _ = binstar.package(args.package.user, args.package.name)
    
    if args.list:
        return list_builds(binstar, args)
    
    if args.tail:
        return tail(binstar, args)
    
    if args.halt:
        return halt_build(binstar, args)
    
    submit_build(binstar, args)
    
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
    group.add_argument('-t', '--tail',
                       help='Tail the build output')
    
    
    
    group.add_argument('--halt', '--stop', metavar='build_id', dest='halt',
                       help='Stop a build for this package')
    group.add_argument('--halt-all', '--stop-all', action='store_const', const='all', dest='halt',
                       help='Stop all builds')
    group.add_argument('path', default='.', nargs='?')

    group = parser.add_argument_group('Tail Options')
    group.add_argument('-n', metavar='#', type=int,
                       help='Number of lines for tail output')
    group.add_argument('-f', action='store_true',
                       help=('The -f option causes tail to not stop when end of current output is reached,'
                             ' but rather to wait for additional data to be appended to the input')
                       )

    parser.set_defaults(main=main)
    
