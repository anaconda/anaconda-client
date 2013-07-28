'''
Manage Collections


'''
from binstar_client.utils import get_config, get_binstar
from collections import namedtuple
from binstar_client.errors import BinstarError

CollectionSpec = namedtuple('CollectionSpec', ('org','name'))

def collection_spec_opt(spec):
    if '/' not in spec:
        return CollectionSpec(spec, None)
    else:  
        org, name = spec.split('/')
        return CollectionSpec(org, name)
    
def collection_spec(spec):
    org, name = spec.split('/')
    return CollectionSpec(org, name)

def package_spec(spec):
    org, name = spec.split('/')
    return CollectionSpec(org, name)


def show_collections(binstar, spec):
    for collection in binstar.collections(spec.org):
        collection['access'] = '[public]' if collection['public'] else '[private]'
        print '%(access)9s %(owner)s/%(name)-15s - %(description)s' % collection



def show_collection(binstar, spec):
    collection = binstar.collection(spec.org, spec.name)
    collection['access'] = 'public' if collection['public'] else 'private'
    print '[%(access)s] %(owner)s/%(name)-15s - %(description)s' % collection
    print ':Packages:'
    if collection['packages']:
        for package in collection['packages']:
            print '   + %(full_name)25s: %(summary)s'  % package

        print ''
    else:
        print '    This collection contains no packages. You can add a package with the binstar with the command'
        print '    binstar collection --add-package ORG/NAME OWNER/PACKAGE'


def main(args):
    config = get_config()
    
    binstar = get_binstar()
    
    spec = args.spec[0]
    org = spec.org
    name = spec.name
    
    if args.show:
        if name:
            show_collection(binstar, spec)
        else:
            show_collections(binstar, spec)
        return 
    
    if not name:
        raise BinstarError('invaid collection spec')

    if args.create:
        public = True if args.public is None else args.public
         
        binstar.add_collection(org, name, 
                               public=public, description=args.description)
        
    if args.update:
        binstar.update_collection(org, name, 
                               public=args.public, description=args.description)
        
    if args.remove:
        binstar.remove_collection(org, name)
        
    if args.add_package:
        package = args.add_package
        
        binstar.collection_add_packages(org, name,
                                        owner=package.org, package=package.name)
        
    if args.remove_package:
        package = args.remove_package
        
        binstar.collection_remove_packages(org, name,
                                        owner=package.org, package=package.name)
    
    if args.clone_from:
        binstar.collection_clone(args.clone_from.org, args.clone_from.name,
                                 org, name)
    if args.pull_from:
        binstar.collection_pull(args.pull_from.org, args.pull_from.name,
                                 org, name)
    
    
def show(args):
    print 'show'

def add_parser(subparsers):
    
    parser = subparsers.add_parser('collections',
                                    help='Manage Collections',
                                    description=__doc__)
    
    parser.add_argument('spec', nargs=1, help='Collection or organization', type=collection_spec_opt)
    parser.add_argument('-d','--description', help='Set the description of a collection')
    parser.add_argument('--public', help='Set a the access of a collection to public',
                        action='store_true', default=None)
    parser.add_argument('--private', help='Set a the access of a collection to private',
                        dest='public', action='store_false')
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--show', help='Show the collection <NAME> in <ORG>', action='store_true')
    
    group.add_argument('--create', help='create the collection <NAME> in <ORG>', action='store_true')
    group.add_argument('--update', help='update the collection <NAME> in <ORG>', action='store_true')
    group.add_argument('--remove', help='remove the collection <NAME> from <ORG>', action='store_true')
    
    group.add_argument('--add-package', metavar='OWNER/PACKAGE', help='add the package OWNER/PACKAGE to the collection ORG/NAME', type=package_spec)
    group.add_argument('--remove-package', metavar='OWNER/PACKAGE', help='remove the package OWNER/PACKAGE from the collection ORG/NAME', type=package_spec)
    
    group.add_argument('--clone-from',metavar='FROM/NAME', help='Create a collection by cloning another collection', type=collection_spec)
    group.add_argument('--pull-from', metavar='FROM/NAME', help='Update this collection with another', type=collection_spec)
    
    
    parser.set_defaults(main=main, sub_parser=parser)
