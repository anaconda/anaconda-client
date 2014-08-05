from __future__ import print_function, unicode_literals

from binstar_client.inspect_package.conda import inspect_conda_package
from binstar_client.inspect_package.pypi import inspect_pypi_package
from binstar_client.inspect_package.r import inspect_r_package
import tarfile

#===============================================================================
#
#===============================================================================

detectors = {'conda':inspect_conda_package,
             'pypi': inspect_pypi_package,
             'r': inspect_r_package,
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
    if filename.endswith('.whl'):
        return True
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
    with open(filename) as fileobj:
        return detectors[package_type](filename, fileobj)
