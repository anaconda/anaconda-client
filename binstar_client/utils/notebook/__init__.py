import os
from binstar_client import errors
from uploader import *


def parse(handle):
    """
    Handle can take the form of:
        notebook
        path/to/notebook[.ipynb]
        project:notebook[.ipynb]
    :param handle: String
    :return: (project, notebook)
    :raises: NotebookNotFound
    """

    if ':' in handle:
        project, filepath = handle.split(':', 1)
    else:
        project = None
        filepath = handle

    if not filepath.endswith('.ipynb'):
        filepath += '.ipynb'

    if not os.path.isfile(filepath):
        raise errors.NotebookNotExist(filepath)

    notebook = os.path.splitext(os.path.basename(filepath))[0]
    if project is None:
        project = notebook

    return project, notebook
