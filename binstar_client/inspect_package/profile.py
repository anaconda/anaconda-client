import yaml
import os

def inspect_profile_package(filename, fileobj):
    fn_name = os.path.basename(filename)
    name = os.path.splitext(fn_name)[0]
    data = yaml.load(fileobj)

    keys = set(data.keys())
    key_validator = set(['name', 'node_type', 'node_id', 'num_nodes'])

    assert key_validator.issubset(keys)

    package_data = {
        'name': name,
        'summary': 'Anaconda Cluster Profile'
    }
    # version should be read from proifle
    release_data = {
        'version': 1.0,
        'description': ''
    }
    file_data = {
        'basename': fn_name,
        'attrs': data
    }

    return package_data, release_data, file_data
