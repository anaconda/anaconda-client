from binstar_client.utils import parse_specs, get_binstar, bool_input,\
    get_config
import tarfile
import json
from warnings import warn
from binstar_client import BinstarError, NotFound, Conflict
from os.path import exists
import sys
import time
import yaml
from os.path import basename
from email.parser import Parser
from os import path
import logging

log = logging.getLogger('binstar.updload')

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

def detect_pypi_attrs(filename):
    
    with tarfile.open(filename) as tf:
        pkg_info = next(name for name in tf.getnames() if name.endswith('/PKG-INFO'))
        fd = tf.extractfile(pkg_info)
        attrs = dict(Parser().parse(fd).items())
        
    name = attrs.pop('Name')
    version = attrs.pop('Version')
    summary = attrs.pop('Summary')
    description = attrs.pop('Description')
    license = attrs.pop('License')
    attrs = {'dist':'sdist'}
    
    filename = basename(filename)
    return filename, name, version, attrs, summary, description, license

arch_map = {('osx', 'x86_64'):'osx-64',
            ('win', 'x86'):'win-32',
            ('win', 'x86_64'):'win-64',
            ('linux', 'x86'):'linux-32',
            ('linux', 'x86_64'):'linux-64',
           }

def detect_conda_attrs(filename):
    
    tar = tarfile.open(filename)
    obj = tar.extractfile('info/index.json')
    attrs = json.loads(obj.read())
    
    description, license = detect_yaml_attrs(filename)
    os_arch = arch_map[(attrs['platform'], attrs['arch'])]
    filename = path.join(os_arch, basename(filename))
    return filename, attrs['name'], attrs['version'], attrs, description, description, license

detectors = {'conda':detect_conda_attrs,
             'pypi': detect_pypi_attrs,
             }


def detect_package_type(filename):
    
    if filename.endswith('.tar.bz2'):  # Could be a conda package
        try:
            with tarfile.open(filename) as tf:
                tf.getmember('info/index.json')
        except KeyError:
            pass
        else:
            return 'conda'
    
    if filename.endswith('.tar.gz'):  # Could be a setuptools sdist
        with tarfile.open(filename) as tf:
            if any(name.endswith('/PKG-INFO') for name in tf.getnames()):
                return 'pypi' 
    
    raise BinstarError('Could not autodetect the package type of file %s' % filename) 

def create_package(binstar, username, package_name, summary, license, public=True, publish=True):
    binstar.add_package(username, package_name,
                        summary,
                        license,
                        public=public, 
                        publish=publish)

def create_release(binstar, username, package_name, version, description, announce=None):
    binstar.add_release(username, package_name, version, [],
                        announce, description)


def create_package_interactive(binstar, username, package_name, public=True, publish=True):
    
    log.info('\nThe package %s/%s does not exist' % (username, package_name))
    if not bool_input('Would you lke to create it now?'):
        log.info('goodbbye')
        raise SystemExit(-1)
    
    summary = raw_input('Enter a short description of the package\nsummary: ')
    license = raw_input('Enter the name of the license (default:BSD)\nlicense: ')
    license_url = raw_input('Enter the url of the license (optional)\nlicense url: ')
    public = bool_input('\nDo you want to make this package public?', public)
    if public:
        publish = bool_input('\nDo you want to make publish this package?\n'
                             'When published it will be added to the global public repositories.', 
                             public)
    else:
        publish = False
    
    binstar.add_package(username, package_name,
                    summary,
                    license,
                    license_url,
                    public,
                    public=public, 
                    publish=publish)


def create_release_interactive(binstar, username, package_name, version):
    
    log.info('\nThe release %s/%s/%s does not exist' % (username, package_name, version))
    if not bool_input('Would you like to create it now?'):
        log.info('good-bye')
        raise SystemExit(-1)

    description = raw_input('Enter a short description of the release:\n')    
    log.info("\nAnnouncements are emailed to your package followers.")
    make_announcement = bool_input('Would you like to make an announcement to the package followers?', False)
    if make_announcement:
        announce = raw_input('Markdown Announcement:\n')
    else: 
        announce = ''
    
    binstar.add_release(username, package_name, version, [],
                        announce, description)

def upload_print_callback():
    start_time = time.time()
    def callback(curr, total):
        curr_time = time.time()
        time_delta = curr_time - start_time
    
        remain = total - curr
        if curr and remain:
            eta = 1.0 * time_delta / curr * remain / 60.0
        else:
            eta = 0 
    
        curr_kb = curr // 1024
        total_kb = total // 1024
        perc = 100.0 * curr / total if total else 0
    
        msg = '\r uploaded %(curr_kb)i of %(total_kb)iKb: %(perc).2f%% ETA: %(eta).1f minutes'
        sys.stderr.write(msg % locals())
        sys.stderr.flush()
        if curr == total:
            sys.stderr.write('\n')
            
    return callback

