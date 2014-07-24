'''
@author: sean
'''

from setuptools import setup, find_packages

setup(
    name='test_package34',
    version="0.3.1",
    author='Sean Ross-Ross',
    author_email='srossross@gmail.com',
    url='http://github.com/binstar/binstar_pypi',
    packages=find_packages(),
    description='Python Distribution Utilities',
    long_description='longer description of the package',
    install_requires=['requests>=2.0,<=3.0',
                      'pyyaml',
                      'python-dateutil',
                      'pytz'],

)


