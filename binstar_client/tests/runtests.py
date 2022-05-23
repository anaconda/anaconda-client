'''
Created on Aug 5, 2013

@author: sean
'''
from __future__ import print_function
import unittest
from os.path import dirname,join
from argparse import ArgumentParser
from binstar_client.tests.runner import ColorTextTestRunner

def main():
    
    parser = ArgumentParser()
    parser.add_argument('--html', action='store_true')
    parser.add_argument('source_dir', nargs='?', default='')
    args = parser.parse_args()
    import binstar_client
    print(binstar_client)
    loader = unittest.loader.TestLoader()
    discover_dir = join(dirname(binstar_client.__path__[0]), args.source_dir)
    print('Discover %s' % discover_dir)
    tests = loader.discover(discover_dir)
    runner = ColorTextTestRunner(verbosity=2)
    result = runner.run(tests)
    runner.write_end(result)

    exit(0 if result.wasSuccessful() else -1)
    
    
if __name__ == '__main__':
    main()
