'''
Print the information of the current user
'''
from binstar_client import Unauthorized
from binstar_client.utils import get_binstar
from binstar_client.utils.pprint import pprint_user

def main(args):
    binstar = get_binstar(args)
    
    try:
        user = binstar.user()
    except Unauthorized:
        print 'Anonymous User'
        return -1
    
    pprint_user(user)
    
def add_parser(subparsers):
    subparser = subparsers.add_parser('whoami', 
                                      help='Print the information of the current user', 
                                      description=__doc__)
    
    subparser.set_defaults(main=main)