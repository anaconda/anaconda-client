'''
Created on May 7, 2013

@author: sean
'''
from __future__ import print_function
from pprint import pprint

def package_list(lst, verbose=True):
    if verbose:
        pprint(lst)
    else:
        for pkg in lst:
            print('%-25s %s' % (pkg['full_name'], pkg['summary']))

def user_list(lst, verbose=True):
    if verbose:
        pprint(lst)
    else:
        for user in lst:
            print('%-25s %s' % (user['login'], user['name']))

