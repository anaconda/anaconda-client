# -*- coding: utf-8 -*-

"""Anaconda Client setup script."""

import os
import setuptools


root = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(root, 'requirements.txt'), 'rt', encoding='utf-8') as stream:
    install_requires = list(filter(bool, (
        requirement.split('#', 1)[0].strip() for requirement in stream
    )))

with open(os.path.join(root, 'requirements-extra.txt'), 'rt', encoding='utf-8') as stream:
    extras_require = list(filter(bool, (
        requirement.split('#', 1)[0].strip() for requirement in stream
    )))

# This is temporarily here so we don't pull in the incompatible dependency in CI
# and during local development as we move to 1.13.0. But to not change the behavior
# around the "full" extra at all. We will soon explicitly drop this dependency.
extras_require.append("anaconda-project>=0.9.1")

__about__ = {}
with open(os.path.join(root, 'binstar_client', '__about__.py'), 'rt', encoding='utf-8') as stream:
    exec(stream.read(), __about__)


setuptools.setup(
    name='anaconda-client',
    version=__about__['__version__'],
    description='Anaconda.org command line client library',
    license='BSD License',
    author='Sean Ross-Ross',
    author_email='srossross@gmail.com',
    url='https://github.com/Anaconda-Platform/anaconda-client',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
    ],

    python_requires = '>=3.8',
    install_requires=install_requires,
    extras_require={
        'full': extras_require,
    },
    packages=setuptools.find_packages(include=['binstar_client', 'binstar_client.*']),
    entry_points={
        'console_scripts': [
            'binstar = binstar_client.scripts.cli:main',
            'conda-server = binstar_client.scripts.cli:main',
        ],
        'anaconda_cli.subcommand': [
            'org = binstar_client.plugins:app',
        ]
    },
)
