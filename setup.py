'''
@author: sean
'''

from setuptools import setup, find_packages

import binstar_client
setup(
    name='binstar',
    version=binstar_client.__version__,
    author='Sean Ross-Ross',
    author_email='srossross@gmail.com',
    url='http://github.com/Binstar/binstar_client',
    packages=find_packages(),
    install_requires=['keyring',
                      'requests>=2.0',
                      'pyyaml',
                      'python-dateutil'],
    entry_points={
          'console_scripts': [
              'binstar = binstar_client.scripts.cli:main',
              ]
                 },

)
