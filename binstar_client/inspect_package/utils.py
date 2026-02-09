from fnmatch import fnmatch
from zipfile import ZipFile
from tarfile import TarFile

from binstar_client.deprecations import DEPRECATE_IN_1_15_0, REMOVE_IN_2_0_0, deprecated


def extract_first(fileobj, pat):
    if isinstance(fileobj, ZipFile):
        return zipfile_match_and_extract(fileobj, pat)

    if isinstance(fileobj, TarFile):
        return tarfile_match_and_extract(fileobj, pat)

    raise TypeError(
        'Don\'t know how to extract %s file type' % type(fileobj),
    )


def zipfile_match_and_extract(zip_file, pat):
    item_name = next((info.filename for info in zip_file.infolist() if fnmatch(info.filename, pat)), None)
    if item_name is None:
        return None
    return zip_file.read(item_name).decode(errors='ignore')


def tarfile_match_and_extract(tar_file, pat):
    item_name = next((name for name in tar_file.getnames() if fnmatch(name, pat)), None)
    if not item_name:
        return None

    file_obj = tar_file.extractfile(item_name)
    return file_obj.read().decode(errors='ignore')


@deprecated(deprecate_in=DEPRECATE_IN_1_15_0, remove_in=REMOVE_IN_2_0_0)
def safe(version):
    return version.replace('\n', '-').replace('\\', '-').replace('#', '-')


@deprecated(deprecate_in=DEPRECATE_IN_1_15_0, remove_in=REMOVE_IN_2_0_0)
def get_key(data, key, *d):
    value = data.get(key, *d)
    if value == 'UNKNOWN':
        if not d:
            raise KeyError(key)
        value = d[0]
    return value


def pop_key(data, key, *d):
    value = data.pop(key, *d)
    if value == 'UNKNOWN':
        if not d:
            raise KeyError(key)
        value = d[0]
    return value
