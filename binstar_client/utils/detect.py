'''
Package type detection and meta-data extraction
'''
from __future__ import print_function, unicode_literals

import logging
from os import path
import tarfile

from binstar_client.inspect_package.conda import inspect_conda_package
from binstar_client.inspect_package import conda_installer
from binstar_client.inspect_package.pypi import inspect_pypi_package
from binstar_client.inspect_package.r import inspect_r_package
from binstar_client.inspect_package.ipynb import inspect_ipynb_package

log = logging.getLogger('binstar.detect')
#===============================================================================
#
#===============================================================================

def file_handler(filename, fileobj, *args, **kwargs):
    return ({}, {'description': ''},
            {'basename': path.basename(filename), 'attrs':{}})

detectors = {'conda':inspect_conda_package,
             'pypi': inspect_pypi_package,
             'r': inspect_r_package,
             'ipynb': inspect_ipynb_package,
             conda_installer.PACKAGE_TYPE: conda_installer.inspect_package,
             'file': file_handler,
             }


def is_ipynb(filename):
    log.debug("Testing if ipynb file ..")
    if filename.endswith('.ipynb'):
        return True
    log.debug("No ipynb file")


def is_conda(filename):
    log.debug("Testing if conda package ..")
    if filename.endswith('.tar.bz2'):  # Could be a conda package
        try:
            with tarfile.open(filename) as tf:
                tf.getmember('info/index.json')
        except KeyError:
            log.debug("Not conda  package no 'info/index.json' file in the tarball")
            return False
        else:
            log.debug("This is a conda package")
            return True
    log.debug("Not conda package (file ext is not .tar.bz2)")


def is_pypi(filename):
    log.debug("Testing if pypi package ..")
    if filename.endswith('.whl'):
        log.debug("This is a pypi wheel package")
        return True
    if filename.endswith('.tar.gz') or filename.endswith('.tgz'):  # Could be a setuptools sdist or r source package
        with tarfile.open(filename) as tf:
            if any(name.endswith('/PKG-INFO') for name in tf.getnames()):
                return True
            else:
                log.debug("This not is a pypi package (no '/PKG-INFO' in tarball)")
                return False

    log.debug("This not is a pypi package (expected .tgz, .tar.gz or .whl)")

def is_r(filename):
    log.debug("Testing if R package ..")
    if filename.endswith('.tar.gz') or filename.endswith('.tgz'):  # Could be a setuptools sdist or r source package
        with tarfile.open(filename) as tf:

            if (any(name.endswith('/DESCRIPTION') for name in tf.getnames()) and
                any(name.endswith('/NAMESPACE') for name in tf.getnames())):
                return True
            else:
                log.debug("This not is an R package (no '*/DESCRIPTION' and '*/NAMESPACE' files).")
    else:
        log.debug("This not is an R package (expected .tgz, .tar.gz).")

def detect_package_type(filename):
    if is_conda(filename):
        return 'conda'
    elif is_pypi(filename):
        return 'pypi'
    elif is_r(filename):
        return 'r'
    elif is_ipynb(filename):
        return 'ipynb'
    elif conda_installer.is_installer(filename):
        return conda_installer.PACKAGE_TYPE
    else:
        return None


def get_attrs(package_type, filename, *args, **kwargs):
    with open(filename, 'rb') as fileobj:
        return detectors[package_type](filename, fileobj, *args, **kwargs)
