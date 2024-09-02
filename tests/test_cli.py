"""Test entrypoint to anaconda-cli-base"""
# pylint: disable=redefined-outer-name
import sys
from argparse import Namespace
from importlib import reload
import logging
from typing import Any, Generator

import pytest
from pytest import LogCaptureFixture
from pytest import MonkeyPatch
from typer.testing import CliRunner
import anaconda_cli_base.cli
import binstar_client.plugins
import binstar_client.scripts.cli
from binstar_client import commands
from binstar_client.plugins import ALL_SUBCOMMANDS, NON_HIDDEN_SUBCOMMANDS, DEPRECATED_SUBCOMMANDS, \
    SUBCOMMANDS_WITH_NEW_CLI

BASE_COMMANDS = {"login", "logout", "whoami"}
HIDDEN_SUBCOMMANDS = ALL_SUBCOMMANDS - BASE_COMMANDS - NON_HIDDEN_SUBCOMMANDS


@pytest.fixture(autouse=True)
def enable_base_cli_plugin(monkeypatch: MonkeyPatch) -> Generator[None, None, None]:
    """Make sure that we get a clean app with plugins loaded"""

    monkeypatch.setenv("ANACONDA_CLI_FORCE_NEW", "1")
    monkeypatch.delenv("ANACONDA_CLIENT_FORCE_STANDALONE", raising=False)
    reload(anaconda_cli_base.cli)
    reload(binstar_client.plugins)
    yield


def test_entrypoint() -> None:
    """Has the entrypoint been loaded?"""

    groups = [grp.name for grp in anaconda_cli_base.cli.app.registered_groups]
    assert "org" in groups


@pytest.fixture()
def assert_binstar_args(mocker):
    """
    Returns a closure that can be used to assert that binstar_main was called with a specific list of args.
    """
    mock = mocker.spy(binstar_client.scripts.cli, "binstar_main")

    def check_args(args):
        mock.assert_called_once_with(commands, args, True)

    return check_args


@pytest.mark.parametrize("cmd", sorted(ALL_SUBCOMMANDS))
def test_org_subcommands(cmd: str, monkeypatch: MonkeyPatch, assert_binstar_args: Any) -> None:
    """anaconda org <cmd>"""

    args = ["org", cmd, "-h"]
    monkeypatch.setattr(sys, "argv", ["/path/to/anaconda"] + args)

    org = next((group for group in anaconda_cli_base.cli.app.registered_groups if group.name == "org"), None)
    assert org is not None

    assert org.typer_instance
    subcmd = next((subcmd for subcmd in org.typer_instance.registered_commands if subcmd.name == cmd), None)
    assert subcmd is not None
    assert subcmd.hidden is False

    runner = CliRunner()
    result = runner.invoke(anaconda_cli_base.cli.app, args)
    assert result.exit_code == 0
    assert "usage:" in result.stdout.lower()

    if cmd not in SUBCOMMANDS_WITH_NEW_CLI:
        assert_binstar_args([cmd, "-h"])


@pytest.mark.parametrize("cmd", list(HIDDEN_SUBCOMMANDS))
def test_hidden_commands(cmd: str, monkeypatch: MonkeyPatch, assert_binstar_args: Any) -> None:
    """anaconda <cmd>"""

    args = [cmd, "-h"]
    monkeypatch.setattr(sys, "argv", ["/path/to/anaconda"] + args)

    subcmd = next((subcmd for subcmd in anaconda_cli_base.cli.app.registered_commands if subcmd.name == cmd), None)
    assert subcmd is not None
    assert subcmd.hidden is True
    assert subcmd.help is not None
    assert subcmd.help.startswith("anaconda.org")

    runner = CliRunner()
    result = runner.invoke(anaconda_cli_base.cli.app, args)
    assert result.exit_code == 0, result.stdout
    assert "usage:" in result.stdout.lower()

    assert_binstar_args([cmd, "-h"])


