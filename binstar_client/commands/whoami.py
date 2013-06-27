'''
Print the information of the current user
'''
from binstar_client import Unauthorized
from binstar_client.utils import get_binstar

def main(args):
    binstar = get_binstar()
    
    try:
        user = binstar.user()
    except Unauthorized:
        return 'Anonymous User'
    
    for key_value in user.items():
        print  '%s: %s' % key_value

def add_parser(subparsers):
    subparser = subparsers.add_parser('whoami', 
                                      help='Print the information of the current user', 
                                      description=__doc__)
    
    subparser.set_defaults(main=main)