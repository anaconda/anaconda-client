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

from binstar_client.utils import get_binstar
from binstar_client.utils import package_specs
import argparse
import logging

log = logging.getLogger('binstar.build')

def halt_build(binstar, args):
    binstar.stop_build(args.package.user, args.package.name, args.halt)
    if args.halt == 'all':
        log.info('Stopping all builds')
    else:
        log.info('Stopping build %s' % args.halt)
    return

def resubmit_build(args):
    
    binstar = get_binstar(args)
    
    binstar.resubmit_build(args.package.user, args.package.name, args.build_no)
    
    log.info("Build %s resubmitted" % args.build_no)


def add_parser(subparsers):

    parser = subparsers.add_parser('resubmit',
                                      help='Resubmit build',
                                      description='Resubmit build',
                                      formatter_class=argparse.RawDescriptionHelpFormatter,
                                      )

    parser.add_argument('package', metavar='OWNER/PACKAGE',
                       help='build to the package OWNER/PACKAGE',
                       nargs='?',
                       type=package_specs)
    
    parser.add_argument('build_no',
                       help='The build to resubmit',
                       type=float)
    
    parser.set_defaults(main=resubmit_build)
    

