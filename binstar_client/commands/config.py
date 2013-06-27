'''
Authenticate a user
'''
from binstar_client.utils import get_config, set_config, SITE_CONFIG,\
    USER_CONFIG

def main(args):
    config = get_config()
    
    if args.show:
        print 'Site Config:', SITE_CONFIG
        print get_config(user=False)
        print 'User Config:', USER_CONFIG
        print get_config(site=False)
    
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
    
    set_config(config, args.user)
    

def add_parser(subparsers):
    parser = subparsers.add_parser('config', 
                                      help='Authenticate a user', 
                                      description=__doc__)
    
    parser.add_argument('--type', type=eval, default=str)
    parser.add_argument('--set', nargs=2, action='append', default=[])
    parser.add_argument('--get')
    parser.add_argument('--remove', action='append', default=[])
    parser.add_argument('--show', action='store_true', default=False)
    parser.add_argument('-u', '--user', action='store_true', dest='user',default=True)
    parser.add_argument('-s', '--site', action='store_false', dest='user')
    parser.add_argument('-f','--files', action='store_true')
    
    
    parser.set_defaults(main=main)