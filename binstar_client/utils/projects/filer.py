from io import BytesIO
import tarfile
import tempfile


def tar_it(pfiles, fd=BytesIO()):
    with tarfile.open(mode='w', fileobj=fd) as tar:
        for pfile in pfiles:
            tar.add(pfile.fullpath, arcname=pfile.relativepath)
    return fd


def memory_tar(pfiles):
    c = BytesIO()
    return tar_it(c)


def tempfile_tar(pfiles):
    with tempfile.NamedTemporaryFile() as ft:
        return tar_it(pfiles, ft)


def output_file_tar(pfiles, filename='/tmp/anaconda.tar'):
    with open(filename, 'wb') as ft:
        return tar_it(pfiles, ft)
