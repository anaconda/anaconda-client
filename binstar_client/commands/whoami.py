'''
Print the information of the current user
'''
from keyring import get_keyring
import getpass
from binstar_client import Binstar
from binstar_client.utils import get_config, get_binstar

def main(args):
    binstar = get_binstar()
    user = binstar.user()
    for key_value in user.items():
        print  '%s: %s' % key_value

def add_parser(subparsers):
    subparser = subparsers.add_parser('whoami', 
                                      help='Print the information of the current user', 
                                      description=__doc__)
    
    subparser.set_defaults(main=main)
    
    

