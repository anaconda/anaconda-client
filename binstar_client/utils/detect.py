"""
Package type detection and meta-data extraction
"""
from __future__ import print_function, unicode_literals

import logging
import tarfile

from os import path

from binstar_client.inspect_package.conda import inspect_conda_package
from binstar_client.inspect_package import conda_installer
from binstar_client.inspect_package.pypi import inspect_pypi_package
from binstar_client.inspect_package.r import inspect_r_package
from binstar_client.inspect_package.ipynb import inspect_ipynb_package
from binstar_client.inspect_package.env import inspect_env_package

logger = logging.getLogger('binstar.detect')


def file_handler(filename, fileobj, *args, **kwargs):
    return ({}, {'description': ''},
            {'basename': path.basename(filename), 'attrs':{}})

detectors = {
    'conda': inspect_conda_package,
    'pypi': inspect_pypi_package,
    'r': inspect_r_package,
    'ipynb': inspect_ipynb_package,
    'env': inspect_env_package,
    conda_installer.PACKAGE_TYPE: conda_installer.inspect_package,
    'file': file_handler,
}


def is_environment(filename):
    logger.debug("Testing if environment file ..")
    if filename.endswith('.yml') or filename.endswith('.yaml'):
        return True
    logger.debug("No environment file")


def is_ipynb(filename):
    logger.debug("Testing if ipynb file ..")
    if filename.endswith('.ipynb'):
        return True
    logger.debug("No ipynb file")


def is_project(filename):
    logger.debug("Testing if project ..")

    def is_python_file():
        return filename.endswith('.py')

    def is_directory():
        return path.isdir(filename)

    if is_directory() or is_python_file():
        return True
    logger.debug("Not a project")


def is_conda(filename):
    logger.debug("Testing if conda package ..")
    
    if filename.endswith('.tar.bz2'):  # Could be a conda package
        try:
            with tarfile.open(filename, mode="r|bz2") as tf:
                for info in tf:
                    if info.name == "info/index.json":
                        break
                else:
                    raise KeyError
        except KeyError:
            logger.debug("Not conda  package no 'info/index.json' file in the tarball")
            return False
        else:
            logger.debug("This is a conda package")
            return True
    logger.debug("Not conda package (file ext is not .tar.bz2)")


def is_pypi(filename):
    logger.debug("Testing if pypi package ..")
    if filename.endswith('.whl'):
        logger.debug("This is a pypi wheel package")
        return True
    if filename.endswith('.tar.gz') or filename.endswith('.tgz'):  # Could be a setuptools sdist or r source package
        with tarfile.open(filename) as tf:
            if any(name.endswith('/PKG-INFO') for name in tf.getnames()):
                return True
            else:
                logger.debug("This not is a pypi package (no '/PKG-INFO' in tarball)")
                return False

    logger.debug("This not is a pypi package (expected .tgz, .tar.gz or .whl)")


def is_r(filename):
    logger.debug("Testing if R package ..")
    if filename.endswith('.tar.gz') or filename.endswith('.tgz'):  # Could be a setuptools sdist or r source package
        with tarfile.open(filename) as tf:

            if (any(name.endswith('/DESCRIPTION') for name in tf.getnames()) and
                any(name.endswith('/NAMESPACE') for name in tf.getnames())):
                return True
            else:
                logger.debug("This not is an R package (no '*/DESCRIPTION' and '*/NAMESPACE' files).")
    else:
        logger.debug("This not is an R package (expected .tgz, .tar.gz).")


def detect_package_type(filename):
    if isinstance(filename, bytes):
        filename = filename.decode('utf-8', errors='ignore')

    if is_conda(filename):
        return 'conda'
    elif is_pypi(filename):
        return 'pypi'
    elif is_r(filename):
        return 'r'
    elif is_ipynb(filename):
        return 'ipynb'
    elif is_environment(filename):
        return 'env'
    elif conda_installer.is_installer(filename):
        return conda_installer.PACKAGE_TYPE
    elif is_project(filename):
        return 'project'
    else:
        return None


def get_attrs(package_type, filename, *args, **kwargs):
    with open(filename, 'rb') as fileobj:
        return detectors[package_type](filename, fileobj, *args, **kwargs)
