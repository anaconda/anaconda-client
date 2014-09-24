from __future__ import print_function

from email.parser import Parser
import json
from os import path
from os.path import basename
from pprint import pprint
import sys
import tarfile
import zipfile

from binstar_client import errors
from binstar_client.inspect_package.uitls import extract_first, pop_key
import pkg_resources


def parse_requirement(line, deps, extras, extra):
    req = pkg_resources.Requirement.parse(line)
    if extra:
        extras[extra][req.key] = req.specs
    else:
        deps[req.key] = req.specs

def parse_requires_txt(requires_txt):
    deps = {}
    error = False
    extras = {}
    extra = None

    for line in requires_txt.split('\n'):
        line = line.strip()
        if line.startswith('[') and line.endswith(']'):
            extra = line[1:-1]
            if extra == 'all':
                extra = None
            else:
                extras.setdefault(extra, {})

            # Dont parse this requirement
            continue
        try:
            parse_requirement(line, deps, extras, extra)
        except ValueError:
            error = True

    return {'has_dep_errors': error, 'depends': deps, 'extras':extras,
            'depends_index': list(deps.keys()),
            'optional_depends_index': [d for extra in extras.values() for d in extra.keys()]
            }

def format_requires_metadata(run_requires):
    deps = {}
    extras = {}
    environments = {}
    for run_require in run_requires:
        extra = run_require.get('extra')
        env = run_require.get('environment')
        requires = run_require['requires']

        if env:
            obj = environments.setdefault(env, {})
        elif extra is None or extra == 'all':
            obj = deps
        else:
            obj = extras.setdefault(extra, {})

        for req in requires:
            req = req.strip()
            req_spec = req.split(' ', 1)
            if len(req_spec) == 1:
                obj[req] = []
            else:
                req, spec = req_spec
                spec = spec.strip()
                if spec[0] == '(': spec = spec[1:]
                if spec[-1] == ')': spec = spec[:-1]

                req = pkg_resources.Requirement.parse('%s %s' % (req, spec))
                obj[req.key] = req.specs

    optional = []
    optional += [d for extra in extras.values() for d in extra.keys()]
    optional += [d for extra in environments.values() for d in extra.keys()]

    attrs = {'has_dep_errors': False, 'depends': deps, 'extra_depends':extras,
             'environment_depends': environments,
            'depends_index': list(deps.keys()),
            'optional_depends_index': optional,
             }

    return attrs

def format_wheel_json_metadata(data, filename, zipfile):
    package_data = {'name': pop_key(data, 'name'),
                    'summary': pop_key(data, 'summary', None),
                    'license': pop_key(data, 'license', None),
                    }
    description_doc = pop_key(data.get('document_names') or {}, 'description', None)

    if description_doc:
        description = extract_first(zipfile, '*.dist-info/%s' % description_doc)
    else:
        description = None

    release_data = {
                    'version': pop_key(data, 'version'),
                    'description': description,
                    'home_page': pop_key(data.get('project_urls', {}), 'Home', None)
                    }

    data.update({
                 'packagetype': 'bdist_wheel',
                 'python_version':'source',
                 })

    file_data = {
                 'basename': path.basename(filename),
                 'attrs': data,
                 'dependencies':format_requires_metadata(data.get('run_requires', {})),
                 }

    return package_data, release_data, file_data


def inspect_pypi_package_whl(filename, fileobj):
    tf = zipfile.ZipFile(fileobj)

    data = extract_first(tf, '*.dist-info/metadata.json')
    if data is None:
        data = extract_first(tf, '*.dist-info/pydist.json')

    if data:
        package_data, release_data, file_data = format_wheel_json_metadata(json.loads(data), filename, tf)
    else:
        package_data, release_data, file_data = {}, {}, {}

    file_components = filename[:-4].split('-')
    if len(file_components) == 5:
        _, _, python_version, abi, platform = file_components
        build_no = 0
    elif len(file_components) == 6:
        _, _, build_no, python_version, abi, platform = file_components
    else:
        raise TypeError("Bad wheel package name")
    if platform == 'any': platform = None
    if abi == 'none': abi = None

    file_data['attrs'].update(build_no=build_no, python_version=python_version, abi=abi,
                              packagetype='bdist_wheel')
    file_data.update(platform=platform)
    return package_data, release_data, file_data


def inspect_pypi_package_sdist(filename, fileobj):

    tf = tarfile.open(filename, fileobj=fileobj)

    data = extract_first(tf, '*.egg-info/PKG-INFO')

    distrubite = False
    if data is None:
        data = extract_first(tf, '*/PKG-INFO')
        distrubite = True
        if data is None:
            raise errors.BinstarError("Could not find *.egg-info/PKG-INFO file in pypi sdist")

    attrs = dict(Parser().parsestr(data).items())
    package_data = {'name': pop_key(attrs, 'Name'),
                    'summary': pop_key(attrs, 'Summary', None),
                    'license': pop_key(attrs, 'License', None),
                    }
    release_data = {
                    'version': pop_key(attrs, 'Version'),
                    'description': pop_key(attrs, 'Description', None),
                    'home_page': pop_key(attrs, 'Home-page', None)

                    }
    file_data = {
                 'basename': basename(filename),
                 'attrs': attrs,
                 }


    if distrubite:  # Distrubite does not create dep files
        file_data.update(dependencies={'has_dep_errors': True})
    requires_txt = extract_first(tf, '*.egg-info/requires.txt')
    if requires_txt:
        file_data.update(dependencies=parse_requires_txt(requires_txt))

    attrs.update({
                 'packagetype': 'sdist',
                 'python_version':'source',
                 })



    return package_data, release_data, file_data


