from unittest.mock import Mock
from repo_cli.utils import format

fixtures = [
        {'channel': 'ovasylenko',
        'download_count': 0,
        'family': 'conda',
        'file_count': 1,
        'metadata': {'build_number': 0,
                     'description': 'Sometimes you just want to send some '
                                    'data to untrusted environments. But '
                                    'how to do this safely? The trick '
                                    'involves signing. Given a key only '
                                    'you know, you can cryptographically '
                                    'sign your data and hand it over to\n'
                                    'someone else. When you get the data '
                                    'back you can easily ensure that '
                                    'nobody\n'
                                    'tampered with it.\n',
                     'dev_url': 'https://github.com/pallets/itsdangerous',
                     'doc_url': 'https://pythonhosted.org/itsdangerous/',
                     'home': 'https://pythonhosted.org/itsdangerous/',
                     'install_cmd': 'conda install -c ovasylenko '
                                    'itsdangerous',
                     'license': 'BSD',
                     'name': 'itsdangerous',
                     'subdirs': ['noarch'],
                     'summary': 'Various helpers to pass trusted data to '
                                'untrusted environments',
                     'version': '0.24'},
        'name': 'itsdangerous',
        'subchannel': None,
        'updated_at': '2019-11-21T13:23:41.899000+00:00'},
       {'channel': 'srakitin',
        'download_count': 0,
        'family': 'conda',
        'file_count': 1,
        'metadata': {'build_number': 0,
                     'description': 'Sometimes you just want to send some '
                                    'data to untrusted environments. But '
                                    'how to do this safely? The trick '
                                    'involves signing. Given a key only '
                                    'you know, you can cryptographically '
                                    'sign your data and hand it over to\n'
                                    'someone else. When you get the data '
                                    'back you can easily ensure that '
                                    'nobody\n'
                                    'tampered with it.\n',
                     'dev_url': 'https://github.com/pallets/itsdangerous',
                     'doc_url': 'https://pythonhosted.org/itsdangerous/',
                     'home': 'https://pythonhosted.org/itsdangerous/',
                     'install_cmd': 'conda install -c srakitin '
                                    'itsdangerous',
                     'license': 'BSD',
                     'name': 'itsdangerous',
                     'subdirs': ['noarch'],
                     'summary': 'Various helpers to pass trusted data to '
                                'untrusted environments',
                     'version': '0.24'},
        'name': 'itsdangerous',
        'subchannel': None,
        'updated_at': '2019-11-21T19:14:22.043000+00:00'},
       {'channel': 'anaconda-main',
        'download_count': 0,
        'family': 'conda',
        'file_count': 40,
        'metadata': {'build_number': 0,
                     'install_cmd': 'conda install -c anaconda-main '
                                    'itsdangerous',
                     'license': 'BSD 3-Clause',
                     'license_family': 'BSD',
                     'name': 'itsdangerous',
                     'subdirs': ['linux-64', 'osx-64', 'noarch', 'win-64'],
                     'version': '1.1.0'},
        'name': 'itsdangerous',
        'subchannel': None,
        'updated_at': '2019-11-21T21:29:54.547000+00:00'},
       {'channel': 'fpliger',
        'download_count': 0,
        'family': 'conda',
        'file_count': 1,
        'metadata': {'build_number': 0,
                     'description': 'Sometimes you just want to send some '
                                    'data to untrusted environments. But '
                                    'how to do this safely? The trick '
                                    'involves signing. Given a key only '
                                    'you know, you can cryptographically '
                                    'sign your data and hand it over to\n'
                                    'someone else. When you get the data '
                                    'back you can easily ensure that '
                                    'nobody\n'
                                    'tampered with it.\n',
                     'dev_url': 'https://github.com/pallets/itsdangerous',
                     'doc_url': 'https://pythonhosted.org/itsdangerous/',
                     'home': 'https://pythonhosted.org/itsdangerous/',
                     'install_cmd': 'conda install -c fpliger itsdangerous',
                     'license': 'BSD',
                     'name': 'itsdangerous',
                     'subdirs': ['noarch'],
                     'summary': 'Various helpers to pass trusted data to '
                                'untrusted environments',
                     'version': '0.24'},
        'name': 'itsdangerous',
        'subchannel': None,
        'updated_at': '2019-11-22T02:04:28.578000+00:00'},
       {'channel': 'fpliger',
        'download_count': 0,
        'family': 'conda',
        'file_count': 1,
        'metadata': {'build_number': 0,
                     'description': 'Sometimes you just want to send some '
                                    'data to untrusted environments. But '
                                    'how to do this safely? The trick '
                                    'involves signing. Given a key only '
                                    'you know, you can cryptographically '
                                    'sign your data and hand it over to\n'
                                    'someone else. When you get the data '
                                    'back you can easily ensure that '
                                    'nobody\n'
                                    'tampered with it.\n',
                     'dev_url': 'https://github.com/pallets/itsdangerous',
                     'doc_url': 'https://pythonhosted.org/itsdangerous/',
                     'home': 'https://pythonhosted.org/itsdangerous/',
                     'install_cmd': 'conda install -c fpliger/bubu '
                                    'itsdangerous',
                     'license': 'BSD',
                     'name': 'itsdangerous',
                     'subdirs': ['noarch'],
                     'summary': 'Various helpers to pass trusted data to '
                                'untrusted environments',
                     'version': '0.24'},
        'name': 'itsdangerous',
        'subchannel': 'bubu',
        'updated_at': '2019-11-22T02:04:28.488000+00:00'},
       {'channel': 'tleffert',
        'download_count': 0,
        'family': 'conda',
        'file_count': 6,
        'metadata': {'build_number': 1,
                     'dev_url': 'https://github.com/pallets/itsdangerous',
                     'doc_url': 'http://pythonhosted.org/itsdangerous',
                     'home': 'https://github.com/pallets/itsdangerous',
                     'install_cmd': 'conda install -c tleffert '
                                    'itsdangerous',
                     'license': 'BSD 3-Clause',
                     'license_family': 'BSD',
                     'name': 'itsdangerous',
                     'subdirs': ['linux-64'],
                     'summary': 'Various helpers to pass trusted data to '
                                'untrusted environments.',
                     'version': '0.24'},
        'name': 'itsdangerous',
        'subchannel': None,
        'updated_at': '2019-11-21T12:54:14.862000+00:00'}]

def test_packages_format():
    expected = [
        '\n     6 packages found:\n',
        '     Channel         | Name            |  Version | Family       | Build      | License         | Platforms      ',
        '     --------------- | --------------- |   ------ | ------------ | ---------- | --------------- | ---------------',
        '     ovasylenko      | itsdangerous    |     0.24 | conda        | 0          | BSD             | noarch         ',
        '     srakitin        | itsdangerous    |     0.24 | conda        | 0          | BSD             | noarch         ',
        '     anaconda-main   | itsdangerous    |    1.1.0 | conda        | 0          | BSD 3-Clause    | linux-64, osx-64, noarch, win-64',
        '     fpliger         | itsdangerous    |     0.24 | conda        | 0          | BSD             | noarch         ',
        '     fpliger/bubu    | itsdangerous    |     0.24 | conda        | 0          | BSD             | noarch         ',
        '     tleffert        | itsdangerous    |     0.24 | conda        | 1          | BSD 3-Clause    | linux-64       ',
        ''
    ]
    logger = Mock()
    format.format_packages(fixtures, logger)
    for line in expected:
        logger.info.assert_any_call(line)