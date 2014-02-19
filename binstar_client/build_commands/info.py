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
import time
import logging

log = logging.getLogger('binstar.build')

def tail(args):
    
    binstar = get_binstar(args)
    
    log_items = binstar.tail_build(args.package.user, args.package.name, args.build_no, limit=args.n)
    for log_item in log_items['log']:
        log.info(log_item.get('msg'))

    last_entry = log_items['last_entry']

    while args.f and not log_items.get('finished'):
        time.sleep(4)
        log_items = binstar.tail_build(args.package.user, args.package.name, args.build_no,
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


def list_builds(args):
    
    binstar = get_binstar(args)

    log.info('Getting builds:')

    fmt = '%(build_no)15s | %(status)15s | %(platform)15s | %(engine)15s | %(env)15s'

    header = {'build_no':'Build #', 'status':'Status',
              'platform':'Platform',
              'engine':'Engine',
              'env':'Env',
              }

    log.info(fmt % header)

    log.info(fmt.replace('|', '+') % dict.fromkeys(header, '-' * 15))
    for build in binstar.builds(args.package.user, args.package.name, args.build_no):
        for item in build['items']:
            item.setdefault('status', build.get('status', '?'))
            item['build_no'] = '%s.%s' % (build['build_no'], item['sub_build_no'])
            log.info(fmt % item)
    log.info('')
    return


def add_parser(subparsers):
    parser = subparsers.add_parser('tail',
                                      help='Tail the build output of build number X.Y',
                                      description=__doc__,
                                      )

    parser.add_argument('package', metavar='OWNER/PACKAGE',
                       help='build to the package OWNER/PACKAGE',
                       nargs='?',
                       type=package_specs)
    
    parser.add_argument('build_no',
                       help='Tail the build output of build number X.Y',
                       type=float)

    group = parser.add_argument_group('Tail Options')
    group.add_argument('-n', metavar='#', type=int,
                       help='Number of lines for tail output')
    
    group.add_argument('-f', action='store_true',
                       help=('The -f option causes tail to not stop when end of current output is reached,'
                             ' but rather to wait for additional data to be appended to the input')
                       )

    parser.set_defaults(main=tail)
    #===========================================================================
    # 
    #===========================================================================
    parser = subparsers.add_parser('list-all',
                                      help='list the builds for package',
                                      description=__doc__,
                                      )
    parser.add_argument('package', metavar='OWNER/PACKAGE',
                       help='build to the package OWNER/PACKAGE',
                       nargs='?',
                       type=package_specs)
    parser.set_defaults(main=list_builds, build_no=None)
    #===========================================================================
    # 
    #===========================================================================
    parser = subparsers.add_parser('list',
                                      help='list the builds for package',
                                      description=__doc__,
                                      )
    parser.add_argument('package', metavar='OWNER/PACKAGE',
                       help='build to the package OWNER/PACKAGE',
                       nargs='?',
                       type=package_specs)

    parser.add_argument('build_no',
                       help='Tail the build output of build number X.Y',
                       type=int)
    parser.set_defaults(main=list_builds)


