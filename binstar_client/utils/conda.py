# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring

import json
import subprocess  # nosec
import sys
import os
from os.path import basename, dirname


ENV_PREFIX = sys.prefix


# this function is broken out for monkeypatch by unit tests,
# so we can test the ImportError handling
def _import_conda_root():
    import conda.config  # pylint: disable=import-error,import-outside-toplevel
    return conda.config.root_dir


def _conda_root_from_conda_info():
    command = os.environ.get('CONDA_EXE', 'conda')
    if not command:
        return None
    try:
        output = subprocess.check_output([
            command, 'info', '--json'], creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
        ).decode('utf-8')  # nosec
        conda_info = json.loads(output)
        return conda_info['root_prefix']
    except (ValueError, KeyError, subprocess.CalledProcessError):
        return None


def get_conda_root():
    """Get the PREFIX of the conda installation.

    Returns:
        str: the ROOT_PREFIX of the conda installation
    """
    try:
        # Fast-path
        # We're in the root environment
        conda_root = _import_conda_root()
    except ImportError:
        # We're not in the root environment.
        envs_dir = dirname(ENV_PREFIX)
        if basename(envs_dir) == 'envs':
            # We're in a named environment: `conda create -n <name>`
            conda_root = dirname(envs_dir)
        else:
            # We're in an isolated environment: `conda create -p <path>`
            # The only way we can find out is by calling conda.
            conda_root = _conda_root_from_conda_info()

    return conda_root


CONDA_ROOT = get_conda_root()
