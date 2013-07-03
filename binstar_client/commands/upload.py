from binstar_client.utils import parse_specs, get_binstar
import tarfile
import json
from warnings import warn
from binstar_client import BinstarError, NotFound
from os.path import exists
import sys
import time
import yaml


def detect_conda_attrs(filename):
    tar = tarfile.open(filename)
    obj = tar.extractfile('info/index.json')
    attrs = json.loads(obj.read())
    return attrs['name'], attrs['version'], attrs

detectors = {'conda':detect_conda_attrs}

def detect_yaml_attrs(filename):
    tar = tarfile.open(filename)
    obj = tar.extractfile('info/recipe/meta.yaml')
    attrs = yaml.load(obj)
    try:
        description = attrs['about']['home']
    except KeyError:
        description = None
    try:
        license = attrs['about']['license']
    except KeyError:
        license = None

    return description, license 

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

def bool_input(prompt, default=True):
        while 1:
            inpt = raw_input('%s [Y|n]: ' % prompt)
            if inpt.lower() in ['y', 'yes'] and not default:
                return True
            elif inpt.lower() in ['', 'n', 'no'] and not default:
                return False
            elif inpt.lower() in ['', 'y', 'yes']:
                return True
            elif inpt.lower() in ['n', 'no']:
                return False
            else:
                print 'please enter yes or no'

def create_package(binstar,username, package_name, package_type, summary, license):
    binstar.add_package(username, package_name,
                    package_type,
                    summary,
                    license)

def create_release(binstar, username, package_name, package_type, version, description, announce=None):
    binstar.add_release(username, package_name, version, [], 
                        announce, description)


def create_package_interactive(binstar, username, package_name, package_type):
    
    print '\nThe package %s/%s does not exist' % (username, package_name)
    if not bool_input('Would you lke to create it now?'):
        print 'goodbbye'
        raise SystemExit(-1)
    
    summary = raw_input('Enter a short description of the package\nsummary: ')
    license = raw_input('Enter the name of the license (default:BSD)\nlicense: ')
    license_url = raw_input('Enter the url of the license (optional)\nlicense url: ')
    public = bool_input('\nDo you want to make this package public?')
    
    binstar.add_package(username, package_name,
                    package_type,
                    summary,
                    license,
                    license_url,
                    public)

def create_release_interactive(binstar, username, package_name, package_type, version):
    
    print '\nThe release %s/%s/%s does not exist' % (username, package_name, version)
    if not bool_input('Would you like to create it now?'):
        print 'good-bye'
        raise SystemExit(-1)

    description = raw_input('Enter a short description of the release:\n')    
    print("\nAnnouncements are emailed to your package followers.")
    make_announcement = bool_input('Would you like to make an announcement to the package followers?', False)
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

    uploaded_packages = [] 

    for filename in args.files:

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

        description, license = detect_yaml_attrs(filename)
    
        if args.package:
            package_name = args.package

        if args.version:
            version = args.version

        try:
            binstar.package(username, package_name)
        except NotFound:
            if args.mode == 'interactive':
                create_package_interactive(binstar, username, package_name, package_type) 
            else:
                create_package(binstar, username, package_name, package_type, description, license)   

        try:
            binstar.release(username, package_name, version)
        except NotFound:
            if args.mode == 'interactive':
               create_release_interactive(binstar, username, package_name, package_type, version)
            else:
                create_release(binstar, username, package_name, package_type, version, description)

        from os.path import basename
        basefilename = basename(filename)
    
        with open(filename) as fd:
            print '\nUploading file %s/%s/%s/%s ... ' % (username, package_name, version, basefilename)
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

            uploaded_packages.append(package_name)


    print("\n\nUpload(s) Complete\n")        
    for package in uploaded_packages:        
        print("Package located at:\nhttps://binstar.org/%s/%s\n" % (username, package))
    

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
    group.add_argument('-i', '--interactive', action='store_const', help='Run an interactive prompt if any packages are missing', 
                        dest='mode', const='interactive')
    group.add_argument('-f', '--fail', help='Fail if a package or release does not exist (default)', 
                                        action='store_const', dest='mode', const='fail' )
    
    parser.set_defaults(main=main)
    