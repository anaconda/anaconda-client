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
        
def pprint_packages(packages):
    if packages:
        log.info('Packages:')
    for package in packages:
        if package.get('published'):
            package['permission'] = '[published]'
        else:
            package['permission'] = '[public]' if package['public'] else '[private]'
            
        log.info('   + %(name)20s: %(permission)-12s | %(summary)s' % package)

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

