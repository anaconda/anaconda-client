import yaml
import os
#
# self.binstar.upload(self.username, self.packagename,
#                                        self.version, self.basename, open(self.file),
#                                        distribution_type=ENVIRONMENT_TYPE, attrs=self.env_data)
#         else:

# def upload(self, login, package_name, release, basename, fd, distribution_type,
#            description='', md5=None, size=None, dependencies=None, attrs=None, channels=('main',), callback=None):

# def upload(self, login, package_name, release, basename, fd, distribution_type,
#            description='', md5=None, size=None, dependencies=None, attrs=None, channels=('main',), callback=None):

def inspect_profile_package(filename, fileobj):
    fn_name = os.path.basename(filename)
    name = os.path.splitext(fn_name)[0]
    data = yaml.load(fileobj)
    keys = set(data.values()[0].keys())
    key_validator = set(['node_type', 'node_id', 'num_nodes'])

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
