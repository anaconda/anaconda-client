'''
Authenticate a user
'''
from keyring import get_keyring
import getpass
from binstar_client.utils import get_config, get_binstar
from binstar_client.errors import Unauthorized, BinstarError
import sys

def interactive_get_token():
    bs = get_binstar()
    config = get_config()
    
    url = config.get('url', 'https://api.binstar.org')
    
    token = None
    for _ in range(3):
        try:
            username = raw_input('Username: ')
            password = getpass.getpass(stream=sys.stderr)
            token = bs.authenticate(username, password, 'Binstar-Cli', url, ['packages'])
            break
        except Unauthorized:
            print 'Invalid Username password combination'
            continue
    
    if token is None:
        raise BinstarError('Sorry. Please try again')    
            
    return token
    
def interactive_login():
                
    token = interactive_get_token()
            
    kr = get_keyring() 
    kr.set_password('binstar-token', getpass.getuser(), token)
    print 'login successful'
    
def main(args):
    interactive_login()

def add_parser(subparsers):
    subparser = subparsers.add_parser('login',
                                      help='Authenticate a user',
                                      description=__doc__)
    
    subparser.set_defaults(main=main)
