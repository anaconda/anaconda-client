import time
from os.path import basename
from binstar_client import errors


class Uploader(object):
    msg = None
    _package = None
    _release = None

    def __init__(self, binstar, project, username=None, version=None, summary=None):
        self.project = project
        self._username = username
        self._version = version
        self._summary = summary
        self.binstar = binstar

    def upload(self, filename, force=False):
        """
        Uploads a notebook
        :param force: True/False
        :return: True/False
        """
        if self.package and self.release:
            try:
                self.binstar.upload(self.username, self.project, self.version,
                                    basename(filename), open(filename, 'rb'), filename.split('.')[-1])
                return True
            except errors.Conflict:
                if force:
                    self.remove()
                    return self.upload()
                else:
                    self.msg = "Conflict: {} already exist in {}/{}".format(filename, self.project, self.version)
                    return False
        else:
            return False

    def remove(self):
        return self.binstar.remove_dist(self, self.username, self.project, self.version, basename=self.notebook)

    @property
    def username(self):
        if self._username is None:
            self._username = self.binstar.user()['login']
        return self._username

    @property
    def version(self):
        if self._version is None:
            self._version = str(int(time.time()))
        return self._version

    @property
    def summary(self):
        if self._summary is None:
            self._summary = "IPython notebook project"
        return self._summary

    @property
    def package(self):
        if self._package is None:
            try:
                self._package = self.binstar.package(self.username, self.project)
            except errors.NotFound:
                try:
                    self._package = self.binstar.add_package(self.username, self.project, summary=self.summary)
                except errors.BinstarError:
                    self.msg = "Project {} can not be created. Maybe you are unauthorized.".format(self.project)
                    self._package = None
        return self._package

    @property
    def release(self):
        if self._release is None:
            try:
                self._release = self.binstar.release(self.username, self.project, self.version)
            except errors.NotFound:
                self._release = self.binstar.add_release(self.username, self.project, self.version, None, None, None)
        return self._release

"""
Use cases:

* There is nothing
    * Create a project
    * Create a version
    * Upload notebook as distribution
* Project exists and notebook not exist
    * upload notebook as distribution of the latest release
* Project exist and notebook exist
    * show warning
    * if --force is activated, overwrite last release
* If version is specified and version does not exist
    * create a new release with version, upload notebook
* If version is specified and version exist
    * upload notebook
"""