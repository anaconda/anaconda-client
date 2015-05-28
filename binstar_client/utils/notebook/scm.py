import os
import hashlib

"""
Version control module
* Download files from a project hosted in anaconda-server
* Upload files to anaconda-server
* Upload new files to an existing project in AS
* If local file already in AS, create a new version and upload it

Usage:
    uploader = Uploader(binstar, project)
    scm = SCM(uploader, project)
    scm.local(loca_files_list)
    scm.pull()
"""


class SCMCollection(object):
    """
    Collection of SCM Files.
    You can add files into it and it behaves as a collection
    You can also substract two scm collections. Will stick
    with the newest versions of every file.
    """
    def __init__(self, elements=[]):
        self._elements = elements

    def append(self, element):
        """
        Add's an element to collection.
        If two elements with dame name,
        only leave the newer version
        """
        prev = self.detect(element)
        if prev is None:
            self._elements.append(element)
        else:
            choosen = self.choose(prev, element)
            if choosen != prev:
                self._elements.remove(prev)
                self._elements.append(choosen)

    def detect(self, element):
        """
        Find element with the same name in _elements
        :returns: element/None
        """
        try:
            index = self._elements.index(element)
        except ValueError:
            return None
        else:
            return self._elements[index]

    def choose(self, element_a, element_b):
        """
        Choose between two elements. Sticks with biggest
        """
        if element_a > element_b:
            return element_a
        else:
            return element_b

    def __len__(self):
        return len(self._elements)

    def __repr__(self):
        return self._elements.__repr__()

    def __sub__(self, other):
        return SCMCollection([element for element in self._elements if element not in other._elements])

    def __iter__(self):
        return self._elements.__iter__()


class SCMFile(object):
    """
    Allows easy comparation between files within the SCM
    Filer are the same if they have the same filename and md5
    A file can be bigger than the other if it has an newer version
    """
    def __init__(self, filename, md5=None, version=None):
        self.filename = filename
        self.md5 = md5
        self.version = version

    def __eq__(self, other):
        return self.filename == other.filename and self.md5 == other.md5

    def __gt__(self, other):
        return int(self.version) > int(other.version)

    def __lt__(self, other):
        return int(self.version) < int(other.version)

    def __repr__(self):
        return "<{}|{}|{}>".format(self.filename, self.md5, self.version)


class SCM(object):
    """
    Version control mechanism for notebooks files.
    * Download files from AS
    * Upload new files
    * Upload files with newer version
    """
    def __init__(self, uploader, project, username=None):
        self.uploader = uploader
        self.project = project
        self._username = username
        self._uploaded = SCMCollection([])
        self._local = SCMCollection([])
        self._diff = None

    def pull(self):
        for package in self.uploader.files:
            self._uploaded.append(
                SCMFile(package['basename'], md5=package['md5'], version=package['version'])
            )
        return self._uploaded

    def local(self, elements):
        for element in elements:
            self._local.append(
                SCMFile(element['basename'], md5=element['md5'], version=element['version'])
            )

    @property
    def diff(self):
        if self._diff is None:
            self._diff = self._local - self._uploaded
        return self._diff

    @property
    def username(self):
        if self._username is None:
            self._username = self.binstar.user()['login']
        return self._username


def local_files(files):
    output = []
    for f in files:
        output.append({
            'basename': os.path.basename(f),
            'md5': hashlib.md5(open(f, 'rb').read()).hexdigest(),
            'version': ''
        })
    return output
