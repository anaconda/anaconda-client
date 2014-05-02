'''
Build command

Initialize the build directory:

    binstar build --init
    
This will create a default .binstar.yml file in the current directory
  
Submit a build:

    binstar build --submit
    
Tail the output of a build untill it is complete:

    binstar build --tail 1.0
    
'''

from binstar_client.utils import get_binstar, PackageSpec, bool_input
import logging, yaml
from os.path import abspath, join, isfile, dirname, basename
from binstar_client.errors import UserError
import tempfile
import tarfile
from contextlib import contextmanager
import os
from binstar_client.utils import package_specs
import time
from itertools import product
from binstar_client import errors
import argparse
from binstar_client.utils.build_file import initial_build_config
import sys

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
        log.info(log_item.get('msg'))

    last_entry = log_items['last_entry']

    while args.f and not log_items.get('finished'):
        time.sleep(4)
        log_items = binstar.tail_build(args.package.user, args.package.name, args.tail,
                                       after=last_entry)
        for log_item in log_items['log']:
            log.info(log_item.get('msg'))

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
    build_no = None if args.list is True else args.list
    for build in binstar.builds(args.package.user, args.package.name, build_no):
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


def expand_build_matrix(instruction_set):
    instruction_set = instruction_set.copy()

    platforms = instruction_set.pop('platform', ['linux-64']) or [None]
    if not isinstance(platforms, list): platforms = [platforms]
    envs = instruction_set.pop('env', [None]) or [None]
    if not isinstance(envs, list): envs = [envs]
    engines = instruction_set.pop('engine', ['python=2']) or [None]
    if not isinstance(engines, list): engines = [engines]

    for platform, env, engine in product(platforms, envs, engines):
        build = instruction_set.copy()
        build.update(platform=platform, env=env, engine=engine)
        yield build

def serialize_builds(instruction_sets):
    builds = {}
    for instruction_set in instruction_sets:
        for build in expand_build_matrix(instruction_set):
            k = '%s::%s::%s' % (build['platform'], build['engine'], build['env'])
            bld = builds.setdefault(k, build)
            bld.update(build)

    for k, value in sorted(builds.items()):
        if value.get('exclude'): continue
        yield value


def submit_build(args):
    
    binstar = get_binstar(args)
    
    path = abspath(args.path)
    log.info('Getting build product: %s' % abspath(args.path))

    with open(join(path, '.binstar.yml')) as cfg:
        build_matrix = list(yaml.load_all(cfg))

    builds = list(serialize_builds(build_matrix))
    log.info('Submitting %i sub builds' % len(builds))
    for i, build in enumerate(builds):
        log.info(' %i)' % i + ' %(platform)-10s  %(engine)-15s  %(env)-15s' % build)

    if not args.dry_run:
        with mktemp() as tmp:
            with tarfile.open(tmp, mode='w|bz2') as tf:
                tf.add(path, '.')

            with open(tmp, mode='rb') as fd:

                build_no = binstar.submit_for_build(args.package.user, args.package.name, fd, builds)
        log.info('Build %s submitted' % build_no)
    else:
        log.info('Build not submitted (dry-run)')



def resubmit_build(binstar, args):
    binstar.resubmit_build(args.package.user, args.package.name, args.resubmit)
    



def init_build(args):
    
    binstar = get_binstar()

    # Force user auth
    user = binstar.user()
    
    binstar_yml = join(args.path, '.binstar.yml')
    
    if os.path.exists(binstar_yml):
        result = bool_input("The file '%s' already exists. Would you like to overwrite it?" % binstar_yml,
                            default=False)
        if not result:
            log.error('goodby')
            sys.exit(1)
    
    name = basename(abspath(args.path))
    package_name = raw_input('Please choose a name for this package: (default %s)\n> ' % name)
    package_name = package_name or name
    
          
    with open(binstar_yml, 'w') as fd:
        fd.write(initial_build_config % dict(PACKAGE_NAME=package_name))
    log.info("Wrote file '%s'" % binstar_yml)
    
    try:
        _ = binstar.package(user['login'], package_name)
    except errors.NotFound:
        log.warn('The package %(username)s/%(name)s does not exist\n'
                 'Please run:\n   binstar package %(username)s/%(name)s --create' % dict(username=user['login'], name=package_name))
    log.info("Run 'binstar build --submit' to submit your first build")
    return

def main(args):

    binstar = get_binstar()

    # Force user auth
    user = binstar.user()

    package_name = None
    user_name = None

    binstar_yml = join(args.path, '.binstar.yml')

    if not isfile(binstar_yml):
        raise UserError("file %s does not exist" % binstar_yml)

    with open(binstar_yml) as cfg:
        for build in yaml.load_all(cfg):
            package_name = build.get('package')
            user_name = build.get('user')

    # Force package to exist
    if args.package:
        if user_name and not args.package.user == user_name:
            log.warn('User name does not match the user specified in the .bisntar.yml file (%s != %s)', args.package.user, user_name)
        user_name = args.package.user
        if package_name and not args.package.name == package_name:
            log.warn('Package name does not match the user specified in the .bisntar.yml file (%s != %s)', args.package.name, package_name)
        package_name = args.package.name
    else:
        if user_name is None:
            user_name = user['login']
        if not package_name:
            raise UserError("You must specify the package name in the .bisntar.yml file or the command line")

    try:
        _ = binstar.package(user_name, package_name)
    except errors.NotFound:
        log.error("The package %s/%s does not exist." % (user_name, package_name))
        log.error("Run: 'binstar package --create %s/%s' to create this package" % (user_name, package_name))
        raise errors.NotFound('Package %s/%s' % (user_name, package_name))
    args.package = PackageSpec(user_name, package_name)
        
    if args.resubmit:
        log.info("Re submit build %s", args.resubmit)
        return resubmit_build(binstar, args)
    
    if args.tail:
        return tail(binstar, args)

    if args.halt:
        return halt_build(binstar, args)

    if args.list:
        return list_builds(binstar, args)

def add_parser(subparsers):

    parser = subparsers.add_parser('build',
                                      help='Build command',
                                      description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter,
                                      )

    parser.add_argument('path', default='.', nargs='?')
    parser.add_argument('package', metavar='OWNER/PACKAGE',
                       help='build to the package OWNER/PACKAGE',
                       nargs='?',
                       type=package_specs)
    parser.add_argument('--test-only', '--no-upload', action='store_true',
                        help="Don't upload the build targets to binstar, but run everything else")
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-l', '--list', default=True, type=int,
                       help='List the sub builds for this package')
    group.add_argument('-a', '--list-all', action='store_true',
                       help='List all the builds and sub-builds for this package',
                       dest='list')
    group.add_argument('-t', '--tail', metavar='X.Y',
                       help='Tail the build output of build number X.Y')
    group.add_argument('-s', '--submit',
                       help='Submit the build', action='store_true')
    group.add_argument('--resubmit',
                       help='Res-ubmit an old sub build', type=float)
    group.add_argument('--dry-run',
                       help="Parse the build file but don't submit", action='store_true')


    group.add_argument('--halt', '--stop', metavar='build_id', dest='halt',
                       help='Stop a build for this package')
    group.add_argument('--halt-all', '--stop-all', action='store_const', const='all', dest='halt',
                       help='Stop all builds')


    group = parser.add_argument_group('Tail Options')
    group.add_argument('-n', metavar='#', type=int,
                       help='Number of lines for tail output')
    group.add_argument('-f', action='store_true',
                       help=('The -f option causes tail to not stop when end of current output is reached,'
                             ' but rather to wait for additional data to be appended to the input')
                       )

    parser.set_defaults(main=main)

