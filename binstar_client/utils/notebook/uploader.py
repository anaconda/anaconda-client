import os
import time
from os.path import basename
from binstar_client import errors
from .inflection import parameterize

VALID_FORMATS = ['ipynb', 'csv', 'yml', 'yaml', 'json', 'md', 'rst', 'txt']


class Uploader(object):
    """
    * Find or create a package (project)
    * Find or create release (version)
    * List files from project
    * Upload new files to project
    """
    msg = None
    _package = None
    _release = None
    _project = None

    def __init__(self, binstar, filepath, **kwargs):
        self.binstar = binstar
        self.filepath = filepath
        self._username = kwargs.get('user', None)
        self._version = kwargs.get('version', None)
        self._summary = kwargs.get('summary', None)

    def upload(self, force=False):
        """
        Uploads a notebook
        :param force: True/False
        :return: True/False
        """
        if self.package and self.release:
            try:
                return self.binstar.upload(self.username, self.project, self.version,
                                           basename(self.filepath), open(self.filepath, 'rb'),
                                           self.filepath.split('.')[-1])
            except errors.Conflict:
                if force:
                    self.remove()
                    return self.upload()
                else:
                    self.msg = "Conflict: {} already exist in {}/{}".format(self.filepath,
                                                                            self.project,
                                                                            self.version)
                    return False
        else:
            return False

    def remove(self):
        return self.binstar.remove_dist(self, self.username, self.project, self.version, basename=self.notebook)

    @property
    def project(self):
        return parameterize(os.path.basename(self.filepath))

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
            self._summary = "IPython notebook"
        return self._summary

    @property
    def package(self):
        if self._package is None:
            try:
                self._package = self.binstar.package(self.username, self.project)
            except errors.NotFound:
                try:
                    self._package = self.binstar.add_package(self.username, self.project,
                                                             summary=self.summary)
                except errors.BinstarError:
                    self.msg = "Project {} can not be created. Maybe you are unauthorized.".\
                        format(self.project)
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

    @property
    def files(self):
        return self.package['files']
