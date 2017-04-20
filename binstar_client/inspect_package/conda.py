from __future__ import print_function

# Standard library imports
from os import path
from pprint import pprint
import json
import re
import sys
import tarfile
import tempfile

# Local imports
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
            depends.append({'name':name, 'specs': []})
        elif len(name_spec) == 2:
            name, spec = name_spec
            if spec.endswith('*'):  # Star does nothing in semver
                spec = spec[:-1]

            match = specs_re.match(spec)
            if match:
                op, spec = match.groups()
            else:
                op = '=='

            depends.append({'name':name, 'specs': [[op, spec]]})
        elif len(name_spec) == 3:
            name, spec, build_str = name_spec
            if spec.endswith('*'):  # Star does nothing in semver
                spec = spec[:-1]

            match = specs_re.match(spec)
            if match:
                op, spec = match.groups()
            else:
                op = '=='

            depends.append({'name':name, 'specs': [['==', '%s+%s' % (spec, build_str)]]})

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


def inspect_conda_package(filename, fileobj, *args, **kwargs):

    index, about, has_prefix = None, {}, False

    with tarfile.open(filename, fileobj=fileobj, mode="r|bz2") as tar:
        for info in tar:
            if info.name == 'info/index.json':
                index = tar.extractfile(info)
                index = json.loads(index.read().decode())
            elif info.name == 'info/recipe.json':
                # recipe.index is deprecated and only packages built with older
                # versions of conda-build contain that file.
                recipe = tar.extractfile(info)
                recipe = json.loads(recipe.read().decode())
                about = recipe.pop('about', {})
            elif info.name == 'info/about.json':
                # recipe.json is deprecated and only packages build with older
                # versions of conda-build contain that file.
                about = tar.extractfile(info)
                about = json.loads(about.read().decode())
            elif info.name == 'info/has_prefix':
                has_prefix = True
            if index is not None and about != {}:
                break
        else:
            if index is None:
                raise TypeError("info/index.json required in conda package")

    # Load icon defined in the index.json and file exists inside info folder
    fileobj.seek(0)
    icon_b64 = None
    icon_path = index.get('icon')
    if icon_path:
        tar = tarfile.open(filename, fileobj=fileobj, mode="r|bz2")
        for info in tar:
            if info.name == 'info/{0}'.format(icon_path):
                icon_data = tar.extractfile(info).read()
                f, temp_path = tempfile.mkstemp()
                with open(temp_path, 'wb') as f:
                    f.write(icon_data)
                icon_b64 = data_uri_from(temp_path)
                break

    subdir = get_subdir(index)

    machine = index['arch']
    operatingsystem = os_map.get(index['platform'], index['platform'])

    package_data = {
        'name': index.pop('name'),
        # TODO: this info should be removed and moved to release
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
        'basename': '%s/%s' % (subdir, path.basename(filename)),
        'attrs': {
            'operatingsystem': operatingsystem,
            'machine': machine,
            'target-triplet': '%s-any-%s' % (machine, operatingsystem),
            'has_prefix': has_prefix
        }
    }

    file_data['attrs'].update(index)
    conda_depends = index.get('depends', index.get('requires', []))
    file_data['dependencies'] = transform_conda_deps(conda_depends)

    return package_data, release_data, file_data


def main():
    filename = sys.argv[1]
    with open(filename) as fileobj:
        package_data, release_data, file_data = inspect_conda_package(filename, fileobj)
    pprint(package_data)
    print('--')
    pprint(release_data)
    print('--')
    pprint(file_data)

if __name__ == '__main__':
    main()
