'''
Build command
'''
from binstar_client import Unauthorized
from binstar_client.utils import get_binstar, parse_specs
import logging
import sys

def main(args):
    
    binstar = get_binstar()
    
    binstar.trigger_build( __data__ )
    
    
def add_parser(subparsers):
    
    parser = subparsers.add_parser('build',
                                      help='Build command',
                                      description=__doc__)
    parser.set_defaults(main=main)
    
