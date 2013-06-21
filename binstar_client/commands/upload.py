'''
Upload a file to binstar:

Examples:


'''
from binstar_client.utils import parse_specs, get_binstar
import tarfile
import json
from warnings import warn
from binstar_client import BinstarError, NotFound
from os.path import exists
import sys
import time


def detect_conda_attrs(filename):
    tar = tarfile.open(filename)
    obj = tar.extractfile('info/index.json')
    attrs = json.loads(obj.read())
    return attrs['name'], attrs['version'], attrs

detectors = {'conda':detect_conda_attrs}
    
def detect_package_type(binstar, username, package_name, filename):
    
    if filename.endswith('.tar.bz2'):
        try:
            with tarfile.open(filename) as tf:
                tf.getmember('info/index.json')
        except KeyError:
            pass
        else:
            return 'conda'
    
    if package_name:
        
        return binstar.package(username, package_name).get('package_type')
    
    raise BinstarError('Could not autodetect the package type of file %s' % filename) 

def bool_input(prompt):
    while 1:
        inpt = raw_input('%s [Y|n]: ' % prompt)
        if inpt.lower() in ['', 'y', 'yes']:
            return True
        elif inpt.lower() in ['n', 'no']:
            return False
        else:
            print 'please enter yes or no'
    
def create_package_interactive(binstar, username, package_name, package_type):
    
    print 'The package %s/%s does not exist' % (username, package_name)
    if not bool_input('Would you lke to create it now?'):
        print 'goodbbye'
        raise SystemExit(-1)
    
    summary = raw_input('Enter a short description of the package\nsummary: ')
    license = raw_input('Enter the name of the license (default:BSD)\nlicense: ')
    license_url = raw_input('Enter the url of the license (optional)\nlicense url: ')
    public = bool_input('Do you want to make this package public?')
    
    binstar.add_package(username, package_name,
                    package_type,
                    summary,
                    license,
                    license_url,
                    public)


def create_release_interactive(binstar, username, package_name, package_type, version):
    
    print 'The release %s/%s/%s does not exist' % (username, package_name, version)
    if not bool_input('Would you lke to create it now?'):
        print 'goodbbye'
        raise SystemExit(-1)
    description = raw_input('Description:\n')
    make_announcement = bool_input('Would you like to make an announcement to the package followers?')
    if make_announcement:
        announce = raw_input('Markdown Announcement:\n')
    else:
        announce = ''
    
    binstar.add_release(username, package_name, version, [], 
                        announce, description)


def main(args):
    
    binstar = get_binstar()
    
    if args.user:
        username = args.user
    else:
        user = binstar.user()
        username = user ['login']
    
    filename = args.files[0]

    if not exists(filename):
        raise BinstarError('file %s does not exist' %(filename)) 
    
    if args.package_type:
        package_type = args.package_type
    else:
        print 'detecting package type ...', 
        sys.stdout.flush()
        package_type = detect_package_type(binstar, username, args.package, filename)
        print package_type
        
    get_attrs = detectors[package_type]
    
    if args.metadata:
        attrs = json.loads(args.metadata)
        package_name = args.package
        version = args.version
    else:
        print 'extracting package attributes for upload ...',
        sys.stdout.flush()
        package_name, version, attrs = get_attrs(filename)
        print 'done'
    
    if args.package:
        package_name = args.package

    if args.version:
        version = args.version

    try:
        binstar.package(username, package_name)
    except NotFound:
        create_package_interactive(binstar, username, package_name, package_type) 

    try:
        binstar.release(username, package_name, version)
    except NotFound:
        create_release_interactive(binstar, username, package_name, package_type, version)
    
    from os.path import basename
    basefilename = basename(filename)
    
    with open(filename) as fd:
        print 'Uploading file %s/%s/%s/%s ... ' % (username, package_name, version, basefilename)
        sys.stdout.flush()
        
        start_time = time.time()
        def callback(curr, total):
            curr_time = time.time()
            time_delta = curr_time - start_time
            
            remain = total - curr
            if curr and remain:
                eta =  1.0 * time_delta / curr * remain / 60.0
            else:
                eta = 0 
            
            curr_kb = curr//1024
            total_kb = total//1024
            perc = 100.0 * curr / total if total else 0
            
            msg = '\r uploaded %(curr_kb)i of %(total_kb)iKb: %(perc).2f%% ETA: %(eta).1f minutes'
            print msg % locals(),
            sys.stdout.flush()
            if curr == total:
                print
        
        binstar.upload(username, package_name, version, basefilename, fd, args.description, attrs=attrs, 
                       callback=callback)
        print 
        print 'done'
    
    
#     detect(binstar, user, package, file)

def add_parser(subparsers):
    
    
    parser = subparsers.add_parser('upload',
                                      help='Upload a file to binstar',
                                      description=__doc__)
    
    parser.add_argument('files', nargs='*', help='Distributions to upload', default=[])
    
    parser.add_argument('-u', '--user', help='User account, defaults to the current user')
    parser.add_argument('-p', '--package', help='Defaults to the packge name in the uploaded file')
    parser.add_argument('-v', '--version', help='Defaults to the packge version in the uploaded file')
    parser.add_argument('-t', '--package-type', help='Set the package type, defaults to autodetect')
    parser.add_argument('-d','--description', help='description of the file(s)')
    parser.add_argument('-m','--metadata', help='json encoded metadata default is to autodetect')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-f', '--fail', help='Fail if a package or release does not exist (default)', 
                                        action='store_const', dest='mode', const='fail' )
    
    parser.set_defaults(main=main)
    
    


