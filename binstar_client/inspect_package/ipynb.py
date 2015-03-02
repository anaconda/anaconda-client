def inspect_ipynb_package(filename, fileobj):
    package_data = {
        'name': filename,
        'summary': 'summary',
    }
    release_data = {
        'version': '0.0.1',
        'description': ''
    }
    file_data = {
        'basename': '',
        'attrs': {}
    }

    return package_data, release_data, file_data
