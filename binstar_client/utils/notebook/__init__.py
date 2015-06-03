try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse
from .uploader import *


def notebook_url(upload_info):
    parsed = urlparse(upload_info['url'])
    if parsed.netloc == 'anaconda.org':
        url = "{}://notebooks.{}{}".format(parsed.scheme, parsed.netloc, parsed.path)
    else:
        url = "{}://{}/notebooks{}".format(parsed.scheme, parsed.netloc, parsed.path)
    return url
