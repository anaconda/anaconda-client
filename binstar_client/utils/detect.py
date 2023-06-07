# pylint: disable=missing-class-docstring,missing-function-docstring

"""
Package type detection and meta-data extraction
"""

from __future__ import print_function, unicode_literals

import logging
import tarfile

from os import path

from binstar_client.utils.config import PackageType
from binstar_client.inspect_package.conda import inspect_conda_package
from binstar_client.inspect_package import conda_installer
from binstar_client.inspect_package.pypi import inspect_pypi_package
from binstar_client.inspect_package.r import inspect_r_package
from binstar_client.inspect_package.ipynb import inspect_ipynb_package
from binstar_client.inspect_package.env import inspect_env_package

logger = logging.getLogger('binstar.detect')


def file_handler(filename, fileobj, *args, **kwargs):  # pylint: disable=unused-argument
    return ({}, {'description': ''},
            {'basename': path.basename(filename), 'attrs': {}})


inspectors = {
    PackageType.CONDA: inspect_conda_package,
    PackageType.STANDARD_PYTHON: inspect_pypi_package,
    PackageType.STANDARD_R: inspect_r_package,
    PackageType.NOTEBOOK: inspect_ipynb_package,
    PackageType.ENV: inspect_env_package,
    PackageType.INSTALLER: conda_installer.inspect_package,
    PackageType.FILE: file_handler,
}


def is_environment(filename):
    """Return file extension if environment"""
    logger.debug('Testing if environment file ..')
    if filename.endswith('.yml') or filename.endswith('.yaml'):
        return path.split(filename)[1]
    logger.debug('No environment file')
    return None


def is_ipynb(filename):
    logger.debug('Testing if ipynb file ..')
    if filename.endswith('.ipynb'):
        return path.split(filename)[1]
    logger.debug('No ipynb file')
    return None


def is_project(filename):
    logger.debug('Testing if project ..')

    def is_python_file():
        return filename.endswith('.py')

    def is_directory():
        return path.isdir(filename)

    if is_directory() or is_python_file():
        return True
    logger.debug('Not a project')
    return False


def is_conda(filename):
    logger.debug('Testing if conda package ..')
    if filename.endswith('.conda'):
        return path.split(filename)[1]

    if filename.endswith('.tar.bz2'):  # Could be a conda package
        try:
            with tarfile.open(filename, mode='r|bz2') as tar_file:
                for info in tar_file:
                    if info.name == 'info/index.json':
                        break
                else:
                    raise KeyError
        except KeyError:
            logger.debug("Not conda package no 'info/index.json' file in the tarball")
            return None
        logger.debug('This is a conda package')
        return '.'.join(filename.split('.')[-2:])
    logger.debug('Not conda package (file ext is not .tar.bz2 or .conda)')
    return None


def is_pypi(filename):
    package_type_label = PackageType.STANDARD_PYTHON.label()
    logger.debug('Testing if %s package ..', package_type_label)
    if filename.endswith('.whl'):
        logger.debug('This is a %s wheel package', package_type_label)
        return path.split(filename)[1]
    if filename.endswith('.tar.gz') or filename.endswith('.tgz'):  # Could be a setuptools sdist or r source package
        with tarfile.open(filename) as tar_file:
            if any(name.endswith('/PKG-INFO') for name in tar_file.getnames()):
                return '.'.join(filename.split('.')[-2:])
            logger.debug("This is not a %s package (no '/PKG-INFO' in tarball)", package_type_label)
    logger.debug('This is not a %s package (expected .tgz, .tar.gz or .whl)', package_type_label)
    return None


def is_r(filename):
    logger.debug('Testing if R package ..')
    if filename.endswith('.tar.gz') or filename.endswith('.tgz'):  # Could be a setuptools sdist or r source package
        with tarfile.open(filename) as tar_file:

            if (
                    any(name.endswith('/DESCRIPTION') for name in tar_file.getnames()) and
                    any(name.endswith('/NAMESPACE') for name in tar_file.getnames())
            ):
                return '.'.join(filename.split('.')[-2:])
            logger.debug("This not is an R package (no '*/DESCRIPTION' and '*/NAMESPACE' files).")
            return None
    else:
        logger.debug('This not is an R package (expected .tgz, .tar.gz).')
        return None


def get_extension(filename):
    return is_conda(filename) or is_ipynb(filename) or is_pypi(filename) or is_r(filename) or is_environment(filename)


def detect_package_type(filename):  # pylint: disable=too-many-return-statements
    if isinstance(filename, bytes):
        filename = filename.decode('utf-8', errors='ignore')

    if is_conda(filename):  # pylint: disable=no-else-return
        return PackageType.CONDA
    elif is_pypi(filename):
        return PackageType.STANDARD_PYTHON
    elif is_r(filename):
        return PackageType.STANDARD_R
    elif is_ipynb(filename):
        return PackageType.NOTEBOOK
    elif is_environment(filename):
        return PackageType.ENV
    elif conda_installer.is_installer(filename):
        return PackageType.INSTALLER
    elif is_project(filename):
        return PackageType.PROJECT

    return None


def get_attrs(package_type, filename, *args, **kwargs):
    with open(filename, 'rb') as fileobj:
        inspector = package_type.get_from_mapping(inspectors)
        return inspector(filename, fileobj, *args, **kwargs)
