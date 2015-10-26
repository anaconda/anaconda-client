import os
import re
import time
from ..utils.notebook.inflection import parameterize
from ..utils.notebook.data_uri import data_uri_from


class IPythonNotebook(object):
    _name = None
    _version = None
    thumbnail_file = None

    def __init__(self, filename, fileobj, *args, **kwargs):
        self.filename = filename
        self.thumbnail_file = kwargs.get('thumbnail_file', None)

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
            self._version = time.strftime('%Y.%m.%d.%H%M')
        return self._version

    @property
    def thumbnail(self):
        if self.thumbnail_file is None:
            return None
        return data_uri_from(self.thumbnail_file)

    def get_package_data(self):
        if self.thumbnail_file is None:
            return {
                'name': self.name,
                'summary': 'IPython notebook'
            }
        else:
            return {
                'name': self.name,
                'summary': 'IPython notebook',
                'thumbnail': self.thumbnail
            }


def inspect_ipynb_package(filename, fileobj, *args, **kwargs):
    if 'parser_args' in kwargs:
        thumbnail_file = kwargs['parser_args'].thumbnail
        ipython_notebook = IPythonNotebook(filename, fileobj, thumbnail_file=thumbnail_file)
    else:
        ipython_notebook = IPythonNotebook(filename, fileobj)

    package_data = ipython_notebook.get_package_data()
    release_data = {
        'version': ipython_notebook.version,
        'description': ''
    }
    file_data = {
        'basename': ipython_notebook.basename,
        'attrs': {}
    }

    return package_data, release_data, file_data
