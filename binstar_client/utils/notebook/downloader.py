import os
from time import mktime
from dateutil.parser import parse
from binstar_client.errors import DestionationPathExists


class Downloader(object):
    """
    Download notebook from anaconda.org
    """
    def __init__(self, aserver_api, username, notebook):
        self.aserver_api = aserver_api
        self.username = username
        self.notebook = notebook

    def __call__(self, output='.', force=False):
        self.output = output
        self.ensure_output()
        return self.download_files(force)

    def download_files(self, force=False):
        output = []
        for f in self.list_files():
            if self.can_download(f, force):
                self.download(f)
                output.append(f['basename'])
            else:
                raise DestionationPathExists(f['basename'])
        return output

    def download(self, dist):
        """
        Download file into location
        """
        requests_handle = self.aserver_api.download(self.username, self.notebook,
                                                dist['version'], dist['basename'])

        with open(os.path.join(self.output, dist['basename']), 'wb') as fdout:
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
        List available files in a project (aka notebook)
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
