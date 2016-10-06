from os.path import basename, dirname, join
import json
import sys
import subprocess

CONDA_PREFIX = sys.prefix
BIN_DIR = 'Scripts' if sys.platform.startswith('win') else 'bin'
CONDA_EXE = join(CONDA_PREFIX, BIN_DIR, 'conda')


def get_conda_root():
    """Get the PREFIX of the conda installation.

    Returns:
        str: the ROOT_PREFIX of the conda installation
    """
    try:
        # Fast-path
        # We're in the root environment
        import conda.config
        conda_root = conda.config.root_dir
    except ImportError:
        # We're not in the root environment.
        envs_dir = dirname(CONDA_PREFIX)
        if basename(envs_dir) == 'envs':
            # We're in a named environment: `conda create -n <name>`
            conda_root = dirname(envs_dir)
        else:
            # We're in an isolated environment: `conda create -p <path>`
            # The only way we can find out is by calling conda.
            try:
                conda_info = json.loads(subprocess.check_output([CONDA_EXE, 'info', '--json']))
                conda_root = conda_info['root_prefix']
            except (ValueError, KeyError, subprocess.CalledProcessError):
                conda_root = None

    return conda_root

CONDA_ROOT = get_conda_root()
