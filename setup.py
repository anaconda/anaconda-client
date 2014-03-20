'''
@author: sean
'''

from setuptools import setup, find_packages

ctx = {}
exec(open('binstar_client/_version.py').read(), ctx)
version = ctx.get('__version__', 'dev')

setup(
    name='binstar',
    version=version,
    author='Sean Ross-Ross',
    author_email='srossross@gmail.com',
    url='http://github.com/Binstar/binstar_client',
    packages=find_packages(),
    install_requires=['requests>=2.0',
                      'pyyaml',
                      'python-dateutil',
                      'pytz'],
    entry_points={
          'console_scripts': [
              'binstar = binstar_client.scripts.cli:main',
              'binstar-build = binstar_client.scripts.build:main',
              ]
                 },

)
