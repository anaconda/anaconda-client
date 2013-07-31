'''
Print the information of the current user
'''
from binstar_client import Unauthorized
from binstar_client.utils import get_binstar
from dateutil.parser import parse as parse_date

def main(args):
    binstar = get_binstar(args)
    
    try:
        user = binstar.user()
    except Unauthorized:
        return 'Anonymous User'
    
    print 'Username:', user.pop('login') 
    print 'Member since:', parse_date(user.pop('created_at')).ctime()
     
    for key_value in user.items():
        print  '  +%s: %s' % key_value

def add_parser(subparsers):
    subparser = subparsers.add_parser('whoami', 
                                      help='Print the information of the current user', 
                                      description=__doc__)
    
    subparser.set_defaults(main=main)