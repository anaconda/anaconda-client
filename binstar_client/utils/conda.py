from os.path import basename, dirname, join
import json
import sys
import subprocess

WINDOWS = sys.platform.startswith('win')
CONDA_PREFIX = sys.prefix
BIN_DIR = 'Scripts' if WINDOWS else 'bin'
CONDA_EXE = join(CONDA_PREFIX, BIN_DIR,
                 'conda.exe' if WINDOWS else 'conda')


# this function is broken out for monkeypatch by unit tests,
# so we can test the ImportError handling
def _import_conda_root():
    import conda.config
    return conda.config.root_dir


def _conda_root_from_conda_info():
    try:
        output = subprocess.check_output([CONDA_EXE, 'info', '--json']).decode("utf-8")
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
        envs_dir = dirname(CONDA_PREFIX)
        if basename(envs_dir) == 'envs':
            # We're in a named environment: `conda create -n <name>`
            conda_root = dirname(envs_dir)
        else:
            # We're in an isolated environment: `conda create -p <path>`
            # The only way we can find out is by calling conda.
            conda_root = _conda_root_from_conda_info()

    return conda_root

CONDA_ROOT = get_conda_root()
