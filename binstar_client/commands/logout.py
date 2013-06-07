'''
Log out from binstar
'''

from keyring import get_keyring
import getpass
from binstar_client import Binstar
from binstar_client.utils import get_config

def main(args):
    
    config = get_config()
    kr = get_keyring()
    token = kr.get_password('binstar-token', getpass.getuser())
    url = config.get('url', 'https://api.binstar.org')
    bs = Binstar(token, domain=url)
    bs.remove_authentication(token)
    kr.delete_password('binstar-token', getpass.getuser())

def add_parser(subparsers):
    subparser = subparsers.add_parser('logout', 
                                      help='Log out from binstar', 
                                      description=__doc__)
    
    subparser.set_defaults(main=main)
    
    

