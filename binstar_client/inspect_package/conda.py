from __future__ import print_function

import json
from os import path
from pprint import pprint
import sys
import tarfile
import re


arch_map = {('osx', 'x86_64'):'osx-64',
            ('osx', 'x86'):'osx-32',
            ('win', 'x86'):'win-32',
            ('win', 'x86_64'):'win-64',
            ('linux', 'x86'):'linux-32',
            ('linux', 'x86_64'):'linux-64',
            (None, None): 'any-any',
           }

os_map = {'osx':'darwin', 'win':'win32'}

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



def inspect_conda_package(filename, fileobj):

    tar = tarfile.open(filename, fileobj=fileobj)
    index = tar.extractfile('info/index.json')
    index = json.loads(index.read().decode())

    try:
        recipe = tar.extractfile('info/recipe.json')
        recipe = json.loads(recipe.read().decode())
    except KeyError:
        recipe = {}

    about = recipe.pop('about', {})

    subdir = index.get('subdir',
                       arch_map[(index['platform'], index['arch'])])
    machine = index['arch']
    operatingsystem = os_map.get(index['platform'], index['platform'])

    package_data = {
                    'name': index.pop('name'),
                    'summary': about.get('summary', ''),
                    'license': about.get('license'),
                    }
    release_data = {
                    'version': index.pop('version'),
                    'home_page': about.get('home'),
                    'description': '',
                    }
    file_data = {
                'basename': '%s/%s' % (subdir, path.basename(filename)),
                'attrs':{
                        'operatingsystem': operatingsystem,
                        'machine': machine,
                        'target-triplet': '%s-any-%s' % (machine, operatingsystem)
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
