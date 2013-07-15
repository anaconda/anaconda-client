'''
Remove an object from binstar:

example::

    binstar remove sean/meta/1.2.0/meta.tar.gz
     
'''
from binstar_client.utils import get_binstar, PackageSpec, parse_specs,\
    bool_input
from argparse import FileType, RawTextHelpFormatter
from binstar_client import NotFound
def main(args):
    
    binstar = get_binstar()
    
    for spec in args.specs:
        try:
            if not args.force and bool_input('Are you sure you want to remove file %s' % (spec,), False):
                binstar.remove_dist(spec.user, spec.package, spec.version, spec.basename)
            else:
                print 'Not removing file %s' %(spec)
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
    parser.add_argument('-f','--force', help='Do not prompt removal', action='store_true')
    
    
    
    parser.set_defaults(main=main)