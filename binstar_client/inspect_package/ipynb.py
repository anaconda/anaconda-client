import json


class IPythonNotebook(object):
    def __init__(self, fileobj):
        content = json.loads(fileobj.read())
        self.basename = fileobj.name

        self.signature = content['metadata']['signature']
        if content['metadata']['name'] == '':
            self.name = fileobj.name
        else:
            self.name = content['metadata']['name']


def inspect_ipynb_package(filename, fileobj):
    ipython_notebook = IPythonNotebook(fileobj)

    package_data = {
        'name': ipython_notebook.name,
        'summary': 'IPython notebook'
    }
    release_data = {
        'version': 'version',
        'description': ''
    }
    file_data = {
        'basename': ipython_notebook.name,
        'attrs': {
            'signature': ipython_notebook.signature
        }
    }

    return package_data, release_data, file_data
