'''
Created on Jan 2, 2014

@author: sean
'''
import tarfile
import json
import yaml
from os.path import basename
from email.parser import Parser
from os import path

def detect_yaml_attrs(filename):
    tar = tarfile.open(filename)

    try:
        obj = tar.extractfile('info/recipe/meta.yaml')
    except KeyError:
        return None, None

    attrs = yaml.load(obj)
    about = attrs.get('about', {})
    summary = about.get('summary')
    home_page = about.get('home')
    description = about.get('description')
    license = about.get('license')

    return summary, description, home_page, license

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

    summary, description, home_page, license = detect_yaml_attrs(filename)
    attrs['home_page'] = home_page
    os_arch = arch_map[(attrs['platform'], attrs['arch'])]
    filename = path.join(os_arch, basename(filename))
    return filename, attrs['name'], attrs['version'], attrs, summary, description, license

def detect_r_attrs(filename):

    with tarfile.open(filename) as tf:
        pkg_info = next(name for name in tf.getnames() if name.endswith('/DESCRIPTION'))
        fd = tf.extractfile(pkg_info)
        raw_attrs = dict(Parser().parse(fd).items())
    print raw_attrs.keys()
    
    name = raw_attrs.pop('Package')
    version = raw_attrs.pop('Version')
    summary = raw_attrs.pop('Title', None)
    description = raw_attrs.pop('Description', None)
    license = raw_attrs.pop('License', None)
    
    attrs = {}
    attrs['NeedsCompilation'] = raw_attrs.get('NeedsCompilation', 'no')
    attrs['depends'] = raw_attrs.get('Depends', '').split(',')
    attrs['suggests'] = raw_attrs.get('Suggests', '').split(',')
    
    built = raw_attrs.get('Built')
    
    if built:
        r, _, date, platform = built.split(';')
        r_version = r.strip('R ')
        attrs['R'] = r_version
        attrs['os'] = platform.strip()
        attrs['type'] = 'package'
    else:
        attrs['type'] = 'source'
    
    return filename, name, version, attrs, summary, description, license


#===============================================================================
# 
#===============================================================================

detectors = {'conda':detect_conda_attrs,
             'pypi': detect_pypi_attrs,
             'r': detect_r_attrs,
             }


def is_conda(filename):
    if filename.endswith('.tar.bz2'):  # Could be a conda package
        try:
            with tarfile.open(filename) as tf:
                tf.getmember('info/index.json')
        except KeyError:
            return False
        else:
            return True
    
def is_pypi(filename):
    if filename.endswith('.tar.gz') or filename.endswith('.tgz'):  # Could be a setuptools sdist or r source package
        with tarfile.open(filename) as tf:
            if any(name.endswith('/PKG-INFO') for name in tf.getnames()):
                return True

def is_r(filename):
    if filename.endswith('.tar.gz') or filename.endswith('.tgz'):  # Could be a setuptools sdist or r source package
        with tarfile.open(filename) as tf:
            
            if (any(name.endswith('/DESCRIPTION') for name in tf.getnames()) and 
                any(name.endswith('/NAMESPACE') for name in tf.getnames())):
                return True

def detect_package_type(filename):
    
    if is_conda(filename):
        return 'conda'
    elif is_pypi(filename):
        return 'pypi'
    elif is_r(filename):
        return 'r'
    else:
        return None


def get_attrs(package_type, filename):
    return detectors[package_type](filename)
