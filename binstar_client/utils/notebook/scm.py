class SCMCollection(object):
    _elements = []

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
                print "hellos"
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


class SCMFile(object):
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
    def __init__(self, binstar, username, project):
        self.binstar = binstar
        self.username = username
        self.project = project

    def uploaded_files(self):
        pass
