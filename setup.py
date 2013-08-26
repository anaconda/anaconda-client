'''
@author: sean
'''

from setuptools import setup, find_packages

setup(
    name='binstar',
    version="0.3.0",
    author='Sean Ross-Ross',
    author_email='srossross@gmail.com',
    url='http://github.com/Binstar/binstar_client',
    packages=find_packages(),
    install_requires=['keyring', 
                      'requests>=1.0',
                      'pyyaml',
                      'python-dateutil'],
    entry_points={
          'console_scripts': [
              'binstar = binstar_client.scripts.cli:main',
              ]
                 },

)
