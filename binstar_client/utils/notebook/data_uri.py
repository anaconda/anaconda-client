import base64
import io
import os
import sys

import requests

from six.moves.urllib.parse import urlparse

try:
    from PIL import Image
except ImportError:
    Image = None

from ...errors import PillowNotInstalled

THUMB_SIZE = (340, 210)


class DataURIConverter(object):
    def __init__(self, location):
        self.check_pillow_installed()
        self.location = location

    def check_pillow_installed(self):
        if Image is None:
            raise PillowNotInstalled()

    def __call__(self):
        if os.path.exists(self.location):
            with open(self.location, "rb") as fp:
                return self._encode(self.resize_and_convert(fp).read())
        elif self.is_url():
            content = requests.get(self.location).content
            fp = io.BytesIO()
            fp.write(content)
            fp.seek(0)
            return self._encode(self.resize_and_convert(fp).read())
        else:
            raise IOError("{} not found".format(self.location))

    def resize_and_convert(self, fp):
        im = Image.open(fp)
        im.thumbnail(THUMB_SIZE)
        out = io.BytesIO()
        im.save(out, format='png')
        out.seek(0)
        return out

    def is_py3(self):
        return sys.version_info[0] == 3

    def is_url(self):
        return self.location is not None and urlparse(self.location).scheme in ['http', 'https']

    def _encode(self, content):
        if self.is_py3():
            data64 = base64.b64encode(content).decode("ascii")
        else:
            data64 = content.encode('base64').replace("\n", "")
        return data64


def data_uri_from(location):
    return DataURIConverter(location)()
