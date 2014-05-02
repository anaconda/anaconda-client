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

from binstar_client.utils import get_binstar, PackageSpec
import logging, yaml
from os.path import abspath, join, isfile
from binstar_client.errors import UserError
import tempfile
import tarfile
from contextlib import contextmanager
import os
from binstar_client.utils import package_specs
from itertools import product
from binstar_client import errors

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

                build_no = binstar.submit_for_build(args.package.user, args.package.name, fd, builds, 
                                                    test_only=args.test_only)
        log.info('Build %s submitted' % build_no)
    else:
        log.info('Build not submitted (dry-run)')


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
    print "args.package", args.package
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
    
    submit_build(args)
    
    
def add_parser(subparsers):
    parser = subparsers.add_parser('submit',
                                      help='Submit for building',
                                      description=__doc__,
                                      )
    
    parser.add_argument('path', default='.', nargs='?')
    
    parser.add_argument('--test-only', '--no-upload', action='store_true',
                        dest='test_only',
                        help="Don't upload the build targets to binstar, but run everything else")
    
    parser.add_argument('-p', '--package',
                       help="The binstar package namespace to upload the build to", 
                       type=package_specs)
    
    parser.add_argument('-n', '--dry-run',
                       help="Parse the build file but don't submit", action='store_true')

    parser.set_defaults(main=main)
    
    