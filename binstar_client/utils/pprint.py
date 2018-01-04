'''
Created on Aug 8, 2013

@author: sean
'''
from __future__ import unicode_literals
from dateutil.parser import parse as parse_date
import logging

logger = logging.getLogger('binstar.pprint')

fmt_access = '     %(full_name)-25s | %(latest_version)8s | %(access)-12s | %(package_types)-15s | %(conda_platforms)-15s | %(builds)-10s'
fmt_no_access = '     %(full_name)-25s | %(latest_version)8s | %(package_types)-15s | %(conda_platforms)-15s | %(builds)-10s'


def pprint_orgs(orgs):
    logger.info('Organizations:')
    for org in orgs:
        logger.info('   + %(login)25s' % org)


def pprint_package_header(access=True, revisions=False):
    package_header = {
        'full_name': 'Name',
        'access': 'Access',
        'package_types': 'Package Types',
        'latest_version': 'Version',
        'conda_platforms': 'Platforms',
        'revision': 'Rev',
        'builds': 'Builds',
    }

    fmt = fmt_access if access else fmt_no_access
    if revisions:
        fmt = '%(revision)-6s | ' + fmt

    logger.info(fmt % package_header)


def pprint_package(package, access=True, full_name=True, revision=False):
    package = package.copy()

    package['access'] = 'published' if package.get('published') else 'public' if package['public'] else 'private'

    if package.get('conda_platforms'):
        package['conda_platforms'] = ', '.join(str(x) for x in package['conda_platforms'] if x is not None)

    if not full_name:
        package['full_name'] = package['name']

    if package.get('package_types'):
        package['package_types'] = ', '.join(str(x) for x in package['package_types'] if x is not None)

    if package.get('builds'):
        package['builds'] = ', '.join(str(x) for x in package['builds'] if x is not None)
    else:
        package['builds'] = ''

    fmt = fmt_access if access else fmt_no_access
    if revision:
        fmt = '%(revision)-6s | ' + fmt

    logger.info(fmt % package)
    if package.get('summary'):
        logger.info(' ' * 34 + '        : %s' % package.get('summary'))


def pprint_packages(packages, access=True, full_name=True, revisions=False):
    if packages:
        logger.info('Packages:')
    else:
        logger.info('No packages found')

    fmt = fmt_access if access else fmt_no_access
    if revisions:
        fmt = '%(revision)-6s | ' + fmt
    pprint_package_header(access, revisions=revisions)

    package_header = {
        'full_name': '-' * 25,
        'access': '-' * 12,
        'latest_version': '-' * 6,
        'conda_platforms': '-' * 15,
        'package_types': '-' * 15,
        'revision': '-' * 6,
        'builds': '-' * 10
    }

    logger.info(fmt % package_header)

    for package in sorted(packages, key=lambda pkg: pkg['full_name'] if full_name else pkg['name']):
        pprint_package(package, access, full_name, revision=revisions)


def pprint_user(user):
    user = user.copy()
    logger.info('Username: %s', user.pop('login'))
    logger.info('Member since: %s', parse_date(user.pop('created_at')).ctime())

    for key_value in user.items():
        logger.info('  +%s: %s' % key_value)


def pprint_collections(collections):
    if collections:
        logger.info('Collections:')
    for collection in collections:
        collection['permission'] = 'public' if collection['public'] else 'private'
        logger.info('   + %(name)25s: [%(permission)s] %(description)s' % collection)
