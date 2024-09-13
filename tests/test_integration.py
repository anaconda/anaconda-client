import os
import shutil
import subprocess
import sys
from pathlib import Path

import pexpect
import pytest
from dotenv import load_dotenv

from binstar_client.__about__ import __version__


load_dotenv()

USERNAME = os.environ["TEST_USERNAME"]
PASSWORD = os.environ["TEST_PASSWORD"]


def login():
    child = pexpect.spawn(["anaconda", "login"])
    child.logfile_read = sys.stdout.buffer

    child.expect('Username:')
    child.sendline(USERNAME)

    child.expect('Password:')
    child.sendline(PASSWORD)

    index = child.expect(
        [
            "Would you like to continue .*:",
            pexpect.EOF,
            pexpect.TIMEOUT,
        ]
    )
    if index == 0:
        child.sendline("Y")
    elif index == 1:
        print("No re-login prompt sent")
    elif index == 2:
        print("Timed out")
    else:
        raise ValueError("This should be unreachable")

    child.expect("login successful")
    child.close()


@pytest.fixture()
def base_dir():
    return Path(__file__).parents[1].resolve()


@pytest.fixture()
def tests_dir():
    return Path(__file__).parent.resolve()


@pytest.fixture()
def data_dir(base_dir):
    return base_dir / "autotest" / "data"


def test_conda_installed():
    result = subprocess.run(["conda"])
    assert result.returncode == 0


def test_expect_installed():
    result = subprocess.run(["expect"])
    assert result.returncode == 0


@pytest.fixture(scope="session")
def command():
    if not (test_cmd := os.getenv("TEST_ENV")):
        test_cmd = "anaconda"
        print(
            f"Using '{test_cmd}' as an anaconda command.\\nYou may change it by providing TST_CMD=... environment variable.\\n"
        )
    return test_cmd


def test_version(command):
    result = subprocess.run([command, "--version"], capture_output=True, text=True)
    assert result.returncode == 0
    assert f"anaconda Command line client (version {__version__})" in result.stdout


def test_config_files(command):
    result = subprocess.run(
        [command, "config", "--files"], capture_output=True, text=True
    )
    assert result.returncode == 0, "Listing of configuration files test failed."


def test_config_show(command):
    result = subprocess.run(
        [command, "config", "--show"], capture_output=True, text=True
    )
    assert result.returncode == 0, "Showing of configuration files test failed."


