from urllib.parse import urlparse

import nbformat

from ...errors import BinstarError

from binstar_client.deprecations import deprecated, DEPRECATE_IN_1_15_0, REMOVE_IN_2_0_0


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
    if len(components) == 2:
        return components[0], components[1]
    raise BinstarError("{} can't be parsed".format(handle))


@deprecated(deprecate_in=DEPRECATE_IN_1_15_0, remove_in=REMOVE_IN_2_0_0)
def notebook_url(upload_info):
    parsed = urlparse(upload_info['url'])
    if parsed.netloc == 'anaconda.org':
        url = '{}://notebooks.{}{}'.format(parsed.scheme, parsed.netloc, parsed.path)
    else:
        url = '{}://{}/notebooks{}'.format(parsed.scheme, parsed.netloc, parsed.path)
    return url


@deprecated(deprecate_in=DEPRECATE_IN_1_15_0, remove_in=REMOVE_IN_2_0_0)
def has_environment(nb_file):
    if nbformat is None:
        return False

    try:
        with open(nb_file) as file:
            data = file.read()
        notebook = nbformat.reader.reads(data)
        return 'environment' in notebook['metadata']
    except (ValueError, AttributeError, KeyError, IOError, nbformat.reader.NotJSONError):
        return False
