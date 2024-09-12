import os
import subprocess

import pytest
from dotenv import load_dotenv

from binstar_client.__about__ import __version__


load_dotenv()


def test_conda_installed():
    result = subprocess.run(["conda"])
    assert result.returncode == 0


def test_expect_installed():
    result = subprocess.run(["expect"])
    assert result.returncode == 0


@pytest.fixture()
def command():
    if not (test_cmd := os.getenv("TEST_ENV")):
        test_cmd = "anaconda"
        print(f"Using '{test_cmd}' as an anaconda command.\\nYou may change it by providing TST_CMD=... environment variable.\\n")
    return test_cmd


def test_version(command):
    result = subprocess.run([command, "--version"], capture_output=True, text=True)
    assert result.returncode == 0
    assert f"anaconda Command line client (version {__version__})" in result.stdout


def test_config_files(command):
    result = subprocess.run([command, "config", "--files"], capture_output=True, text=True)
    assert result.returncode == 0, "Listing of configuration files test failed."


def test_config_show(command):
    result = subprocess.run([command, "config", "--show"], capture_output=True, text=True)
    assert result.returncode == 0, "Showing of configuration files test failed."


def test_login(command):
    username = os.environ["TEST_USERNAME"]
    password = os.environ["TEST_PASSWORD"]

    program = subprocess.Popen(
        [
            command,
            "login",
            "--username",
            username,
            "--password",
            password,
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Here, we confirm that it's okay that we already have a token
    [out, err] = program.communicate(b"y")

    assert program.returncode == 0

    # Now that we're authenticated, we can run commands!
    result = subprocess.run(
        [command, "whoami"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert f"Username: {username}" in result.stderr
