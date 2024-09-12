import os
import shutil
import subprocess
from pathlib import Path

import pytest
from dotenv import load_dotenv

from binstar_client.__about__ import __version__


load_dotenv()


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
    username = os.environ["TEST_USERNAME"]
    password = os.environ["TEST_PASSWORD"]

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


def test_whoami_logged_in(command):
    username = "mattkram"

    # Now that we're authenticated, we can run commands!
    result = subprocess.run(
        [command, "whoami"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert f"Username: {username}" in result.stderr


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
    username = "mattkram"
    result = subprocess.run(
        [
            command,
            "update",
            f"{username}/{package_name}",
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
    yield p
    shutil.rmtree(p)
    # TODO: There's a bug where this stranded empty directory iscreated in CWD 
    shutil.rmtree(p / "linux-64")


def test_download_packages(command, tmp_pkg_dir):
    username = "mattkram"
    package_names = ["conda_gc_test", "bcj-cffi"]
    for package_name in package_names:
        result = subprocess.run(
            [
                command,
                "download",
                f"{username}/{package_name}",
                "-o",
                str(tmp_pkg_dir),
            ],
            capture_output=True,
            text=True,
        )

    assert result.returncode == 0, result.stderr

    assert (tmp_pkg_dir / "linux-64" / "conda_gc_test-1.2.1-3.tar.bz2").exists()
    assert (tmp_pkg_dir / "linux-64" / "bcj-cffi-0.5.1-py310h295c915_0.tar.bz2").exists()
    """
    # Remove package:\\n"
    echo -e "spawn ${TST_CMD} remove \"${TST_LOGIN}/conda_gc_test\"\\nexpect {\\n  \"Are you sure you want to remove the package \" {\\n    send -- \"y\\\\r\"\\n  }\\n  timeout {\\n    send_user \"\\\\n\\\\nUnexpected application state.\\\\n\"\\n    exit 67\\n  }\\n  eof {\\n    send_user \"\\\\n\\\\nUnexpected application state.\\\\n\"\\n    exit 67\\n  }\\n}\\nexpect {\\n  timeout {\\n    send_user \"\\\\n\\\\nUnexpected application state.\\\\n\"\\n    exit 67\\n  }\\n  eof {\\n    exit 0\\n  }\\n}\\n" | expect || (echo -e "\\n\\n/!\\\\ Remove package test failed.\\n" && exit 1)
    echo

    echo -e "spawn ${TST_CMD} remove \"${TST_LOGIN}/bcj-cffi\"\\nexpect {\\n  \"Are you sure you want to remove the package \" {\\n    send -- \"y\\\\r\"\\n  }\\n  timeout {\\n    send_user \"\\\\n\\\\nUnexpected application state.\\\\n\"\\n    exit 67\\n  }\\n  eof {\\n    send_user \"\\\\n\\\\nUnexpected application state.\\\\n\"\\n    exit 67\\n  }\\n}\\nexpect {\\n  timeout {\\n    send_user \"\\\\n\\\\nUnexpected application state.\\\\n\"\\n    exit 67\\n  }\\n  eof {\\n    exit 0\\n  }\\n}\\n" | expect || (echo -e "\\n\\n/!\\\\ Remove package test failed.\\n" && exit 1)
    echo

    # Upload notebook:\\n"
    ${TST_CMD} upload ./data/hello_binstar.ipynb || (echo -e "\\n\\n/!\\\\ Upload notebook test failed.\\n" && exit 1)
    echo

    # Download notebook:\\n"
    rm -rf nbk_tmp
    mkdir -p nbk_tmp
    ${TST_CMD} download "${TST_LOGIN}/hello_binstar" -o nbk_tmp || (echo -e "\\n\\n/!\\\\ Download notebook test failed.\\n" && exit 1)
    [ $(find nbk_tmp -name hello_binstar.ipynb | wc -l) = 1 ] || (echo -e "\\n\\n/!\\\\ Download notebook test failed.\\n" && exit 1)
    rm -rf nbk_tmp
    echo

    # Remove notebook:\\n"
    echo -e "spawn ${TST_CMD} remove \"${TST_LOGIN}/hello_binstar\"\\nexpect {\\n  \"Are you sure you want to remove the package \" {\\n    send -- \"y\\\\r\"\\n  }\\n  timeout {\\n    send_user \"\\\\n\\\\nUnexpected application state.\\\\n\"\\n    exit 67\\n  }\\n  eof {\\n    send_user \"\\\\n\\\\nUnexpected application state.\\\\n\"\\n    exit 67\\n  }\\n}\\nexpect {\\n  timeout {\\n    send_user \"\\\\n\\\\nUnexpected application state.\\\\n\"\\n    exit 67\\n  }\\n  eof {\\n    exit 0\\n  }\\n}\\n" | expect || (echo -e "\\n\\n/!\\\\ Remove notebook test failed.\\n" && exit 1)
    echo

    # Upload environment:\\n"
    ${TST_CMD} upload ./data/test_env.yml || (echo -e "\\n\\n/!\\\\ Upload environment test failed.\\n" && exit 1)
    echo

    # Download environment:\\n"
    rm -rf env_tmp
    mkdir -p env_tmp
    ${TST_CMD} download "${TST_LOGIN}/test_env" -o env_tmp || (echo -e "\\n\\n/!\\\\ Download environment test failed.\\n" && exit 1)
    [ $(find env_tmp -name test_env.yml | wc -l) = 1 ] || (echo -e "\\n\\n/!\\\\ Download environment test failed.\\n" && exit 1)
    rm -rf env_tmp
    echo

    # Remove environment:\\n"
    echo -e "spawn ${TST_CMD} remove \"${TST_LOGIN}/test_env\"\\nexpect {\\n  \"Are you sure you want to remove the package \" {\\n    send -- \"y\\\\r\"\\n  }\\n  timeout {\\n    send_user \"\\\\n\\\\nUnexpected application state.\\\\n\"\\n    exit 67\\n  }\\n  eof {\\n    send_user \"\\\\n\\\\nUnexpected application state.\\\\n\"\\n    exit 67\\n  }\\n}\\nexpect {\\n  timeout {\\n    send_user \"\\\\n\\\\nUnexpected application state.\\\\n\"\\n    exit 67\\n  }\\n  eof {\\n    exit 0\\n  }\\n}\\n" | expect || (echo -e "\\n\\n/!\\\\ Remove environment test failed.\\n" && exit 1)
    echo

    # Copy package:\\n"
    ${TST_CMD} copy --from-label main --to-label test anaconda/pip/21.2.4 || (echo -e "\\n\\n/!\\\\ Copy package test failed.\\n" && exit 1)
    echo

    ${TST_CMD} copy --from-label main --to-label test anaconda/git-lfs/2.13.3 || (echo -e "\\n\\n/!\\\\ Copy package test failed.\\n" && exit 1)
    echo

    # Move package:\\n"
    ${TST_CMD} move --from-label test --to-label demo "${TST_LOGIN}/pip/21.2.4" || (echo -e "\\n\\n/!\\\\ Move package test failed.\\n" && exit 1)
    echo

    ${TST_CMD} move --from-label test --to-label demo "${TST_LOGIN}/git-lfs/2.13.3" || (echo -e "\\n\\n/!\\\\ Move package test failed.\\n" && exit 1)
    echo

    # Download copied package:\\n"
    rm -rf pkg_tmp
    mkdir -p pkg_tmp/linux-32 pkg_tmp/linux-64 pkg_tmp/linux-aarch64 pkg_tmp/linux-ppc64le pkg_tmp/linux-s390x pkg_tmp/noarch pkg_tmp/osx-64 pkg_tmp/osx-arm64 pkg_tmp/win-32 pkg_tmp/win-64
    ${TST_CMD} download "${TST_LOGIN}/pip" -o pkg_tmp || (echo -e "\\n\\n/!\\\\ Download copied package test failed.\\n" && exit 1)
    [ $(find pkg_tmp -name 'pip-21.2.4-*.tar.bz2' | wc -l) ">" 0 ] || (echo -e "\\n\\n/!\\\\ Download copied package test failed.\\n" && exit 1)
    rm -rf pkg_tmp
    echo

    rm -rf pkg_tmp
    mkdir -p pkg_tmp/linux-32 pkg_tmp/linux-64 pkg_tmp/linux-aarch64 pkg_tmp/linux-ppc64le pkg_tmp/linux-s390x pkg_tmp/noarch pkg_tmp/osx-64 pkg_tmp/osx-arm64 pkg_tmp/win-32 pkg_tmp/win-64
    ${TST_CMD} download "${TST_LOGIN}/git-lfs" -o pkg_tmp || (echo -e "\\n\\n/!\\\\ Download copied package test failed.\\n" && exit 1)
    [ $(find pkg_tmp -name 'git-lfs-2.13.3-*.tar.bz2' | wc -l) ">" 0 ] || (echo -e "\\n\\n/!\\\\ Download copied package test failed.\\n" && exit 1)
    rm -rf pkg_tmp
    echo

    # Remove copied package:\\n"
    echo -e "spawn ${TST_CMD} remove ${TST_LOGIN}/pip\\nexpect {\\n  \"Are you sure you want to remove the package \" {\\n    send -- \"y\\\\r\"\\n  }\\n  timeout {\\n    send_user \"\\\\n\\\\nUnexpected application state.\\\\n\"\\n    exit 67\\n  }\\n  eof {\\n    send_user \"\\\\n\\\\nUnexpected application state.\\\\n\"\\n    exit 67\\n  }\\n}\\nexpect {\\n  timeout {\\n    send_user \"\\\\n\\\\nUnexpected application state.\\\\n\"\\n    exit 67\\n  }\\n  eof {\\n    exit 0\\n  }\\n}\\n" | expect || (echo -e "\\n\\n/!\\\\ Remove copied package test failed.\\n" && exit 1)
    echo

    echo -e "spawn ${TST_CMD} remove ${TST_LOGIN}/git-lfs\\nexpect {\\n  \"Are you sure you want to remove the package \" {\\n    send -- \"y\\\\r\"\\n  }\\n  timeout {\\n    send_user \"\\\\n\\\\nUnexpected application state.\\\\n\"\\n    exit 67\\n  }\\n  eof {\\n    send_user \"\\\\n\\\\nUnexpected application state.\\\\n\"\\n    exit 67\\n  }\\n}\\nexpect {\\n  timeout {\\n    send_user \"\\\\n\\\\nUnexpected application state.\\\\n\"\\n    exit 67\\n  }\\n  eof {\\n    exit 0\\n  }\\n}\\n" | expect || (echo -e "\\n\\n/!\\\\ Remove copied package test failed.\\n" && exit 1)
    echo

    # Logout:\\n"
    ${TST_CMD} logout || (echo -e "\\n\\n/!\\\\ Logout test failed.\\n" && exit 1)
    echo

    echo -e "/?\\\\ Success!\\n\\nAll tests have passed!\\n"

    rm -rf ./linux-32 ./linux-64 ./linux-aarch64 ./linux-ppc64le ./linux-s390x ./noarch ./osx-64 ./osx-arm64 ./win-32 ./win-64

        """
