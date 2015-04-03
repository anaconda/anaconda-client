import json
import os


class IPythonNotebook(object):
    def __init__(self, filename, fileobj):
        content = json.loads(fileobj.read())
        if content['nbformat'] == 3:
            self.populate_nbformat_2(filename, content)
        else:
            self.populate_nbformat_3(filename, content)

    def populate_nbformat_2(self, filename, content):
        self.basename = os.path.basename(filename)
        self.name = content['metadata']['name'] or \
            self.basename.replace('.ipynb', '')
        self.version = content['metadata'].get('version', '1.0')

    def populate_nbformat_3(self, filename, content):
        self.basename = os.path.basename(filename)
        self.name = self.basename.replace('.ipynb', '')
        self.version = content['metadata'].get('version', '1.0')


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
        'attrs': {}
    }

    return package_data, release_data, file_data