@pytest.fixture(autouse=True, scope="session")
def logged_in(command):

    # Now that we're authenticated, we can run commands!
    result = subprocess.run(
        [command, "whoami"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0

    not_logged_in = "Anonymous User" in result.stderr
    if not_logged_in:
        program = subprocess.Popen(
            [
                command,
                "login",
                "--username",
                USERNAME,
                "--password",
                PASSWORD,
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Here, we confirm that it's okay that we already have a token
        [out, err] = program.communicate(b"y")

        assert program.returncode == 0


def test_whoami_logged_in(command):
    # Now that we're authenticated, we can run commands!
    result = subprocess.run(
        [command, "whoami"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert f"Username: {USERNAME}" in result.stderr


@pytest.mark.parametrize(
    "package_filename",
    [
        "conda_gc_test-1.2.1-3.tar.bz2",
        "bcj-cffi-0.5.1-py310h295c915_0.tar.bz2",
    ],
)
def test_upload_package(command, data_dir, package_filename):
    # Upload package
    result = subprocess.run(
        [command, "upload", str(data_dir / package_filename), "--force"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "package_name",
    [
        "conda_gc_test",
        "bcj-cffi",
    ],
)
def test_update_packages(command, data_dir, package_name):
    result = subprocess.run(
        [
            command,
            "update",
            f"{USERNAME}/{package_name}",
            str(data_dir / "conda_gc_test_metadata.json"),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


@pytest.fixture()
def tmp_pkg_dir(base_dir):
    p = base_dir / "pkg_tmp"
    (p / "linux-64").mkdir(exist_ok=True, parents=True)
    (p / "linux-aarch64").mkdir(exist_ok=True, parents=True)
    (p / "linux-ppc64le").mkdir(exist_ok=True, parents=True)
    (p / "linux-s390x").mkdir(exist_ok=True, parents=True)
    (p / "osx-64").mkdir(exist_ok=True, parents=True)
    (p / "osx-arm64").mkdir(exist_ok=True, parents=True)
    (p / "win-32").mkdir(exist_ok=True, parents=True)
    (p / "win-64").mkdir(exist_ok=True, parents=True)
    yield p
    shutil.rmtree(p)
    # TODO: There's a bug where this stranded empty directory iscreated in CWD 
    shutil.rmtree(base_dir / "linux-64")
    shutil.rmtree(base_dir / "linux-aarch64")
    shutil.rmtree(base_dir / "linux-ppc64le")
    shutil.rmtree(base_dir / "linux-s390x")
    shutil.rmtree(base_dir / "osx-64")
    shutil.rmtree(base_dir / "osx-arm64")
    shutil.rmtree(base_dir / "win-32")
    shutil.rmtree(base_dir / "win-64")


def test_download_packages(command, tmp_pkg_dir):
    package_names = ["conda_gc_test", "bcj-cffi"]
    for package_name in package_names:
        result = subprocess.run(
            [
                command,
                "download",
                f"{USERNAME}/{package_name}",
                "-o",
                str(tmp_pkg_dir),
            ],
            capture_output=True,
            text=True,
        )

    assert result.returncode == 0, result.stderr

    assert (tmp_pkg_dir / "linux-64" / "conda_gc_test-1.2.1-3.tar.bz2").exists()
    assert (tmp_pkg_dir / "linux-64" / "bcj-cffi-0.5.1-py310h295c915_0.tar.bz2").exists()


@pytest.mark.parametrize(
    "package_name",
    [
        "conda_gc_test",
        "bcj-cffi",
    ],
)
def test_remove_package(command, package_name):
    program = subprocess.Popen(
        [
            command,
            "remove",
            f"mattkram/{package_name}",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Here, we confirm that it's okay that we already have a token
    [out, err] = program.communicate(b"y")

    assert program.returncode == 0


def test_copy_package(command):
    package_names = ["pip/21.2.4", "git-lfs/2.13.3"]
    for package_name in package_names:
        result = subprocess.run(
            [
                command,
                "copy",
                "--from-label",
                "main",
                "--to-label",
                "test",
                f"anaconda/{package_name}",
            ],
            capture_output=True,
            text=True,
        )

    assert result.returncode == 0, result.stderr


def test_move_package(command):
    package_names = ["pip/21.2.4", "git-lfs/2.13.3"]
    for package_name in package_names:
        result = subprocess.run(
            [
                command,
                "move",
                "--from-label",
                "test",
                "--to-label",
                "demo",
                f"{USERNAME}/{package_name}",
            ],
            capture_output=True,
            text=True,
        )

    assert result.returncode == 0, result.stderr




def test_download_copied_packages(command, tmp_pkg_dir):
    package_names = ["pip", "git-lfs"]
    for package_name in package_names:
        result = subprocess.run(
            [
                command,
                "download",
                f"{USERNAME}/{package_name}",
                "-o",
                str(tmp_pkg_dir),
            ],
            capture_output=True,
            text=True,
        )

    assert result.returncode == 0, result.stderr

    files = list((tmp_pkg_dir).glob("*/pip-21.2.4-*.tar.bz2"))
    assert len(files) > 0

    files = list((tmp_pkg_dir).glob("*/git-lfs-2.13.3-*.tar.bz2"))
    assert len(files) > 0


@pytest.mark.parametrize(
    "package_name",
    [
        "pip",
        "git-lfs",
    ],
)
def test_remove_copied_package(command, package_name):
    program = subprocess.Popen(
        [
            command,
            "remove",
            f"{USERNAME}/{package_name}",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Here, we confirm that it's okay that we already have a token
    [out, err] = program.communicate(b"y")

    assert program.returncode == 0


def test_logout(command):
    result = subprocess.run([command, "logout"])
    assert result.returncode == 0
