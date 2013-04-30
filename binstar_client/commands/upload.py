'''
Add a new package to your account.
'''
from binstar_client.utils import get_binstar
from argparse import FileType
from os.path import basename
import tarfile
import json

def detect_conda_attrs(file):
    tar = tarfile.open(file)
    obj = tar.extractfile('info/index.json')
    return json.loads(obj.read())

detectors = {'conda':detect_conda_attrs}
def detect(binstar, user, package, file):
    
    package_type = binstar.package(user, package).get('package_type')
    func = detectors.get(package_type, lambda file:{})
    attrs = func(file)
    attrs.pop('version')
    return attrs

def main(args):
    
    binstar = get_binstar()
    
    if args.action == 'upload':
        user, package, version = args.spec.split('/', 2)
        for file in args.files:
            attrs = detect(binstar, user, package, file)
            with open(file) as fd:
                print 'Uploading %s ... ' % file
                binstar.upload(user, package, version, basename(file), fd, args.description, **attrs)
        print '... done'
    elif args.action == 'download':
        user, package, version, fname = args.spec.split('/', 3)
        fd = binstar.download(user, package, version, fname)
        
        if args.files:
            fname = args.files[0]
        data = fd.read()
        with open(fname, 'w') as fdout:
            fdout.write(data)
    else:
        raise NotImplementedError(args.action)
    

def add_parser(subparsers):
    
    parser = subparsers.add_parser('file',
                                      help='Add a release',
                                      description=__doc__)
    
    parser.add_argument('action', help='Adde remove or update an existing release',
                        choices=['upload', 'download', 'remove', 'list'])
    parser.add_argument('spec', help='Package written as <user>/<package>/<version>')
    parser.add_argument('files', nargs='*', help='Distributions to upload', default=[])
    parser.add_argument('-d','--description', help='description of the file(s)')
    
    parser.set_defaults(main=main)
    
    


