import re
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
    r = r'^(?P<user1>\w+)/(?P<notebook1>\w+)$|^(?P<notebook2>.+)$'

    try:
        parsed = re.compile(r).match(handle).groupdict()
    except AttributeError:
        raise BinstarError("{} can't be parsed".format(handle))

    if parsed['notebook2'] is not None:
        return None, parsed['notebook2'], None
    else:
        return parsed['user1'], parsed['notebook1'], None
