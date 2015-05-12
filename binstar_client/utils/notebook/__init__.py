import os
from binstar_client import errors
from .uploader import *


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


class Finder(object):
    """
    You may pass a list of files or a single directory
    It will return two list:
    * valid uploadable files
    * invalid files/directories
    """
    extensions = ['ipynb', 'csv', 'json']

    def __init__(self, elements):
        self.elements = elements
        self.first = elements[0]

    def parse(self):
        if self.one_directory():
            return self.valid_files_from_dir()
        else:
            return self.valid_files_from_elements()

    def one_directory(self):
        return len(self.elements) == 1 and os.path.isdir(self.first)

    def valid_files_from_dir(self):
        valid = []
        invalid = []
        for element in os.listdir(self.elements[0]):
            if element.startswith('.'):
                continue
            elif self.is_valid(element):
                valid.append(element)
            else:
                invalid.append(element)

        return valid, invalid

    def valid_files_from_elements(self):
        valid = []
        invalid = []

        for element in self.elements:
            if self.is_valid(element):
                valid.append(element)
            else:
                invalid.append(element)

        return valid, invalid

    def is_valid(self, element, prefix=''):
        return os.path.isfile(os.path.join(prefix, element)) and self.valid_extension(element)

    def valid_extension(self, element):
        for extension in self.extensions:
            if element.endswith(extension):
                return True
        return False
