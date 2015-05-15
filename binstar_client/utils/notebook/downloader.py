import os


class Downloader(object):
    """
    Download a notebook or a data file from Binstar.org
    """
    def __init__(self, binstar, username, project, notebook):
        self.binstar = binstar
        self.username = username
        self.project = project
        self.notebookk = notebook

    def call(self, force=False, output=None):
        location = output or self.project
        self.ensure_location(location)
        for f in self.list_files():
            self.download(f, location)

    def download(self, dist, location):
        requests_handle = self.binstar.download(self.username, self.project, dist['version'], dist['basename'])

        with open(os.path.join(location, dist['basename']), 'w') as fdout:
            for chunk in requests_handle.iter_content(4096):
                fdout.write(chunk)

    def ensure_location(self, d):
        """
        Created directory dir
        """
        if not os.path.exists(d):
            os.makedirs(d)

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
                tmp['basename'].append(f)
            else:
                tmp['basename'] = [f]

        for basename, versions in tmp:
            output.append(max(versions, lambda x: x['version']))

        return output
