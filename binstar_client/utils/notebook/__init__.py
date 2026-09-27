from urllib.parse import urlparse

import nbformat

from binstar_client.commands.download import parse
from binstar_client.deprecations import DEPRECATE_IN_1_15_0, REMOVE_IN_2_0_0, deprecated

deprecated.constant(
    deprecate_in=DEPRECATE_IN_1_15_0,
    remove_in=REMOVE_IN_2_0_0,
    constant="parse",
    value=parse,
    addendum="Use `binstar_client.commands.dowload.parse` instead",
)


@deprecated(deprecate_in=DEPRECATE_IN_1_15_0, remove_in=REMOVE_IN_2_0_0)
def notebook_url(upload_info):
    parsed = urlparse(upload_info['url'])
    if parsed.netloc == 'anaconda.org':
        url = f'{parsed.scheme}://notebooks.{parsed.netloc}{parsed.path}'
    else:
        url = f'{parsed.scheme}://{parsed.netloc}/notebooks{parsed.path}'
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
    except (OSError, ValueError, AttributeError, KeyError, nbformat.reader.NotJSONError):
        return False
