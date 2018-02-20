from __future__ import absolute_import, print_function, unicode_literals

import os
import re
import time

import nbformat

from ..utils.notebook.data_uri import data_uri_from
from ..utils.notebook.inflection import parameterize


def _get_name(filename):
    return re.sub('\-ipynb$', '', parameterize(os.path.basename(filename)))


def inspect_ipynb_package(filename, fileobj, *args, **kwargs):
    notebook = nbformat.read(fileobj, nbformat.NO_CONVERT)
    summary = notebook['metadata'].get('summary', 'Jupyter Notebook')
    description = notebook['metadata'].get('description', 'Jupyter Notebook')

    package_data = {
        'name': _get_name(filename),
        'summary': summary,
        'description': description,
    }

    if 'parser_args' in kwargs and kwargs['parser_args'].thumbnail:
        package_data['thumbnail'] = data_uri_from(kwargs['parser_args'].thumbnail)

    release_data = {
        'version': time.strftime('%Y.%m.%d.%H%M'),
        'summary': summary,
        'description': description,
    }

    file_data = {
        'basename': os.path.basename(filename),
        'attrs': {}
    }

    return package_data, release_data, file_data