def main(args):
    
    binstar = get_binstar(args)
    
    if args.user:
        username = args.user
    else:
        user = binstar.user()
        username = user ['login']

    uploaded_packages = [] 

    for filename in args.files:

        if not exists(filename):
            raise BinstarError('file %s does not exist' % (filename)) 
    
        if args.package_type:
            package_type = args.package_type
        else:
            log.info('detecting package type ...')
            sys.stdout.flush()
            package_type = detect_package_type(filename)
            log.info(package_type)
        
        get_attrs = detectors[package_type]
    
        if args.metadata:
            attrs = json.loads(args.metadata)
            package_name = args.package
            version = args.version
        else:
            log.info('extracting package attributes for upload ...')
            sys.stdout.flush()
            basefilename, package_name, version, attrs, summary, description, license = get_attrs(filename)
            log.info('done')

        if args.package:
            package_name = args.package

        if args.version:
            version = args.version

        try:
            binstar.package(username, package_name)
        except NotFound:
            if args.mode == 'interactive':
                create_package_interactive(binstar, username, package_name, 
                                           public=args.public,
                                           publish=args.publish) 
            else:
                create_package(binstar, username, package_name, summary, license,
                               public=args.public,
                               publish=args.publish) 


        try:
            binstar.release(username, package_name, version)
        except NotFound:
            if args.mode == 'interactive':
                create_release_interactive(binstar, username, package_name, version)
            else:
                create_release(binstar, username, package_name, version, description)

        with open(filename, 'rb') as fd:
            log.info('\nUploading file %s/%s/%s/%s ... ' % (username, package_name, version, basefilename))
            sys.stdout.flush()
            try:
                binstar.distribution(username, package_name, version, basefilename)
            except NotFound:
                pass
            else:
                if args.mode == 'interactive':
                    if bool_input('Distribution %s already exists. Would you like to replace it?' % (basefilename,)):
                        binstar.remove_dist(username, package_name, version, basefilename)
                    else:
                        log.info('Not replacing distribution %s' % (basefilename,))
                        continue
            try:
                binstar.upload(username, package_name, version, basefilename, fd, package_type, args.description, attrs=attrs,
                           callback=upload_print_callback())
            except Conflict:
                full_name = '%s/%s/%s/%s' % (username, package_name, version, basefilename)
                log.info('Distribution already exists. Please use the -i/--interactive option or `binstar delete %s`' % full_name)
                raise

            uploaded_packages.append(package_name)
            log.info("\n\nUpload(s) Complete\n")
        
    
    for package in uploaded_packages:
        log.info("Package located at:\nhttps://binstar.org/%s/%s\n" % (username, package))
    


def add_parser(subparsers):
    
    config = get_config()
    
    parser = subparsers.add_parser('upload',
                                      help='Upload a file to binstar',
                                      description=__doc__)
    
    parser.add_argument('files', nargs='*', help='Distributions to upload', default=[])

    parser.add_argument('-u', '--user', help='User account, defaults to the current user')
    parser.add_argument('-p', '--package', help='Defaults to the packge name in the uploaded file')
    parser.add_argument('-v', '--version', help='Defaults to the packge version in the uploaded file')
    parser.add_argument('-t', '--package-type', help='Set the package type, defaults to autodetect')
    parser.add_argument('-d', '--description', help='description of the file(s)')
    parser.add_argument('-m', '--metadata', help='json encoded metadata default is to autodetect')
    
    perms = parser.add_mutually_exclusive_group()
    perms.desciption = 'The package permissions'
    perms.add_argument('--public', action='store_true', default=config.get('public') or config.get('publish', True),
                       help='Set the permissions of the package to public (if it does not exist) (default %(default)s)')
    perms.add_argument('--private', action='store_false', dest='public',
                       help='Set the permissions of the package to private (if it does not exist)')
    perms.add_argument('--publish', action='store_true', default=config.get('publish', True),
                       help=('Set the permissions of the package to public and ' 
                             'publish this package to the global public repositories - if it does not exist. '
                            '(default %(default)s)'))
    perms.add_argument('--personal', action='store_false', dest='publish',
                       help=('Set the permissions of the package to public. ' 
                             'Do not publish this to the global public repo. This package will be kept in you user repository.'))
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-i', '--interactive', action='store_const', help='Run an interactive prompt if any packages are missing',
                        dest='mode', const='interactive')
    group.add_argument('-f', '--fail', help='Fail if a package or release does not exist (default)',
                                        action='store_const', dest='mode', const='fail')
    
    parser.set_defaults(main=main)
    
