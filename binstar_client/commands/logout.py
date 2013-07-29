'''
Log out from binstar
'''

from keyring import get_keyring
import getpass
from binstar_client.utils import get_binstar

def main(args):
    
    bs = get_binstar()
    auth = bs.authentication()
    bs.remove_authentication(auth['id'])
    kr = get_keyring()
    kr.delete_password('binstar-token', getpass.getuser())
    print("logout successful")

def add_parser(subparsers):
    subparser = subparsers.add_parser('logout', 
                                      help='Log out from binstar', 
                                      description=__doc__)
    
    subparser.set_defaults(main=main)