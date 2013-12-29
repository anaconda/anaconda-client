'''
@author: sean
'''

from setuptools import setup, find_packages

try:
    from distutils.command.build_py import build_py_2to3 as build_py
except ImportError:
    from distutils.command.build_py import build_py

setup(
    name='binstar',
    version="0.3.0",
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
    
    cmdclass={'build_py': build_py},
)
