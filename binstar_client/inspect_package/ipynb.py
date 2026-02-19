from __future__ import absolute_import, print_function, unicode_literals

import os
import re
from datetime import datetime

import nbformat

from ..utils.notebook.data_uri import data_uri_from
from ..utils.notebook.inflection import parameterize


from binstar_client.deprecations import deprecated, DEPRECATE_IN_1_15_0, REMOVE_IN_2_0_0


@deprecated(deprecate_in=DEPRECATE_IN_1_15_0, remove_in=REMOVE_IN_2_0_0)
def inspect_ipynb_package(filename, fileobj, *args, **kwargs):
    notebook = nbformat.read(fileobj, nbformat.NO_CONVERT)
    summary = notebook.get('metadata', {}).get('summary', 'Jupyter Notebook')
    description = notebook.get('metadata', {}).get('description', 'Jupyter Notebook')

    package_data = {
        'name': re.sub('\\-ipynb$', '', parameterize(os.path.basename(filename))),
        'summary': summary,
        'description': description,
    }

    if 'parser_args' in kwargs and kwargs['parser_args'].thumbnail:
        package_data['thumbnail'] = data_uri_from(kwargs['parser_args'].thumbnail)

    release_data = {
        'version': datetime.now().strftime('%Y.%m.%d.%H%M'),
        'summary': summary,
        'description': description,
    }

    file_data = {
        'basename': os.path.basename(filename),
        'attrs': {},
    }

    return package_data, release_data, file_data
