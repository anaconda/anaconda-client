'''
Bisntar configuration

Get, Set, Remove or Show the binstar configuration.


'''
from binstar_client.errors import ShowHelp
from binstar_client.utils import get_config, set_config, SITE_CONFIG, \
    USER_CONFIG
from pprint import pprint

def main(args):
    config = get_config()
    
    if args.show:
        fmt = ' + %s: %r'
        print 'Site Config:', SITE_CONFIG
        for key_value in get_config(user=False).items():
            print fmt % key_value
        print
        print 'User Config:', USER_CONFIG
        for key_value in get_config(site=False).items():
            print fmt % key_value
        print
        return
    
    if args.get:
        print config[args.get]
        return
    
    if args.files:
        print 'User Config:', USER_CONFIG 
        print 'Site Config:', SITE_CONFIG
    
    config = get_config(args.user, not args.user)
    
    for key, value in args.set:
        config[key] = args.type(value)
    
    for key in args.remove:
        if key in config:
            del config[key]
            
    if not (args.set or args.remove):
        raise ShowHelp()
    
    set_config(config, args.user)
    

def add_parser(subparsers):
    parser = subparsers.add_parser('config',
                                      help='Bisntar configuration',
                                      description=__doc__)
    
    parser.add_argument('--type', type=eval, default=str, help='The type of the values in the set commands')
    parser.add_argument('--set', nargs=2, action='append', default=[], help='sets a new variable: name value', metavar=('name', 'value'))
    parser.add_argument('--get', help='get value: name', metavar='name')
    parser.add_argument('--remove', action='append', default=[], help='removes a variable')
    parser.add_argument('--show', action='store_true', default=False, help='show all variables')
    parser.add_argument('-u', '--user', action='store_true', dest='user', default=True, help='set a variable for this user')
    parser.add_argument('-s', '--site', action='store_false', dest='user', help='set a variable for all users on this machine')
    parser.add_argument('-f', '--files', action='store_true', help='show the config file names')
    
    
    parser.set_defaults(main=main, sub_parser=parser)
    
