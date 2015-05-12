import os


class Finder(object):
    """
    You can pass a list of files or a single directory
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
        for element in os.listdir(self.first):
            if element.startswith('.'):
                continue
            elif self.is_valid(element, self.first):
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
