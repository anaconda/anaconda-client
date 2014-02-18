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

from binstar_client.utils import get_binstar, bool_input
import logging
from os.path import abspath, join, basename
import os
from binstar_client import errors
from binstar_client.utils.build_file import initial_build_config
import sys

log = logging.getLogger('binstar.build')

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

def add_parser(subparsers):
    parser = subparsers.add_parser('init',
                                      help='Initialize Build file',
                                      description=__doc__,
                                      )
    parser.add_argument('path', default='.', nargs='?')
    parser.set_defaults(main=init_build)


