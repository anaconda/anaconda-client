'''
Created on Aug 8, 2013

@author: sean
'''
from dateutil.parser import parse as parse_date
import logging
log = logging.getLogger('binstar.pprint')

def pprint_orgs(orgs):
    log.info('Organizations:')
    for org in orgs:
        log.info('   + %(login)25s' % org)

fmt_access = '     %(full_name)25s | %(access)-12s | %(package_types)-15s | %(summary)s'
fmt_no_access = '     %(full_name)25s | %(package_types)-15s | %(summary)s'

def pprint_package_header(access=True):
    package_header = {'full_name':'Name', 'access': 'Access', 'package_types':'Package Types', 'summary':'Summary'}
    fmt = fmt_access if access else fmt_no_access
    log.info(fmt % package_header)

def pprint_package(package, access=True, full_name=True):
    package = package.copy()
    if not full_name:
        package['full_name'] = package['name']
    package['access'] = 'published' if package.get('published') else 'public' if package['public'] else 'private'
    if package.get('package_types'):
        package['package_types'] = ', '.join(package['package_types'])
    fmt = fmt_access if access else fmt_no_access
    log.info(fmt % package)
        
def pprint_packages(packages, access=True, full_name=True):
    if packages:
        log.info('Packages:')
    else:
        log.info('No packages found')
    
    fmt = fmt_access if access else fmt_no_access
    pprint_package_header(access)
    
    package_header = {'full_name':'-' * 25, 'access': '-' * 12, 'package_types':'-' * 15, 'summary':'-' * 20}
    
    log.info(fmt % package_header)
    for package in packages:
        pprint_package(package, access, full_name)

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

