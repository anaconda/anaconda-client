'''
'''

from setuptools import setup, find_packages

ctx = {}
try:
    with open('binstar_client/_version.py') as fd:
        exec(open('binstar_client/_version.py').read(), ctx)
    version = ctx.get('__version__', 'dev')
except IOError:
    version = 'dev'

setup(
    name='binstar',
    version=version,
    author='Sean Ross-Ross',
    author_email='srossross@gmail.com',
    url='http://github.com/Binstar/binstar_client',
    description='Binstar command line client library',
    packages=find_packages(),
    install_requires=['clyent',
                      'requests>=2.0',
                      'pyyaml',
                      'python-dateutil',
                      'pytz'],
    entry_points={
          'console_scripts': [
              'binstar = binstar_client.scripts.cli:main',
              ]
                 },

)
