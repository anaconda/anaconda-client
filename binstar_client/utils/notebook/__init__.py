import nbformat

from six.moves.urllib.parse import urlparse

from .uploader import *
from .downloader import *
from ...errors import BinstarError


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


def has_environment(nb_file):
    if nbformat is None:
        return False

    try:
        with open(nb_file) as fb:
            data = fb.read()
        nb = nbformat.reader.reads(data)
        return 'environment' in nb['metadata']
    except (AttributeError, KeyError):
        return False
    except (IOError, nbformat.reader.NotJSONError):
        return False
