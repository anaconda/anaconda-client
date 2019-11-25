from __future__ import unicode_literals
from dateutil.parser import parse as parse_date
import logging

INITIAL_SPACE = '     '
fmt_package_headers = INITIAL_SPACE + '%(channel_path)-15s | %(name)-15s | %(version)8s | %(family)-12s ' \
                                       '| %(build_number)-10s | %(license)-15s | %(subdirs)-15s'

class PackagesFormatter:
    def __init__(self, log):
        self.log = log

    def format_package_header(self):
        package_header = {
            'channel_path': 'Channel',
            'name': 'Name',
            'family': 'Family',
            'version': 'Version',
            'subdirs': 'Platforms',
            'license': 'License',
            'build_number': 'Build'
        }
        self.log.info(fmt_package_headers % package_header)

    def format_package(self, package):
        package = package.copy()
        package.update(package['metadata'])

        if package['subchannel']:
            package['channel_path'] = '%s/%s' % (package['channel'], package['subchannel'])
        else:
            package['channel_path']= package['channel']

        package['full_name'] = '%s::%s' % (package['channel_path'], package['name'])
        package['subdirs'] = ', '.join(str(x) for x in package['subdirs'] if x is not None)

        self.log.info(fmt_package_headers % package)\

    def format(self, packages):
        if packages:
            self.log.info('\n%s%i packages found:\n' % (INITIAL_SPACE, len(packages)))
        else:
            self.log.info('No packages found')

        self.format_package_header()

        package_header = {
            'channel_path': '-' * 15,
            'name': '-' * 15,
            'family': '-' * 12,
            'version': '-' * 6,
            'subdirs': '-' * 15,
            'license': '-' * 15,
            'build_number': '-' * 10
        }


        self.log.info(fmt_package_headers % package_header)

        for package in packages:
            self.format_package(package)
        self.log.info('')

def format_packages(packages, logger):
    formatter = PackagesFormatter(logger)
    formatter.format(packages)
    return formatter

