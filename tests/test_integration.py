import os
import subprocess

import pytest

from binstar_client.__about__ import __version__


def test_conda_installed():
    result = subprocess.run(["conda"])
    assert result.returncode == 0


def test_expect_installed():
    result = subprocess.run(["expect"])
    assert result.returncode == 0


@pytest.fixture()
def command():
    if not (test_cmd := os.getenv("TEST_ENV")):
        test_cmd = "anaconda" #"python -W ignore -m binstar_client.scripts.cli"
    print(f"Using '{test_cmd}' as an anaconda command.\\nYou may change it by providing TST_CMD=... environment variable.\\n")
    return test_cmd


def test_version(command):
    result = subprocess.run([command, "--version"], capture_output=True, text=True)
    assert result.returncode == 0
    assert f"anaconda Command line client (version {__version__})" in result.stdout
