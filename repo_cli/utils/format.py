from __future__ import unicode_literals
from dateutil.parser import parse as parse_date

INITIAL_SPACE = '     '
fmt_package_headers = INITIAL_SPACE + '%(channel_path)-15s | %(name)-15s | %(version)8s | %(family)-12s ' \
                                       '| %(build_number)-10s | %(license)-15s | %(subdirs)-15s'
fmt_channel_headers = INITIAL_SPACE + '%(channel_path)-15s | %(privacy)-10s | %(owners)15s | %(artifact_count)-12s ' \
                                       '| %(download_count)-11s | %(subchannel_count)-14s |  %(mirror_count)-9s | %(description)-30s'
fmt_mirror_header_spacer = {
        'id': '-' * 36,
        'name': '-' * 15,
        'type': '-' * 8,
        'mode': '-' * 10,
        'state': '-' * 10,
        'source_root': '-' * 50,
        'last_run_at': '-' * 30,
        'updated_at': '-' * 30
    }
fmt_mirror_headers = INITIAL_SPACE + '%(id)-36s | %(name)-15s | %(type)8s | %(mode)-10s ' \
                                       '| %(state)-10s | %(source_root)-50s |  %(last_run_at)-30s | %(updated_at)-30s'
class PackagesFormatter:
    def __init__(self, log):
        self.log = log

    @staticmethod
    def format_package_header():
        package_header = {
            'channel_path': 'Channel',
            'name': 'Name',
            'family': 'Family',
            'version': 'Version',
            'subdirs': 'Platforms',
            'license': 'License',
            'build_number': 'Build'
        }
        return fmt_package_headers % package_header

    def log_format_package_header(self):
        self.log.info(self.format_package_header())

    @staticmethod
    def format_package(package):
        package = package.copy()
        package.update(package['metadata'])

        if package['subchannel']:
            package['channel_path'] = '%s/%s' % (package['channel'], package['subchannel'])
        else:
            package['channel_path']= package['channel']

        package['full_name'] = '%s::%s' % (package['channel_path'], package['name'])
        package['subdirs'] = ', '.join(str(x) for x in package['subdirs'] if x is not None)
        return fmt_package_headers % package

    def log_format_package(self, package):
        self.log.info(self.format_package(package))

    @staticmethod
    def format_channel_header():
        package_header = {
            'channel_path': 'Channel',
            'privacy': 'Privacy',
            'owners': 'Owners',
            'artifact_count': '# Artifacts',
            'download_count': '# Downloads',
            'subchannel_count': '# Subchannels',
            'mirror_count': '# Mirrors',
            'description': 'Description'
        }
        return fmt_channel_headers % package_header

    def log_format_channel_header(self):
        self.log.info(self.format_channel_header())

    @staticmethod
    def format_channel(channel):
        channel = channel.copy()

        if channel['parent']:
            channel['channel_path'] = '%s/%s' % (channel['parent'], channel['name'])
        else:
            channel['channel_path']= channel['name']

        channel['owners'] = ', '.join(str(x) for x in channel['owners'] if x is not None)
        return fmt_channel_headers % channel

    def log_format_channel(self, channel):
        self.log.info(self.format_channel(channel))

    def format(self, packages, metadata):
        self.log_format_package_header()

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
            self.log_format_package(package)

        if packages:
            end_set = len(packages) + metadata['offset']
            self.log.info('\n%s%i packages found.' % (INITIAL_SPACE, metadata['total_count']))
            self.log.info('%sVisualizing %i-%i interval.' % (INITIAL_SPACE, len(packages), end_set))
        else:
            self.log.info('No packages found')

        self.log.info('')


