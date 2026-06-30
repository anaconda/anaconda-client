"""Package type detection utilities for repo channels.

Ported from conda-repo-cli to support proper package type detection
for uploads to anaconda repository channels.
"""

import json
import logging
import os
import tarfile
import zipfile
from enum import Enum
from glob import glob
from os import path
from typing import List, Optional

import typer
from anaconda_cli_base.console import console

logger = logging.getLogger("binstar.repocore.package_utils")


class PackageType(str, Enum):
    """Supported package types for upload."""
    env = "env"
    ipynb = "ipynb"
    conda = "conda"
    pypi = "pypi"
    project = "project"
    sdist = "sdist"
    gra = "gra"


def _is_environment(filename: str) -> bool:
    """Check if file is an environment yaml file."""
    logger.debug("Testing if environment file ..")
    if filename.endswith(".yml") or filename.endswith(".yaml"):
        return True
    logger.debug("No environment file")
    return False


def _is_ipynb(filename: str) -> bool:
    """Check if file is a Jupyter notebook."""
    logger.debug("Testing if ipynb file ..")
    if filename.endswith(".ipynb"):
        return True
    logger.debug("No ipynb file")
    return False


def _is_anaconda_project_yaml(filename: str) -> bool:
    """Check if file is an anaconda-project.yml file."""
    return filename == "anaconda-project.yml" or filename.endswith("/anaconda-project.yml")


def _is_project(filename: str) -> bool:
    """Check if file is a project (directory or archive containing anaconda-project.yml)."""
    logger.debug("Testing if project ..")

    def is_python_file():
        return filename.endswith(".py")

    def is_directory():
        return path.isdir(filename)

    if is_directory() or is_python_file():
        return True

    if filename.endswith(".tar.gz") or filename.endswith(".tar.bz2"):
        compression = filename.rsplit(".", maxsplit=1)[1]
        try:
            with tarfile.open(filename, mode=f"r|{compression}") as tf:
                for name in tf.getnames():
                    if _is_anaconda_project_yaml(name):
                        return True
        except Exception:
            pass

    if filename.endswith(".zip"):
        try:
            with zipfile.ZipFile(filename) as zf:
                for name in zf.namelist():
                    if _is_anaconda_project_yaml(name):
                        return True
        except Exception:
            pass

    logger.debug("Not a project")
    return False


def _is_conda(filename: str) -> bool:
    """Check if file is a conda package."""
    logger.debug("Testing if conda package ..")

    if filename.endswith(".tar.bz2"):
        try:
            with tarfile.open(filename, mode="r|bz2") as tf:
                for info in tf:
                    if info.name == "info/index.json":
                        return True
        except Exception:
            logger.debug("Not conda package - error reading tarball")
            return False
        logger.debug("Not conda package - no 'info/index.json' file in the tarball")
        return False
    logger.debug("Not conda package (file ext is not .tar.bz2)")
    return False


def _is_pypi(filename: str) -> bool:
    """Check if file is a PyPI wheel package."""
    logger.debug("Testing if pypi package ..")
    if filename.endswith(".whl"):
        logger.debug("This is a pypi wheel package")
        return True
    logger.debug("This not is a pypi package (expected .whl)")
    return False


def _is_sdist(filename: str) -> bool:
    """Check if file is a Python source distribution (sdist)."""
    logger.debug("Testing if sdist package ..")
    if filename.endswith(".tar.gz") or filename.endswith(".tgz"):
        try:
            with tarfile.open(filename) as tf:
                if any(name.endswith("/PKG-INFO") for name in tf.getnames()):
                    return True
                else:
                    logger.debug("This not is a sdist package (no '/PKG-INFO' in tarball)")
                    return False
        except Exception:
            logger.debug("This not is a sdist package (error reading tarball)")
            return False
    logger.debug("This not is a sdist package (expected .tgz, .tar.gz).")
    return False


def _is_r(filename: str) -> bool:
    """Check if file is an R package."""
    logger.debug("Testing if R package ..")
    if filename.endswith(".tar.gz") or filename.endswith(".tgz"):
        try:
            with tarfile.open(filename) as tf:
                names = tf.getnames()
                if any(name.endswith("/DESCRIPTION") for name in names) and any(
                    name.endswith("/NAMESPACE") for name in names
                ):
                    return True
                else:
                    logger.debug("This not is an R package (no '*/DESCRIPTION' and '*/NAMESPACE' files).")
        except Exception:
            logger.debug("This not is an R package (error reading tarball).")
    else:
        logger.debug("This not is an R package (expected .tgz, .tar.gz).")
    return False


def _is_sbom(filename: str) -> bool:
    """Check if file is an SBOM (Software Bill of Materials) document."""
    if not filename.endswith(".spdx.json"):
        return False

    logger.debug("Testing if SBOM document ..")
    try:
        with open(filename) as sbom:
            content = json.load(sbom)

        if not content.get("spdxVersion"):
            logger.warning("Document contains no version information!")
            return False

        packages = content.get("packages")
        if not packages or len(packages) < 1:
            logger.warning("Document contains no package information!")
            return False

        checksums = packages[0].get("checksums")
        if not checksums:
            logger.warning("Document contains no package checksums!")
            return False
        sha256s = [x for x in checksums if x.get("algorithm") == "SHA256"]
        if sha256s and sha256s[0].get("checksumValue"):
            return True
        logger.warning("Document does not contain the needed package sha256 hash!")
        return False
    except Exception:
        logger.debug("Error reading SBOM file")
        return False


def detect_package_type(filename: str) -> Optional[str]:
    """
    Detect package type from filename.

    Ported from conda-repo-cli to support repo channel uploads.
    Detection order matches conda-repo-cli priority.

    Args:
        filename: Path to the package file

    Returns:
        Package type string (conda, pypi, sdist, r, ipynb, env, project, sbom) or None
    """
    if isinstance(filename, bytes):
        filename = filename.decode("utf-8", errors="ignore")

    if _is_conda(filename):
        return "conda"
    if _is_project(filename):
        return "project"
    if _is_pypi(filename):
        return "pypi"
    if _is_sdist(filename):
        return "sdist"
    if _is_r(filename):
        return "r"
    if _is_ipynb(filename):
        return "ipynb"
    if _is_environment(filename):
        return "env"
    if _is_sbom(filename):
        return "sbom"
    return None


def windows_glob(item: str) -> List[str]:
    """Handle glob expansion on Windows.

    Args:
        item: File path or pattern

    Returns:
        List of matching file paths
    """
    if os.name == "nt" and "*" in item:
        return glob(item)
    return [item]


def determine_package_type(filename: str, package_type: Optional[PackageType] = None) -> str:
    """Determine the package type from file or explicit argument.

    Args:
        filename: Path to the package file
        package_type: Explicitly specified package type (optional)

    Returns:
        Package type string

    Raises:
        typer.Exit: If package type cannot be detected
    """
    if package_type:
        return package_type.value

    console.print(f"Detecting file type for [cyan]{filename}[/cyan]...")
    detected_type = detect_package_type(filename)

    if detected_type is None:
        console.print(
            f"[red]Error:[/red] Could not detect package type for '{filename}'.\n"
            "Please specify package type with --package-type option."
        )
        raise typer.Exit(1)

    console.print(f"Detected type: [green]{detected_type}[/green]")
    return detected_type
