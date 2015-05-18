import os
from binstar_client import errors


class Downloader(object):
    """
    Download a notebook or a data file from Binstar.org
    """
    def __init__(self, binstar, username, project):
        self.binstar = binstar
        self.username = username
        self.project = project
        self.location = project

    def call(self, basename=None, force=False, output=None):
        if output is not None:
            self.location = output
        self.ensure_location(force)
        if basename is None:
            self.download_files(force)
        else:
            self.download_file(basename, force)

    def download(self, dist):
        """
        Download file into location
        """
        requests_handle = self.binstar.download(self.username, self.project, dist['version'], dist['basename'])

        with open(os.path.join(self.location, dist['basename']), 'w') as fdout:
            for chunk in requests_handle.iter_content(4096):
                fdout.write(chunk)

    def download_files(self, force=False):
        for f in self.list_files():
            if self.can_download(f, force):
                self.download(f)

    def download_file(self, basename, force=False):
        dist = next(dist for dist in self.list_files() if dist['basename'] == basename)
        if dist is None:
            raise errors.NotFound(basename)
        if self.can_download(dist, force):
            self.download(dist)
        else:
            raise errors.DestionationPathExists(os.join(self.location), basename)

    def can_download(self, dist, force=False):
        """
        Can download if location/file does not exist or if force=True
        :param dist:
        :param force:
        :return: True/False
        """
        return not os.path.exists(os.path.join(self.location, dist['basename'])) or force

    def ensure_location(self, force):
        """
        Created directory dir
        """
        if not os.path.exists(self.location):
            os.makedirs(self.location)
        elif not force:
            raise errors.DestionationPathExists(self.location)

    def list_files(self):
        """
        List available files in a project
        :return: list
        """
        output = []
        tmp = {}
        files = self.binstar.package(self.username, self.project)['files']

        for f in files:
            if f['basename'] in tmp:
                tmp[f['basename']].append(f)
            else:
                tmp[f['basename']] = [f]

        for basename, versions in tmp.items():
            output.append(max(versions, key=lambda x: int(x['version'])))

        return output
