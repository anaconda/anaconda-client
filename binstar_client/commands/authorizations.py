'''
Manage Authentication tokens
'''
from binstar_client.utils import get_binstar
import getpass
from dateutil.parser import parse as parse_date


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
        
        username = raw_input('Username: ')
        password = getpass.getpass()
        
        print binstar.authenticate(username, password, 
                                   application='Binstar Cli', application_url='', 
                                   scopes=['read','write'], resource=args.resource, max_age=args.max_age)
        
    
    
def add_parser(subparsers):
    
    parser = subparsers.add_parser('auth',
                                    help='Manage Authorization Tokens',
                                    description=__doc__)
    parser.add_argument('-n','--name')
    parser.add_argument('--max-age', type=int)
    parser.add_argument('--resource', default='api:**')
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-l', '--list', action='store_true')
    group.add_argument('-r', '--remove', metavar='ID', nargs='+')
    group.add_argument('-c', '--create', action='store_true')
    parser.set_defaults(main=main)
    