class MirrorFormatter:
    keymap = {'created_at': 'created at', 'updated_at': 'Updated at', 'last_run_at': 'Last run at'}
    @staticmethod
    def format_detail(mirror):
        mirror = {key.replace('mirror_', ''): val for key, val in mirror.items()}
        keymap = {'created_at': 'created at', 'updated_at': 'Updated at', 'last_run_at': 'Last run at'}
        mirror_ = dict(mirror)
        resp = [INITIAL_SPACE + "Mirror Details:", INITIAL_SPACE + "---------------"]

        fields = ['id', 'name', 'type', 'mode', 'state', 'source_root', 'last_run_at', 'updated_at', 'created',
                  'cron', 'proxy', 'filters']
        for key in fields:
            label = keymap.get(key, key.replace('_', ' ')).capitalize()
            value = mirror_.get(key, '')
            resp.append("%s%s: %s" % (INITIAL_SPACE, label, value))

        return '\n'.join(resp)

    @classmethod
    def format_list_headers(cls):
        mirror_headers = {k: k.capitalize() for k in fmt_mirror_header_spacer}
        mirror_headers.update(cls.keymap)
        return fmt_mirror_headers % mirror_headers

    @staticmethod
    def format_list_item(mirror):
        mirror = {key.replace('mirror_', ''): val for key, val in mirror.items()}
        return fmt_mirror_headers % mirror

    @staticmethod
    def format_list(mirrors):
        lines = []
        lines.append(MirrorFormatter.format_list_headers())
        lines.append(fmt_mirror_headers % fmt_mirror_header_spacer)

        for mirror in mirrors:
            lines.append(MirrorFormatter.format_list_item(mirror))

        return '\n'.join(lines)


class CVEFormatter:
    fmt_header_spacer = {
        'cve': '-' * 12,
        'score': '-' * 6,
        'score_type': '-' * 6,
        'description': '-' * 100,
        # 'mode': '-' * 10,
        # 'state': '-' * 10,
        # 'source_root': '-' * 50,
        # 'last_run_at': '-' * 30,
        # 'updated_at': '-' * 30
    }
    fmt_headers = INITIAL_SPACE + '%(cve)-12s | %(score)6s | %(score_type)6s | %(description)-50s'

    keymap = {'date_added': 'Published', 'updated_at': 'Updated at', 'last_run_at': 'Last run at'}

    fields = ['cve', 'score', 'score_type', 'description','cvssv2accesscomplexity',
              'cvssv2accessvector', 'cvssv2authentication', 'cvssv2availabilityimpact',
              'cvssv2confidentialityimpact', 'cvssv2integrityimpact', 'cvssv2score', 'cvssv2severity',
              'cvssv3attackvector', 'cvssv3availabilityimpact', 'cvssv3basescore', 'cvssv3baseseverity',
              'cvssv3confidentialityimpact', 'cvssv3integrityimpact', 'cvssv3privilegesrequired',
              'cvssv3scope', 'cvssv3userinteraction', 'date_added',
              'packages']

    @classmethod
    def format_detail(cls, item):
        item_ = cls.normalize_item(item)
        resp = [INITIAL_SPACE + "CVE Details:", INITIAL_SPACE + "---------------"]

        fields = ['cve', 'score', 'description']
        for key in cls.fields:
            label = cls.keymap.get(key, key).capitalize()
            value = item_.get(key, '')
            resp.append("%s%s: %s" % (INITIAL_SPACE, label, value))

        return '\n'.join(resp)

    @classmethod
    def format_list_headers(cls):
        cve_headers = {k: k.capitalize() for k in cls.fmt_header_spacer}
        cve_headers.update(cls.keymap)
        return cls.fmt_headers % cve_headers

    @classmethod
    def format_list_item(cls, item):
        item_ = cls.normalize_item(item)
        return cls.fmt_headers % item_

    @staticmethod
    def normalize_item(item):
        item_ = {key: val for key, val in item.items()}
        score = item_.get('cvssv3basescore')
        if score:
            item_['score'] = score
            item_['score_type'] = 'CVSS3'
        else:
            item_['score'] = item_.get('cvssv2score')
            item_['score_type'] = 'CVSS2'

        def fmt_package(pack):
            try:
                if not 'subdir' in pack:
                    pack['subdir'] = ''
                return '{subdir}/{name}-{version} (sha258: {sha256})'.format(**pack)
            except TypeError:
                return pack

        packages = [fmt_package(pack) for pack in item_.get('packages', [])]
        item_['packages'] = ', '.join(packages)
        return item_


    @classmethod
    def format_list(cls, items):
        lines = []
        lines.append(cls.format_list_headers())
        lines.append(cls.fmt_headers % cls.fmt_header_spacer)

        for item in items:
            lines.append(cls.format_list_item(item))

        return '\n'.join(lines)

def format_packages(packages, meta, logger):
    formatter = PackagesFormatter(logger)
    formatter.format(packages, meta)
    return formatter

