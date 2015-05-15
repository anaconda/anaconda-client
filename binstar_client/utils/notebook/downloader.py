class Downloader(object):
    def __init__(self, username, project, notebook):
        self._username = username
        self.project = project
        self._notebook = notebook

    def call(self, force=False, output=None):
        return True
