from time import mktime
from dateutil.parser import parse
from collections import OrderedDict
import os

from binstar_client.errors import DestionationPathExists


class Downloader(object):
    """
    Download files from your Anaconda repository.
    """

    def __init__(self, aserver_api, username, notebook):
        self.aserver_api = aserver_api
        self.username = username
        self.notebook = notebook

    def __call__(self, package_types, output='.', force=False):
        self.output = output
        self.ensure_output()
        return self.download_files(package_types, force)

    def list_download_files(self, package_types, output='.', force=False):
        """
        This additional method was created to better handle the log output
        as files are downloaded one by one on the commands/download.py.
        """
        self.output = output
        self.ensure_output()
        files = OrderedDict()
        for f in self.list_files():
            # Check type
            pkg_type = f.get('type') or ''
            if pkg_type in package_types:
                if self.can_download(f, force):
                    files[f['basename']] = f
                else:
                    raise DestionationPathExists(f['basename'])
        return files

    def download_files(self, package_types, force=False):
        output = []
        for f in self.list_files():
            # Check type
            pkg_type = f.get('type') or ''
            if pkg_type in package_types:
                if self.can_download(f, force):
                    self.download(f)
                    output.append(f['basename'])
                else:
                    raise DestionationPathExists(f['basename'])
        return sorted(output)

    def download(self, dist):
        """
        Download file into location.
        """
        filename = dist['basename']
        requests_handle = self.aserver_api.download(
            self.username, self.notebook, dist['version'], filename
        )

        if not os.path.exists(os.path.dirname(filename)):
            try:
                os.makedirs(os.path.dirname(filename))
            except OSError:
                pass

        with open(os.path.join(self.output, filename), 'wb') as fdout:
            for chunk in requests_handle.iter_content(4096):
                fdout.write(chunk)

    def can_download(self, dist, force=False):
        """
        Can download if location/file does not exist or if force=True
        :param dist:
        :param force:
        :return: True/False
        """
        return not os.path.exists(os.path.join(self.output, dist['basename'])) or force

    def ensure_output(self):
        """
        Ensure output's directory exists
        """
        if not os.path.exists(self.output):
            os.makedirs(self.output)

    def list_files(self):
        """
        List available files in a project (aka notebook).
        :return: list
        """
        output = []
        tmp = {}

        files = self.aserver_api.package(self.username, self.notebook)['files']

        for f in files:
            if f['basename'] in tmp:
                tmp[f['basename']].append(f)
            else:
                tmp[f['basename']] = [f]

        for basename, versions in tmp.items():
            try:
                output.append(max(versions, key=lambda x: int(x['version'])))
            except ValueError:
                output.append(
                    max(versions, key=lambda x: mktime(parse(x['upload_time']).timetuple()))
                )
            except:
                output.append(versions[-1])

        return output
