from __future__ import print_function, unicode_literals

from email.parser import Parser
import json
from os import path
import re
import tarfile
import zipfile
import sys

import pkg_resources

from binstar_client import errors
from binstar_client.inspect_package.uitls import extract_first, pop_key


sort_key = lambda i: i['name']

def python_version_check(filedata):
    python_version = sys.version_info.major

    if python_version == 3:
        filedata = Parser().parsestr(filedata).items()
    else:
        filedata = Parser().parsestr(filedata.encode("UTF-8", "replace")).items()

    return filedata



def parse_requirement(line, deps, extras, extra):
    req = pkg_resources.Requirement.parse(line)
    if extra:
        extras[extra].append({'name':req.key, 'specs': req.specs or []})
    else:
        deps.append({'name':req.key, 'specs': req.specs or []})

    deps.sort(key=sort_key)
    for extra in extras.values():
        extra.sort(key=sort_key)

def parse_requires_txt(requires_txt):
    deps = []
    error = False
    extras = {}
    extra = None

    for line in requires_txt.split('\n'):
        line = line.strip()

        if not line: continue

        if line.startswith('[') and line.endswith(']'):
            extra = line[1:-1]
            extras.setdefault(extra, [])
            # Dont parse this requirement
            continue
        try:
            parse_requirement(line, deps, extras, extra)
        except ValueError as err:
            error = True
    extras = [{'name': k, 'depends': sorted(v, key=sort_key)} for (k, v) in extras.items()]

    return {'has_dep_errors': error, 'depends': sorted(deps, key=sort_key),
            'extras': sorted(extras, key=sort_key)}

def format_rqeuirements(requires):
    obj = []
    for req in requires:
        req = req.strip()
        req_spec = req.split(' ', 1)
        if len(req_spec) == 1:
            obj.append({'name': req, 'specs': []})
        else:
            req, spec = req_spec
            spec = spec.strip()
            if spec[0] == '(': spec = spec[1:]
            if spec[-1] == ')': spec = spec[:-1]

            req = pkg_resources.Requirement.parse('%s %s' % (req, spec))
            obj.append({'name': req.key, 'specs': req.specs or []})

    return obj

def format_run_requires_metadata(run_requires):
    deps = []
    extras = []
    environments = []
    for run_require in run_requires:
        extra = run_require.get('extra')
        env = run_require.get('environment')
        requires = run_require['requires']

        if env:
            obj = []
            environments.append({'name': env, 'depends': obj})
        elif extra is None:
            obj = deps
        else:
            obj = []
            extras.append({'name': extra, 'depends': obj})

        obj.extend(format_rqeuirements(requires))

    deps.sort(key=sort_key)
    extras.sort(key=sort_key)
    for extra in extras:
        extra['depends'].sort(key=sort_key)

    attrs = {'has_dep_errors': False, 'depends': sorted(deps, key=sort_key),
             'extras':extras,
             'environments': environments}

    return attrs

def format_requires_metadata(run_requires):
    deps = []
    extras = []

    extras_re = re.compile('extra == [\'\"](.*)[\'\"]')
    has_dep_errors = False

    if not isinstance(run_requires, dict):
        if isinstance(run_requires, basestring):
            run_requires = {'': [run_requires]}
        else:
            has_dep_errors = True
            run_requires = {}

    for key, requirements in run_requires.items():
        is_extra = extras_re.match(key)
        if is_extra:
            extra = is_extra.groups()[0]
            if extra is None:
                obj = deps
            else:
                obj = []
                extras.append({'name': extra, 'depends': obj})

        else:
            obj = deps

        obj.extend(format_rqeuirements(requirements))

    attrs = {'has_dep_errors': has_dep_errors,
             'depends': deps, 'extra_depends':extras}

    return attrs

def format_wheel_json_metadata(data, filename, zipfile):

    package_data = {'name': pop_key(data, 'name'),
                    'summary': pop_key(data, 'summary', None),
                    'license': pop_key(data, 'license', None)}
    description_doc = (data.get('document_names') or {}).get('description')

    # Metadata version 2.0
    if not description_doc:
        description_doc = data.get('extensions', {}).get('python.details', {}).get('document_names', {}).get('description')

    if description_doc:
        description = extract_first(zipfile, '*.dist-info/%s' % description_doc).strip()
    else:
        description = None

    home_page = (data.get('project_urls', {})).get('Home')
    if not home_page:
        home_page = data.get('extensions', {}).get('python.details', {}).get('project_urls', {}).get('Home')

    release_data = {'version': pop_key(data, 'version'),
                    'description': description,
                    'home_page': home_page}

    attrs = {'packagetype': 'bdist_wheel',
             'python_version':'source',
             'pypi': [{'key':k, 'value': v} for (k, v) in data.items()]}

    if data.get('run_requires', {}):
        dependencies = format_run_requires_metadata(data['run_requires'])
    else:
        dependencies = format_requires_metadata(data.get('requires', {}))


    file_data = {'basename': path.basename(filename),
                 'attrs': attrs,
                 'dependencies': dependencies}

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

    filename = path.basename(filename)
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

    file_data.setdefault('attrs', {})

    file_data['attrs'] = dict(build_no=build_no, python_version=python_version, abi=abi,
                              packagetype='bdist_wheel')

    file_data.update(platform=platform)
    return package_data, release_data, file_data


def disutils_dependencies(config_items):
    requirements = [v for k, v in config_items if k == 'Requires']
    depends = format_rqeuirements(requirements)

    return {'depends':depends,
            'extras': [],
            'has_dep_errors': False}