def inspect_pypi_package_egg(filename, fileobj):
    tf = zipfile.ZipFile(fileobj)

    data = extract_first(tf, 'EGG-INFO/PKG-INFO')
    if data is None:
        raise errors.BinstarError("Could not find EGG-INFO/PKG-INFO file in pypi sdist")

    attrs = dict(Parser().parsestr(data).items())

    package_data = {'name': pop_key(attrs, 'Name'),
                    'summary': pop_key(attrs, 'Summary'),
                    'license': pop_key(attrs, 'License'),
                    }
    release_data = {
                    'version': pop_key(attrs, 'Version'),
                    'description': pop_key(attrs, 'Description', None),
                    'home_page': pop_key(attrs, 'Home-page', None)
                    }
    file_data = {
                 'basename': basename(filename),
                 'attrs': attrs,
                 }

    requires_txt = extract_first(tf, 'EGG-INFO/requires.txt')
    if requires_txt:
        file_data.update(dependencies=parse_requires_txt(requires_txt))

    if len(filename.split('-')) == 4:
        _, _, python_version, platform = filename[:-4].split('-')
    else:
        python_version = 'source'
        platform = None


    file_data.update(platform=platform)

    attrs.update({
                 'packagetype': 'bdist_egg',
                 'python_version': python_version,
                 })

    return package_data, release_data, file_data


def inspect_pypi_package_zip(filename, fileobj):
    filename, fileobj

    tf = zipfile.ZipFile(fileobj)

    data = extract_first(tf, '*/PKG-INFO')
    if data is None:
        raise errors.BinstarError("Could not find EGG-INFO/PKG-INFO file in pypi sdist")

    attrs = dict(Parser().parsestr(data).items())
    package_data = {'name': pop_key(attrs, 'Name'),
                    'summary': pop_key(attrs, 'Summary', None),
                    'license': pop_key(attrs, 'License', None),
                    }
    release_data = {
                    'version': pop_key(attrs, 'Version'),
                    'description': pop_key(attrs, 'Description', None),
                    'home_page': pop_key(attrs, 'Home-page', None)
                    }
    file_data = {
                 'basename': basename(filename),
                 'attrs': attrs,
                 }

    attrs.update({
                 'packagetype': 'bdist_egg',
                 'python_version': 'source',
                 })

    return package_data, release_data, file_data

def inspect_pypi_package_exe(filename, fileobj):

    # ipython-0.12.1.win-amd64.exe
    name_version, windist = filename[:-4].rsplit('.', 1)

    name, version = name_version.split('-', 1)

    package_data = {'name': name}
    release_data = {version: version}
    file_data = {'attrs': {
                           'packagetype': 'bdist_wininst',
                           'python_version': 'source',
                           'windist': windist,
                           },
                 'basename': path.basename(filename),
                }

    return package_data, release_data, file_data

def inspect_pypi_package_rpm(filename, fileobj):
    # ipython-0.12.1.win-amd64.exe
    name_version, rpmarch = filename[:-4].rsplit('.', 1)

    name, version, python_version = name_version.split('-', 2)

    package_data = {'name': name}
    release_data = {version: version}
    file_data = {'attrs': {
                           'packagetype': 'bdist_rpm',
                           'python_version': python_version,
                           'rpmarch': rpmarch,
                           },
                 'basename': path.basename(filename),
                }
    return package_data, release_data, file_data


def inspect_pypi_package(filename, fileobj):
    if filename.endswith('.tar.gz') or filename.endswith('.tar.bz2'):
        return inspect_pypi_package_sdist(filename, fileobj)
    if filename.endswith('.whl'):
        return inspect_pypi_package_whl(filename, fileobj)
    if filename.endswith('.egg'):
        return inspect_pypi_package_egg(filename, fileobj)
    if filename.endswith('.zip'):
        return inspect_pypi_package_zip(filename, fileobj)
    if filename.endswith('.exe'):
        return inspect_pypi_package_exe(filename, fileobj)
    if filename.endswith('.rpm'):
        return inspect_pypi_package_rpm(filename, fileobj)

    name, etx = path.splitext(filename)
    raise TypeError("Can not inspect pypi package with file extension %s" % etx)

def main():
    filename = sys.argv[1]
    with open(filename) as fileobj:
        package_data, release_data, file_data = inspect_pypi_package(filename, fileobj)
    pprint(package_data)
    print('--')
    pprint(release_data)
    print('--')
    pprint(file_data)

if __name__ == '__main__':
    main()
