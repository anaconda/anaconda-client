import re
try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse
from .uploader import *
from ...errors import BinstarError
from .downloader import *
from .uploader import *


def parse(handle):
    """
    >>> parse("user/notebook")
    ('user', 'notebook')
    >>> parse("notebook")
    (None, 'notebook')

    :param handle: String
    :return: username, notebooks
    """

    components = handle.split('/', 1)
    if len(components) == 1:
        return None, components[0]
    elif len(components) == 2:
        return components[0], components[1]
    else:
        raise BinstarError("{} can't be parsed".format(handle))


def notebook_url(upload_info):
    parsed = urlparse(upload_info['url'])
    if parsed.netloc == 'anaconda.org':
        url = "{}://notebooks.{}{}".format(parsed.scheme, parsed.netloc, parsed.path)
    else:
        url = "{}://{}/notebooks{}".format(parsed.scheme, parsed.netloc, parsed.path)
    return url
