import base64
import mimetypes
import os
import re
import sys
import requests
from ...errors import ImageTooBig

MAX_IMAGE_SIZE = 1024 * 512  # 512Kb


class DataURIConverter(object):
    def __init__(self, location):
        self.location = location
        self.mime, _ = mimetypes.guess_type(location)

    def __call__(self):
        if os.path.exists(self.location):
            with open(self.location, "rb") as fp:
                return self._encode(fp.read())
        elif self.is_url():
            content = requests.get(self.location).content
            return self._encode(content)
        else:
            raise IOError("{} not found".format(self.location))

    def is_py3(self):
        return sys.version_info[0] == 3

    def is_url(self):
        regex = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return self.location is not None and regex.search(self.location)

    def _encode(self, content):
        if self.is_py3():
            data64 = base64.b64encode(content).decode("ascii")
        else:
            data64 = content.encode('base64').replace("\n", "")
        return data64


def data_uri_from(location):
    return DataURIConverter(location)()
