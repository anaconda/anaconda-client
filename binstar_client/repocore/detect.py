"""Package type detection for repocore uploads."""

import logging
import tarfile

logger = logging.getLogger(__name__)


def is_conda(filename):
    if filename.endswith(".conda"):
        return True
    if filename.endswith(".tar.bz2"):
        try:
            with tarfile.open(filename, mode="r:bz2") as tf:
                tf.getmember("info/index.json")
        except KeyError:
            return False
        return True
    return False


def is_pypi(filename):
    return filename.endswith(".whl")


def is_sdist(filename):
    if filename.endswith(".tar.gz") or filename.endswith(".tgz"):
        with tarfile.open(filename) as tf:
            if any(name.endswith("/PKG-INFO") for name in tf.getnames()):
                return True
    return False


def detect_package_type(filename):
    """Detect the package type from a filename. Returns None if undetectable."""
    if isinstance(filename, bytes):
        filename = filename.decode("utf-8", errors="ignore")

    if is_conda(filename):
        return "conda"
    if is_pypi(filename):
        return "pypi"
    if is_sdist(filename):
        return "sdist"
    return None
