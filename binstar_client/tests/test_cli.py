'''
Created on Feb 18, 2014

@author: sean
'''
import unittest
import mock

class Test(unittest.TestCase):
    
#     @mock.patch('requests.get')
    def test_foo(self):
        from subprocess import check_call
        
        import shutil, shlex
        print shlex.split('binstar -t 123 whoami')
        print check_call('binstar -t 123 whoami', shell=True)
        
