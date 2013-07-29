'''
Manage Authentication tokens
'''
from binstar_client.utils import get_binstar
import getpass
from dateutil.parser import parse as parse_date
import sys


def show_auths(authentications):
    header = {'id': 'ID', 'application': 'Application',
              'remote_addr':'Remote Addr',
              'hostname':'Host',
              'resource':'Resource',
              'expires':'Expires'}
    
    template = '%(id)-25s | %(application)-20s | %(remote_addr)-20s | %(hostname)-20s | %(resource)-20s | %(expires)-20s'
    print
    print template % header
    print '%s-+-%s-+-%s-+-%s-+-%s-+-%s' % ('-' * 25, '-' * 20, '-' * 20, '-' * 20, '-' * 20, '-' * 20)
    
    for auth in authentications:
        if auth['expires']:
            auth['expires'] = parse_date(auth['expires']).ctime()
        print template % auth


def main(args):
    binstar = get_binstar(args)
    if args.list:
        show_auths(binstar.authentications())
    if args.remove:
        for auth_id in args.remove:
            binstar.remove_authentication(auth_id)
            
    if args.create:
        
        sys.stderr.write('Username: ')
        sys.stderr.flush()
        username = raw_input('')
        password = getpass.getpass()
        
        print binstar.authenticate(username, password, 
                                   args.name, application_url=args.url, 
                                   scopes=['read','write'], 
                                   resource=args.resource, max_age=args.max_age)
        
    
    
def add_parser(subparsers):
    
    parser = subparsers.add_parser('auth',
                                    help='Manage Authorization Tokens',
                                    description=__doc__)
    parser.add_argument('-n','--name', default='Binstar Cli', help='The name of the application that will use this token')
    parser.add_argument('--url', default='http://binstar.org', help='The url of the application that will use this token')
    parser.add_argument('--max-age', type=int, help='The maximum age in seconds that this token will be valid for')
    parser.add_argument('--resource', default='api:**', help='The resource path that this token is valid')
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-l', '--list', action='store_true', help='list all user authentication tokens')
    group.add_argument('-r', '--remove', metavar='ID', nargs='+', help='remove authentication tokens')
    group.add_argument('-c', '--create', action='store_true', help='Create an authentication token')
    parser.set_defaults(main=main)
    


