import os
from setuptools import setup, find_packages

base_dir = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(base_dir, 'requirements.txt')) as source:
    requirements = source.read().splitlines()

__about__ = {}
with open(os.path.join(base_dir, 'binstar_client', '__about__.py')) as source:
    exec(source.read(), __about__)

setup(
    name='anaconda-client',
    version=__about__['__version__'],
    author='Sean Ross-Ross',
    author_email='srossross@gmail.com',
    url='http://github.com/Anaconda-Platform/anaconda-client',
    description='Anaconda Cloud command line client library',
    packages=find_packages(),
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'anaconda = binstar_client.scripts.cli:main',
            'binstar = binstar_client.scripts.cli:main',
            'conda-server = binstar_client.scripts.cli:main'
        ]
    },
    license='BSD License',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
    ]
)