def inspect_pypi_package_sdist(filename, fileobj):

    tf = tarfile.open(filename, fileobj=fileobj)

    data = extract_first(tf, '*.egg-info/PKG-INFO')

    distrubite = False
    if data is None:
        data = extract_first(tf, '*/PKG-INFO')
        distrubite = True
        if data is None:
            raise errors.NoMetadataError("Could not find *.egg-info/PKG-INFO file in pypi sdist")
    config_items = python_version_check(data)
    attrs = dict(config_items)
    name = pop_key(attrs, 'Name', None)

    if name is None:
        name = filename.split('-', 1)[0]

    package_data = {'name': name,
                    'summary': pop_key(attrs, 'Summary', None),
                    'license': pop_key(attrs, 'License', None)}

    release_data = {'version': pop_key(attrs, 'Version'),
                    'description': pop_key(attrs, 'Description', None),
                    'home_page': pop_key(attrs, 'Home-page', None)}

    file_data = {'basename': path.basename(filename),
                 'attrs': {
                     'packagetype': 'sdist',
                     'python_version':'source',
                     }
                }


    if distrubite:  # Distrubite does not create dep files
        file_data.update(dependencies=disutils_dependencies(config_items))

    requires_txt = extract_first(tf, '*.egg-info/requires.txt')
    if requires_txt:
        file_data.update(dependencies=parse_requires_txt(requires_txt))

    return package_data, release_data, file_data


def inspect_pypi_package_egg(filename, fileobj):
    tf = zipfile.ZipFile(fileobj)

    data = extract_first(tf, 'EGG-INFO/PKG-INFO')
    if data is None:
        raise errors.NoMetadataError("Could not find EGG-INFO/PKG-INFO file in pypi sdist")
    attrs = dict(python_version_check(data))

    package_data = {'name': pop_key(attrs, 'Name'),
                    'summary': pop_key(attrs, 'Summary', None),
                    'license': pop_key(attrs, 'License', None)}

    release_data = {'version': pop_key(attrs, 'Version'),
                    'description': pop_key(attrs, 'Description', None),
                    'home_page': pop_key(attrs, 'Home-page', None)}

    if len(filename.split('-')) == 4:
        _, _, python_version, platform = filename[:-4].split('-')
    else:
        python_version = 'source'
        platform = None

    file_data = {'basename': path.basename(filename),
                 'attrs': {'packagetype': 'bdist_egg',
                           'python_version': python_version},
                 'platform': platform}

    requires_txt = extract_first(tf, 'EGG-INFO/requires.txt')
    if requires_txt:
        file_data.update(dependencies=parse_requires_txt(requires_txt))

    return package_data, release_data, file_data


def inspect_pypi_package_zip(filename, fileobj):
    filename, fileobj

    tf = zipfile.ZipFile(fileobj)

    data = extract_first(tf, '*/PKG-INFO')
    if data is None:
        raise errors.NoMetadataError("Could not find EGG-INFO/PKG-INFO file in pypi sdist")

    attrs = dict(Parser().parsestr(data.encode("UTF-8", "replace")).items())

    package_data = {'name': pop_key(attrs, 'Name'),
                    'summary': pop_key(attrs, 'Summary', None),
                    'license': pop_key(attrs, 'License', None)}

    release_data = {'version': pop_key(attrs, 'Version'),
                    'description': pop_key(attrs, 'Description', None),
                    'home_page': pop_key(attrs, 'Home-page', None)}

    file_data = {'basename': path.basename(filename),
                 'attrs': {
                     'packagetype': 'bdist_egg',
                     'python_version': 'source'}
                 }

    return package_data, release_data, file_data

def inspect_pypi_package_exe(filename, fileobj):

    # ipython-0.12.1.win-amd64.exe
    name_version, windist = filename[:-4].rsplit('.', 1)

    name, version = name_version.split('-', 1)

    package_data = {'name': name}
    release_data = {'version': version}

    file_data = {'attrs': {'packagetype': 'bdist_wininst',
                           'python_version': 'source',
                           'windist': windist},
                 'basename': path.basename(filename)}

    return package_data, release_data, file_data

def inspect_pypi_package_rpm(filename, fileobj):
    # ipython-0.12.1.win-amd64.exe
    name_version, rpmarch = filename[:-4].rsplit('.', 1)

    name, version, python_version = name_version.split('-', 2)

    package_data = {'name': name}
    release_data = {'version': version}

    file_data = {'attrs': {'packagetype': 'bdist_rpm',
                           'python_version': python_version,
                           'rpmarch': rpmarch},
                 'basename': path.basename(filename)}

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

    _, etx = path.splitext(filename)
    raise errors.NoMetadataError("Can not inspect pypi package with file extension %s" % etx)

# Test Package: https://pypi.python.org/packages/source/F/Flask-Bower/Flask-Bower-1.1.1.tar.gz
# Test Package: https://pypi.python.org/packages/2.7/i/ipython/ipython-3.0.0-py2-none-any.whl
# Test Package: https://pypi.python.org/packages/source/i/ipython/ipython-3.0.0.tar.gz

def main():
    import sys
    from pprint import pprint

    filename = sys.argv[1]

    if filename.startswith('https://') or filename.startswith('http://'):
        import requests, io
        data = requests.get(filename, stream=True).raw.read()
        fileobj = io.BytesIO(data)
    else:
        fileobj = open(filename)

    package_data, release_data, file_data = inspect_pypi_package(filename, fileobj)
    pprint(package_data)
    print('--')
    pprint(release_data)
    print('--')
    pprint(file_data)

if __name__ == '__main__':
    main()
