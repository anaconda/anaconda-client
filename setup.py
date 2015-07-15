'''
'''

from setuptools import setup, find_packages
import versioneer

print versioneer.get_version()

setup(
    name='conda-server',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    author='Sean Ross-Ross',
    author_email='srossross@gmail.com',
    url='http://github.com/Binstar/conda-server',
    description='Binstar command line client library',
    packages=find_packages(),
    install_requires=['clyent',
                      'requests>=2.0',
                      'pillow',
                      'pyyaml',
                      'python-dateutil',
                      'pytz'],
    entry_points={
          'console_scripts': [
              'binstar = binstar_client.scripts.cli:main',
              'conda-server = binstar_client.scripts.cli:main',
              ]
                 },

)
