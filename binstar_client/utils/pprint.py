'''
Created on Aug 8, 2013

@author: sean
'''
from __future__ import unicode_literals
from dateutil.parser import parse as parse_date
import logging
log = logging.getLogger('binstar.pprint')

def pprint_orgs(orgs):
    log.info('Organizations:')
    for org in orgs:
        log.info('   + %(login)25s' % org)

fmt_access = '     %(full_name)-25s | %(latest_version)8s | %(access)-12s | %(package_types)-15s | %(conda_platforms)-15s'
fmt_no_access = '     %(full_name)-25s | %(latest_version)8s | %(package_types)-15s | %(conda_platforms)-15s'

def pprint_package_header(access=True, revisions=False):
    package_header = {'full_name':'Name',
                      'access': 'Access', 'package_types':'Package Types',
                      'latest_version': 'Version', 'conda_platforms': 'Platforms',
                      'revision':'Rev'}
    fmt = fmt_access if access else fmt_no_access
    if revisions:
        fmt = '%(revision)-6s | ' + fmt

    log.info(fmt % package_header)

def pprint_package(package, access=True, full_name=True, revision=False):
    package = package.copy()

    if 'conda_platforms' in package:
        package['conda_platforms'] = ', '.join(package['conda_platforms'])
    if not full_name:
        package['full_name'] = package['name']
    package['access'] = 'published' if package.get('published') else 'public' if package['public'] else 'private'
    if package.get('package_types'):
        package['package_types'] = ', '.join(package['package_types'])
    fmt = fmt_access if access else fmt_no_access

    if revision:
        fmt = '%(revision)-6s | ' + fmt

    log.info(fmt % package)
    if package.get('summary'):
        log.info(' ' * 34 + '        : %s' % package.get('summary'))

def pprint_packages(packages, access=True, full_name=True, revisions=False):
    if packages:
        log.info('Packages:')
    else:
        log.info('No packages found')

    fmt = fmt_access if access else fmt_no_access
    if revisions:
        fmt = '%(revision)-6s | ' + fmt
    pprint_package_header(access, revisions=revisions)

    package_header = {'full_name':'-' * 25, 'access': '-' * 12,
                      'latest_version': '-' * 6, 'conda_platforms': '-' * 15,
                      'package_types':'-' * 15,
                      'revision': '-' * 6}

    log.info(fmt % package_header)

    key = lambda pkg: pkg['full_name'] if full_name else pkg['name']

    for package in sorted(packages, key=key):
        pprint_package(package, access, full_name, revision=revisions)

def pprint_user(user):
    user = user.copy()
    log.info('Username: %s', user.pop('login'))
    log.info('Member since: %s', parse_date(user.pop('created_at')).ctime())

    for key_value in user.items():
        log.info('  +%s: %s' % key_value)

def pprint_collections(collections):
    if collections:
        log.info('Collections:')
    for collection in collections:
        collection['permission'] = 'public' if collection['public'] else 'private'
        log.info('   + %(name)25s: [%(permission)s] %(description)s' % collection)

