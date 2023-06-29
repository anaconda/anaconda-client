# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring

from __future__ import print_function

import os.path
import json
import re
import sys
import tempfile
from pprint import pprint
from shutil import rmtree
from conda_package_handling.api import extract

from ..utils.notebook.data_uri import data_uri_from


os_map = {'osx': 'darwin', 'win': 'win32'}
specs_re = re.compile('^([=><]+)(.*)$')


def transform_conda_deps(deps):
    """
    Format dependencies into a common binstar format
    """
    depends = []
    for dep in deps:
        dep = dep.strip()
        name_spec = dep.split(' ', 1)
        if len(name_spec) == 1:
            name, = name_spec
            depends.append({'name': name, 'specs': []})
        elif len(name_spec) == 2:
            name, spec = name_spec
            if spec.endswith('*'):  # Star does nothing in semver
                spec = spec[:-1]

            match = specs_re.match(spec)
            if match:
                operator, spec = match.groups()
            else:
                operator = '=='

            depends.append({'name': name, 'specs': [[operator, spec]]})
        elif len(name_spec) == 3:
            name, spec, build_str = name_spec
            if spec.endswith('*'):  # Star does nothing in semver
                spec = spec[:-1]

            match = specs_re.match(spec)
            if match:
                operator, spec = match.groups()
            else:
                operator = '=='

            depends.append({'name': name, 'specs': [['==', '%s+%s' % (spec, build_str)]]})

    return {'depends': depends}


def get_subdir(index):
    """
    Return the sub-directory given the index dictionary.  The return
    value is obtained in the following order:

    1. when the 'subdir' key exists, it's value is returned
    2. if the 'arch' is None, or does not exist, 'noarch' is returned
    3. otherwise, the return value is constructed from the 'platform' key
       and the 'arch' key (where 'x86' is replaced by '32',
       and 'x86_64' by '64')
    """
    try:
        return index['subdir']
    except KeyError:
        arch = index.get('arch')
        if arch is None:
            return 'noarch'
        intel_map = {'x86': '32', 'x86_64': '64'}
        return '%s-%s' % (index.get('platform'), intel_map.get(arch, arch))


def inspect_conda_info_dir(info_path, basename):  # pylint: disable=too-many-locals
    def _load(filename, default=None):
        file_path = os.path.join(info_path, filename)
        if os.path.exists(file_path):
            with open(file_path, encoding='utf-8') as file:
                return json.load(file)
        return default

    index = _load('index.json', None)
    if index is None:
        raise TypeError('info/index.json required in conda package')

    recipe = _load('recipe.json')
    about = recipe.get('about', {}) if recipe else _load('about.json', {})
    has_prefix = os.path.exists(os.path.join(info_path, 'has_prefix'))

    # Load icon defined in the index.json and file exists inside info folder
    icon_b64 = index.get('icon', None)
    icon_path = os.path.join(info_path, icon_b64) if icon_b64 else None
    if icon_path and os.path.exists(icon_path):
        icon_b64 = data_uri_from(icon_path)

    subdir = get_subdir(index)
    machine = index['arch']
    operatingsystem = os_map.get(index['platform'], index['platform'])

    package_data = {
        'name': index.pop('name'),
        # NOTE: this info should be removed and moved to release
        'summary': about.get('summary', ''),
        'description': about.get('description', ''),
        'license': about.get('license'),
        'license_url': about.get('license_url'),
        'license_family': about.get('license_family'),
        'dev_url': about.get('dev_url'),
        'doc_url': about.get('doc_url'),
        'home': about.get('home'),
        'source_git_url': about.get('source_git_url'),
    }
    release_data = {
        'version': index.pop('version'),
        'home_page': about.get('home'),
        'description': about.get('description', ''),
        'summary': about.get('summary', ''),
        'dev_url': about.get('dev_url'),
        'doc_url': about.get('doc_url'),
        'home': about.get('home'),
        'source_git_url': about.get('source_git_url'),
        'source_git_tag': about.get('source_git_tag'),
        'icon': icon_b64,
        'license': about.get('license'),
        'license_url': about.get('license_url'),
        'license_family': about.get('license_family'),
    }
    file_data = {
        'basename': '%s/%s' % (subdir, basename),
        'attrs': {
            'operatingsystem': operatingsystem,
            'machine': machine,
            'target-triplet': '%s-any-%s' % (machine, operatingsystem),
            'has_prefix': has_prefix,
            'subdir': subdir,
        }
    }

    file_data['attrs'].update(index)
    conda_depends = index.get('depends', index.get('requires', []))
    file_data['dependencies'] = transform_conda_deps(conda_depends)

    return package_data, release_data, file_data


def inspect_conda_package(filename, *args, **kwargs):  # pylint: disable=unused-argument
    tmpdir = tempfile.mkdtemp()
    extract(filename, tmpdir, components='info')

    info_dir = os.path.join(tmpdir, 'info')
    package_data, release_data, file_data = inspect_conda_info_dir(info_dir, os.path.basename(filename))

    rmtree(tmpdir)

    return package_data, release_data, file_data


def main():
    filename = sys.argv[1]
    with open(filename) as fileobj:  # pylint: disable=unspecified-encoding
        package_data, release_data, file_data = inspect_conda_package(filename, fileobj)
    pprint(package_data)
    print('--')
    pprint(release_data)
    print('--')
    pprint(file_data)


if __name__ == '__main__':
    main()
