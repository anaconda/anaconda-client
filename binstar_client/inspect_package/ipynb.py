import json
import os


class IPythonNotebook(object):
    def __init__(self, filename, fileobj):
        content = json.loads(fileobj.read())
        self.name = content['metadata']['name'] or filename
        self.basename = os.path.basename(filename)
        self.signature = content['metadata']['signature']

        if 'version' in content['metadata']:
            self.version = content['metadata']['version']
        else:
            self.version = '1.0'


def inspect_ipynb_package(filename, fileobj):
    ipython_notebook = IPythonNotebook(filename, fileobj)


    package_data = {
        'name': ipython_notebook.name,
        'summary': 'IPython notebook'
    }
    release_data = {
        'version': ipython_notebook.version,
        'description': ''
    }
    file_data = {
        'basename': ipython_notebook.basename,
        'attrs': {
            'signature': ipython_notebook.signature
        }
    }

    return package_data, release_data, file_data
