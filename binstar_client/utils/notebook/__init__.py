import re
from ...errors import BinstarError
from .downloader import *
from .uploader import *
from .finder import *
from .scm import *


def parse(handle):
    """
    >>> parse("user/project:main.ipynb")
    ('user', 'project', 'main.ipynb')
    >>> parse("project")
    (None, 'project', None)
    >>> parse("user/project")
    ('user', 'project', None)

    :param handle: String
    :return: username, project, file
    """
    r = r'^(?P<user0>\w+)/(?P<project0>\w+):(?P<notebook0>\w+)$|^(?P<user1>\w+)/(?P<project1>\w+)$|^(?P<project2>.+)$'

    try:
        parsed = re.compile(r).match(handle).groupdict()
    except AttributeError:
        raise BinstarError("{} can't be parsed".format(handle))

    if parsed['project2'] is not None:
        return None, parsed['project2'], None
    elif parsed['project1'] is not None:
        return parsed['user1'], parsed['project1'], None
    else:
        return parsed['user0'], parsed['project0'], parsed['notebook0']
