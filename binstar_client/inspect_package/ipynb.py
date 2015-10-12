import os
import re
import time
from ..utils.notebook.inflection import parameterize


class IPythonNotebook(object):
    _name = None
    _version = None

    def __init__(self, filename, fileobj):
        self.filename = filename

    @property
    def basename(self):
        return os.path.basename(self.filename)

    @property
    def name(self):
        if self._name is None:
            return re.sub('\-ipynb$', '', parameterize(os.path.basename(self.filename)))
        return self._name

    @property
    def version(self):
        if self._version is None:
            self._version = time.strftime('%Y.%m.%d-%H%M')
        return self._version


def inspect_ipynb_package(filename, fileobj, *args, **kwargs):
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
