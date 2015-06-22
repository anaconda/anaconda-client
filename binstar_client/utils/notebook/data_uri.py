import os
import base64
import mimetypes
import requests


class DataURIConverter(object):
    def __init__(self, location):
        self.location = location
        self.mime, _ = mimetypes.guess_type(location)

    def __call__(self):
        if os.path.exists(self.location):
            with open(self.location, "rb") as fp:
                data64 = base64.b64encode(fp.read()).decode("ascii")
        else:
            r = requests.get(self.location)
            data64 = base64.b64encode(bytes(r.text, 'utf-8')).decode('ascii')
        return u'data:%s;base64,%s' % (self.mime, data64)


def data_uri_from(location):
    return DataURIConverter(location)()
