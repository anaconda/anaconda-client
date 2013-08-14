'''
Remove an object from binstar:

example::

    binstar remove sean/meta/1.2.0/meta.tar.gz
     
'''
from binstar_client.utils import get_binstar, PackageSpec, parse_specs, \
    bool_input
from argparse import FileType, RawTextHelpFormatter
from binstar_client import NotFound

import logging
log = logging.getLogger('binstar.remove')

def main(args):
    
    binstar = get_binstar(args)
    
    for spec in args.specs:
        try:
            if spec._basename:
                msg = 'Are you sure you want to remove file %s ?' % (spec,)
                if not args.force and bool_input(msg, False):
                    binstar.remove_dist(spec.user, spec.package, spec.version, spec.basename)
                else:
                    log.warn('Not removing file %s' % (spec))
            elif spec._version:
                msg = 'Are you sure you want to remove the package release %s ? (and all files under it?)' % (spec,)
                if not args.force and bool_input(msg, False):
                    binstar.remove_release(spec.user, spec.package, spec.version)
                else:
                    log.warn('Not removing release %s' % (spec))
            elif spec._package:
                msg = 'Are you sure you want to remove the package %s ? (and all data with it?)' % (spec,)
                if not args.force and bool_input(msg, False):
                    binstar.remove_package(spec.user, spec.package)
                else:
                    log.warn('Not removing release %s' % (spec))
            
        except NotFound:
            if args.force:
                continue
            else:
                raise
                 
            
def add_parser(subparsers):
    
    parser = subparsers.add_parser('remove',
                                      help='Remove an object from binstar',
                                      description=__doc__, formatter_class=RawTextHelpFormatter)
    
    parser.add_argument('specs', help='Package written as <user>[/<package>[/<version>[/<filename>]]]', type=parse_specs, nargs='+')
    parser.add_argument('-f', '--force', help='Do not prompt removal', action='store_true')
    
    
    
    parser.set_defaults(main=main)