@pytest.mark.parametrize("cmd", list(NON_HIDDEN_SUBCOMMANDS))
def test_non_hidden_commands(cmd: str, monkeypatch: MonkeyPatch, assert_binstar_args: Any) -> None:
    """anaconda login"""

    args = [cmd, "-h"]
    monkeypatch.setattr(sys, "argv", ["/path/to/anaconda"] + args)

    subcmd = next((subcmd for subcmd in anaconda_cli_base.cli.app.registered_commands if subcmd.name == cmd), None)
    assert subcmd is not None
    assert subcmd.hidden is False
    assert subcmd.help is not None
    assert subcmd.help.startswith("anaconda.org")

    runner = CliRunner()
    result = runner.invoke(anaconda_cli_base.cli.app, args)
    assert result.exit_code == 0
    assert "usage:" in result.stdout.lower()

    if cmd not in SUBCOMMANDS_WITH_NEW_CLI:
        assert_binstar_args([cmd, "-h"])


@pytest.mark.parametrize("cmd", list(DEPRECATED_SUBCOMMANDS))
def test_deprecated_message(
        cmd: str, caplog: LogCaptureFixture, monkeypatch: MonkeyPatch, assert_binstar_args: Any
) -> None:
    """anaconda <cmd> warning"""

    args = [cmd, "-h"]
    monkeypatch.setattr(sys, "argv", ["/path/to/anaconda"] + args)

    with caplog.at_level(logging.WARNING):
        runner = CliRunner()
        result = runner.invoke(anaconda_cli_base.cli.app, args)
        assert result.exit_code == 0
        assert "commands will be deprecated" in caplog.records[0].msg

    assert_binstar_args([cmd, "-h"])


@pytest.mark.parametrize("cmd", list(NON_HIDDEN_SUBCOMMANDS))
def test_top_level_options_passed_through(cmd: str, monkeypatch: MonkeyPatch, assert_binstar_args: Any) -> None:
    """Ensure top-level CLI options are passed through to binstar_main."""

    args = ["-t", "TOKEN", "-s", "some-site.com", cmd, "-h"]
    monkeypatch.setattr(sys, "argv", ["/path/to/anaconda"] + args)

    runner = CliRunner()
    result = runner.invoke(anaconda_cli_base.cli.app, args)
    assert result.exit_code == 0
    assert "usage:" in result.stdout.lower()

    if cmd not in SUBCOMMANDS_WITH_NEW_CLI:
        assert_binstar_args(["-t", "TOKEN", "-s", "some-site.com", cmd, "-h"])


@pytest.mark.parametrize(
    "args, mods",
    [
        pytest.param([], {}, id="defaults"),
        pytest.param(["-i"], dict(interactive=True), id="interactive-short"),
        pytest.param(["--interactive"], dict(interactive=True), id="interactive-long"),
        pytest.param(["-l", "some-label"], dict(labels=["some-label"]), id="labels-short-single"),
        pytest.param(["--label", "some-label"], dict(labels=["some-label"]), id="labels-long-single"),
        pytest.param(["-l", "some-label", "-l", "another"], dict(labels=["some-label", "another"]), id="labels-short-multiple"),
        pytest.param(["--label", "some-label", "--label", "another"], dict(labels=["some-label", "another"]), id="labels-long-multiple"),
        pytest.param(["-c", "some-label", "--channel", "another"], dict(labels=["some-label", "another"]), id="channels-mixed-multiple"),
        pytest.param(["--progress"], dict(no_progress=False), id="progress"),
        pytest.param(["--no-progress"], dict(no_progress=True), id="no-progress"),
        pytest.param(["-u", "username"], dict(user="username"), id="username-short"),
        pytest.param(["--user", "username"], dict(user="username"), id="username-long"),
    ]
)
def test_arg_parsing_upload_command(monkeypatch, mocker, args, mods):
    args = ["org", "upload"] + args

    monkeypatch.setattr(sys, "argv", ["/path/to/anaconda"] + args)

    runner = CliRunner()

    mock = mocker.patch("binstar_client.commands.upload.main")
    result = runner.invoke(anaconda_cli_base.cli.app, args)
    assert result.exit_code == 0, result.stdout

    defaults = dict(
        files=[],
        interactive=False,
        token=None,
        disable_ssl_warnings=False,
        show_traceback=False,
        log_level=20,
        site=None,
        labels=[],
        no_progress=False,
        user=None,
        keep_basename=False,
        package=None,
        version=None,
        summary=None,
        package_type=None,
        description=None,
        thumbnail=None,
        private=False,
        auto_register=True,
        build_id=None,
        mode='interactive',
        force_metadata_update=False,
        json_help=None,
    )
    expected = {**defaults, **mods}
    mock.assert_called_once_with(arguments=Namespace(**expected))
