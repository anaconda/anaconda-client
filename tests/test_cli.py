from importlib import reload
from typing import Generator

import pytest
from pytest import MonkeyPatch
from typer.testing import CliRunner
import anaconda_cli_base.cli
import binstar_client.plugins
from binstar_client.plugins import ALL_SUBCOMMANDS, NON_HIDDEN_SUBCOMMANDS

BASE_COMMANDS = {"login", "logout", "whoami"}
HIDDEN_SUBCOMMANDS = ALL_SUBCOMMANDS - BASE_COMMANDS - NON_HIDDEN_SUBCOMMANDS


@pytest.fixture(autouse=True)
def enable_base_cli_plugin(monkeypatch: MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("ANACONDA_CLI_FORCE_NEW", "1")
    monkeypatch.delenv("ANACONDA_CLIENT_FORCE_STANDALONE", raising=False)
    reload(anaconda_cli_base.cli)
    reload(binstar_client.plugins)
    yield


def test_entrypoint() -> None:
    groups = [g.name for g in anaconda_cli_base.cli.app.registered_groups]
    assert "org" in groups


@pytest.mark.parametrize("cmd", ALL_SUBCOMMANDS)
def test_org_subcommands(cmd: str) -> None:
    org = next((group for group in anaconda_cli_base.cli.app.registered_groups if group.name == "org"), None)
    assert org is not None

    subcmd = next((subcmd for subcmd in org.typer_instance.registered_commands if subcmd.name == cmd), None)
    assert subcmd is not None
    assert subcmd.hidden is False

    runner = CliRunner()
    result = runner.invoke(anaconda_cli_base.cli.app, ["org", cmd, "-h"])
    assert result.exit_code == 0
    assert result.stdout.startswith("usage")


@pytest.mark.parametrize("cmd", HIDDEN_SUBCOMMANDS)
def test_hidden_commands(cmd: str) -> None:
    subcmd = next((subcmd for subcmd in anaconda_cli_base.cli.app.registered_commands if subcmd.name == cmd), None)
    assert subcmd is not None
    assert subcmd.hidden is True
    assert subcmd.help is not None
    assert subcmd.help.startswith("anaconda.org")

    runner = CliRunner()
    result = runner.invoke(anaconda_cli_base.cli.app, [cmd, "-h"])
    assert result.exit_code == 0
    assert result.stdout.startswith("usage")


@pytest.mark.parametrize("cmd", NON_HIDDEN_SUBCOMMANDS)
def test_non_hidden_commands(cmd: str) -> None:
    subcmd = next((subcmd for subcmd in anaconda_cli_base.cli.app.registered_commands if subcmd.name == cmd), None)
    assert subcmd is not None
    assert subcmd.hidden is False
    assert subcmd.help is not None
    assert subcmd.help.startswith("anaconda.org")

    runner = CliRunner()
    result = runner.invoke(anaconda_cli_base.cli.app, [cmd, "-h"])
    assert result.exit_code == 0
    assert result.stdout.startswith("usage")
