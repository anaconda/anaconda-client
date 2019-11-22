from __future__ import unicode_literals
from dateutil.parser import parse as parse_date
import logging


fmt_access = '     %(full_name)-25s | %(latest_version)8s | %(access)-12s | %(package_types)-15s | %(conda_platforms)-15s | %(builds)-10s'
fmt_no_access = '     %(full_name)-25s | %(latest_version)8s | %(package_types)-15s | %(conda_platforms)-15s | %(builds)-10s'




def pprint_package_header(logger, access=True, revisions=False):
    package_header = {
        'full_name': 'Name',
        'access': 'Access',
        'package_types': 'Package Types',
        'latest_version': 'Version',
        'conda_platforms': 'Platforms',
        'revision': 'Rev',
        'builds': 'Builds',
    }

    fmt = fmt_access if access else fmt_no_access
    if revisions:
        fmt = '%(revision)-6s | ' + fmt

    logger.info(fmt % package_header)


def format_packages(logger, packages, access=True, full_name=True, revisions=False):
    if packages:
        logger.info('Packages:')
    else:
        logger.info('No packages found')

    fmt = fmt_access if access else fmt_no_access
    if revisions:
        fmt = '%(revision)-6s | ' + fmt
    pprint_package_header(access, revisions=revisions)

    package_header = {
        'full_name': '-' * 25,
        'access': '-' * 12,
        'latest_version': '-' * 6,
        'conda_platforms': '-' * 15,
        'package_types': '-' * 15,
        'revision': '-' * 6,
        'builds': '-' * 10
    }

    logger.info(fmt % package_header)

    for package in sorted(packages, key=lambda pkg: pkg['full_name'] if full_name else pkg['name']):
        pprint_package(package, access, full_name, revision=revisions)
