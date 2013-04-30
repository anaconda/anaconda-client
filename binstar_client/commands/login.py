'''
Authenticate a user
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
    bs = Binstar(token, domain=url,)
    
    username = raw_input('Username: ')
    password = getpass.getpass()

    token = bs.authenticate(username, password, 'Binstar-Cli', url, ['packages'])
    kr.set_password('binstar-token', getpass.getuser(), token)
    print 'login successful'

def add_parser(subparsers):
    subparser = subparsers.add_parser('login', 
                                      help='Authenticate a user', 
                                      description=__doc__)
    
    subparser.set_defaults(main=main)
    
    

