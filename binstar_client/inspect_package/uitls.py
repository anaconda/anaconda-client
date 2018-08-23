from __future__ import print_function, unicode_literals

from fnmatch import fnmatch
from zipfile import ZipFile
from tarfile import TarFile


def extract_first(fileobj, pat):
    if isinstance(fileobj, ZipFile):
        return zipfile_match_and_extract(fileobj, pat)
    elif isinstance(fileobj, TarFile):
        return tarfile_match_and_extract(fileobj, pat)
    else:
        raise Exception("Don't know how to extract %s file type" % type(fileobj))


def zipfile_match_and_extract(zf, pat):
    m = lambda fn: fnmatch(fn, pat)
    item_name = next((i.filename for i in zf.infolist() if m(i.filename)), None)
    if item_name is None:
        return None
    return zf.read(item_name).decode(errors='ignore')


def tarfile_match_and_extract(tf, pat):
    m = lambda fn: fnmatch(fn, pat)
    item_name = next((name for name in tf.getnames() if m(name)), None)
    if not item_name:
        return None

    fd = tf.extractfile(item_name)
    return fd.read().decode(errors='ignore')


def safe(version):
    return version.replace('\n', '-').replace('\\', '-').replace('#', '-')


def get_key(data, k, *d):
    value = data.get(k, *d)
    if value == 'UNKNOWN':
        if not d:
            raise KeyError(k)
        value = d[0]
    return value


def pop_key(data, k, *d):
    value = data.pop(k, *d)
    if value == 'UNKNOWN':
        if not d:
            raise KeyError(k)
        value = d[0]
    return value
