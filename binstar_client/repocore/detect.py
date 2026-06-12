"""Package type detection for repocore uploads."""

import json
import logging
import tarfile
import zipfile
from os import path

logger = logging.getLogger(__name__)


def is_environment(filename):
    return filename.endswith(".yml") or filename.endswith(".yaml")


def is_ipynb(filename):
    return filename.endswith(".ipynb")


def is_anaconda_project_yaml(filename):
    return filename == "anaconda-project.yml" or filename.endswith("/anaconda-project.yml")


def is_project(filename):
    if path.isdir(filename) or filename.endswith(".py"):
        return True

    if filename.endswith(".tar.gz") or filename.endswith(".tar.bz2"):
        compression = filename.rsplit(".", maxsplit=1)[1]
        with tarfile.open(filename, mode="r|%s" % compression) as tf:
            for name in tf.getnames():
                if is_anaconda_project_yaml(name):
                    return True

    if filename.endswith(".zip"):
        with zipfile.ZipFile(filename) as zf:
            for name in zf.namelist():
                if is_anaconda_project_yaml(name):
                    return True

    return False


def is_conda(filename):
    if filename.endswith(".tar.bz2"):
        try:
            with tarfile.open(filename, mode="r|bz2") as tf:
                for info in tf:
                    if info.name == "info/index.json":
                        break
                else:
                    raise KeyError
        except KeyError:
            return False
        else:
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


def is_sbom(filename):
    if not filename.endswith(".spdx.json"):
        return False

    try:
        with open(filename) as sbom:
            content = json.load(sbom)
    except (OSError, json.JSONDecodeError):
        return False

    if not content.get("spdxVersion"):
        return False

    packages = content.get("packages")
    if not packages or len(packages) < 1:
        return False

    checksums = packages[0].get("checksums")
    if not checksums:
        return False
    sha256s = [x for x in checksums if x.get("algorithm") == "SHA256"]
    return bool(sha256s and sha256s[0].get("checksumValue"))


def detect_package_type(filename):
    """Detect the package type from a filename. Returns None if undetectable."""
    if isinstance(filename, bytes):
        filename = filename.decode("utf-8", errors="ignore")

    if is_conda(filename):
        return "conda"
    if is_project(filename):
        return "project"
    if is_pypi(filename):
        return "pypi"
    if is_sdist(filename):
        return "sdist"
    if is_ipynb(filename):
        return "ipynb"
    if is_environment(filename):
        return "env"
    if is_sbom(filename):
        return "sbom"
    return None
