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
from typer import rich_utils
from typer.testing import CliRunner
import anaconda_cli_base.cli
import binstar_client.plugins
import binstar_client.scripts.cli
from binstar_client import commands
from binstar_client.plugins import ALL_SUBCOMMANDS, NON_HIDDEN_SUBCOMMANDS, DEPRECATED_SUBCOMMANDS, \
    SUBCOMMANDS_WITH_NEW_CLI
from binstar_client.utils import parse_specs

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

    if cmd not in SUBCOMMANDS_WITH_NEW_CLI:
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
    "org_prefix",
    [[], ["org"]],
    ids=["bare", "org"],
)
@pytest.mark.parametrize(
    "prefix_args, args, mods",
    [
        pytest.param([], ["-l", "some-label"], dict(labels=["some-label"]), id="labels-short-single"),
        pytest.param([], ["--label", "some-label"], dict(labels=["some-label"]), id="labels-long-single"),
        pytest.param([], ["-l", "some-label", "-l", "another"], dict(labels=["some-label", "another"]), id="labels-short-multiple"),
        pytest.param([], ["--label", "some-label", "--label", "another"], dict(labels=["some-label", "another"]), id="labels-long-multiple"),
        pytest.param([], ["-c", "some-label", "--channel", "another"], dict(labels=["some-label", "another"]), id="channels-mixed-multiple"),
        pytest.param([], ["--progress"], dict(no_progress=False), id="progress"),
        pytest.param([], ["--no-progress"], dict(no_progress=True), id="no-progress"),
        pytest.param([], ["-u", "username"], dict(user="username"), id="username-short"),
        pytest.param([], ["--user", "username"], dict(user="username"), id="username-long"),
        pytest.param([], ["--keep-basename"], dict(keep_basename=True), id="keep-basename-long"),
        pytest.param([], ["-p", "my_package"], dict(package="my_package"), id="package-short"),
        pytest.param([], ["--package", "my_package"], dict(package="my_package"), id="package-long"),
        pytest.param([], ["--version", "1.2.3"], dict(version="1.2.3"), id="version-long"),
        pytest.param([], ["-v", "1.2.3"], dict(version="1.2.3"), id="version-short"),
        pytest.param([], ["--summary", "Some package summary"], dict(summary="Some package summary"), id="summary-long"),
        pytest.param([], ["-s", "Some package summary"], dict(summary="Some package summary"), id="summary-short"),
        pytest.param([], ["--package-type", "conda"], dict(package_type="conda"), id="package-type-long"),
        pytest.param([], ["-t", "conda"], dict(package_type="conda"), id="package-type-short"),
        pytest.param([], ["--description", "Some package description"], dict(description="Some package description"), id="description-long"),
        pytest.param([], ["-d", "Some package description"], dict(description="Some package description"), id="description-short"),
        pytest.param([], ["--thumbnail", "/path/to/thumbnail"], dict(thumbnail="/path/to/thumbnail"), id="thumbnail-long"),
        pytest.param([], ["--private"], dict(private=True), id="private-long"),
        pytest.param([], ["--register"], dict(auto_register=True), id="register-long"),
        pytest.param([], ["--no-register"], dict(auto_register=False), id="no-register-long"),
        pytest.param([], ["--build-id", "BUILD123"], dict(build_id="BUILD123"), id="build-id-long"),
        pytest.param([], ["-i"], dict(mode="interactive"), id="interactive-short"),
        pytest.param([], ["--interactive"], dict(mode="interactive"), id="interactive-long"),
        pytest.param([], ["-f"], dict(mode="fail"), id="fail-short"),
        pytest.param([], ["--fail"], dict(mode="fail"), id="fail-long"),
        pytest.param([], ["--force"], dict(mode="force"), id="force-long"),
        pytest.param([], ["--skip-existing"], dict(mode="skip"), id="skip-existing-long"),
        pytest.param([], ["-m"], dict(force_metadata_update=True), id="force-metadata-update-short"),
        pytest.param([], ["--force-metadata-update"], dict(force_metadata_update=True), id="force-metadata-update-long"),
        pytest.param(["--token", "TOKEN"], [], dict(token="TOKEN"), id="token"),
        pytest.param(["--site", "site.com"], [], dict(site="site.com"), id="site"),
        pytest.param(["--disable-ssl-warnings"], [], dict(disable_ssl_warnings=True), id="disable-ssl-warnings"),
        pytest.param(["--show-traceback"], [], dict(show_traceback=True), id="show-traceback"),
        pytest.param(["--verbose"], [], dict(log_level=logging.DEBUG), id="verbose-long"),
        pytest.param(["-v"], [], dict(log_level=logging.DEBUG), id="verbose-short"),
        pytest.param(["--quiet"], [], dict(log_level=logging.WARNING), id="quiet-long"),
        pytest.param(["-q"], [], dict(log_level=logging.WARNING), id="quiet-short"),
    ]
)
def test_arg_parsing_upload_command(monkeypatch, mocker, org_prefix, prefix_args, args, mods):
    """Test parsing of the arguments for the upload command. We call `anaconda org upload` both
    with and without the "org" subcommand.

    We check that the main upload function is called with the expected Namespace.

    """
    args = prefix_args + org_prefix + ["upload"] + args + ["some-file"]

    monkeypatch.setattr(sys, "argv", ["/path/to/anaconda"] + args)

    runner = CliRunner()

    mock = mocker.patch("binstar_client.commands.upload.main")
    result = runner.invoke(anaconda_cli_base.cli.app, args)
    assert result.exit_code == 0, result.stdout

    defaults = dict(
        files=["some-file"],
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
        mode=None,
        force_metadata_update=False,
        json_help=None,
    )
    expected = {**defaults, **mods}
    mock.assert_called_once_with(arguments=Namespace(**expected))


@pytest.mark.parametrize(
    "opts, error_opt, conflict_opt",
    [
        pytest.param(
            ["--interactive", "--force"], "'--force'", "'-i' / '--interactive'"
        ),
        pytest.param(
            ["--force", "-i"], "'-i' / '--interactive'", "'--force'"
        ),
        pytest.param(
            ["--fail", "-i"], "'-i' / '--interactive'", "'-f' / '--fail'"
        ),
        pytest.param(
            ["--interactive", "--fail"], "'-f' / '--fail'", "'-i' / '--interactive'"
        ),
        pytest.param(
            ["--force", "--fail"], "'-f' / '--fail'", "'--force'"
        ),
        pytest.param(
            ["--fail", "--force"], "'--force'", "'-f' / '--fail'"
        ),
        pytest.param(
            ["--interactive", "--skip-existing"], "'--skip-existing'", "'-i' / '--interactive'"
        ),
    ]
)
def test_upload_mutually_exclusive_options(monkeypatch, mocker, opts, error_opt, conflict_opt):
    # We need to ensure the terminal is wide enough for long output to stdout
    monkeypatch.setattr(rich_utils, "MAX_WIDTH", 1000)

    mock = mocker.patch("binstar_client.commands.upload.main")

    runner = CliRunner()
    args = ["org", "upload"] + opts + ["./some-file"]
    result = runner.invoke(anaconda_cli_base.cli.app, args, terminal_width=1000)

    assert result.exit_code == 2, result.stdout
    assert f"Invalid value for {error_opt}: mutually exclusive with {conflict_opt}" in result.stdout, result.stdout

    mock.assert_not_called()


@pytest.mark.parametrize(
    "org_prefix",
    [[], ["org"]],
    ids=["bare", "org"],
)
@pytest.mark.parametrize(
    "prefix_args, args, mods",
    [
        pytest.param([], [], dict(), id="defaults"),
        pytest.param([], ["--to-owner", "some-recipient"], dict(to_owner="some-recipient"), id="to-owner"),
        pytest.param([], ["--from-label", "source-label"], dict(from_label="source-label"), id="from-label"),
        pytest.param([], ["--to-label", "destination-label"], dict(to_label="destination-label"), id="to-label"),
        pytest.param([], ["--replace"], dict(replace=True), id="replace"),
        pytest.param([], ["--update"], dict(update=True), id="update"),
        pytest.param(["--token", "TOKEN"], [], dict(token="TOKEN"), id="token"),
        pytest.param(["--site", "site.com"], [], dict(site="site.com"), id="site"),
    ]
)
def test_arg_parsing_copy_command(monkeypatch, mocker, org_prefix, prefix_args, args, mods):
    args = prefix_args + org_prefix + ["copy"] + args + ["some-spec"]

    monkeypatch.setattr(sys, "argv", ["/path/to/anaconda"] + args)

    runner = CliRunner()

    mock = mocker.patch("binstar_client.commands.copy.main")
    result = runner.invoke(anaconda_cli_base.cli.app, args)
    assert result.exit_code == 0, result.stdout

    defaults = dict(
        token=None,
        site=None,
        spec=parse_specs("some-spec"),
        to_owner=None,
        from_label="main",
        to_label="main",
        replace=False,
        update=False,
    )
    expected = {**defaults, **mods}
    mock.assert_called_once_with(args=Namespace(**expected))


@pytest.mark.parametrize(
    "org_prefix",
    [[], ["org"]],
    ids=["bare", "org"],
)
@pytest.mark.parametrize(
    "prefix_args, args, mods",
    [
        pytest.param([], [], dict(), id="defaults"),
        pytest.param([], ["--from-label", "source-label"], dict(from_label="source-label"), id="from-label"),
        pytest.param([], ["--to-label", "destination-label"], dict(to_label="destination-label"), id="to-label"),
        pytest.param(["--token", "TOKEN"], [], dict(token="TOKEN"), id="token"),
        pytest.param(["--site", "site.com"], [], dict(site="site.com"), id="site"),
    ]
)
def test_arg_parsing_move_command(monkeypatch, mocker, org_prefix, prefix_args, args, mods):
    args = prefix_args + org_prefix + ["move"] + args + ["some-spec"]

    monkeypatch.setattr(sys, "argv", ["/path/to/anaconda"] + args)

    runner = CliRunner()

    mock = mocker.patch("binstar_client.commands.move.main")
    result = runner.invoke(anaconda_cli_base.cli.app, args)
    assert result.exit_code == 0, result.stdout

    defaults = dict(
        token=None,
        site=None,
        spec=parse_specs("some-spec"),
        from_label="main",
        to_label="main",
    )
    expected = {**defaults, **mods}
    mock.assert_called_once_with(args=Namespace(**expected))


@pytest.mark.parametrize(
    "org_prefix",
    [[], ["org"]],
    ids=["bare", "org"],
)
@pytest.mark.parametrize(
    "prefix_args, args, mods",
    [
        pytest.param([], [], dict(), id="defaults"),
        pytest.param([], ["--organization", "some-org"], dict(organization="some-org"), id="organization-long"),
        pytest.param([], ["-o", "some-org"], dict(organization="some-org"), id="organization-short"),
        pytest.param([], ["--copy", "source-label", "dest-channel"], dict(copy=("source-label", "dest-channel")), id="copy"),
        pytest.param([], ["--list"], dict(list=True), id="list"),
        pytest.param(["--token", "TOKEN"], [], dict(token="TOKEN"), id="token"),
        pytest.param(["--site", "site.com"], [], dict(site="site.com"), id="site"),
    ]
)
def test_arg_parsing_channel_command(monkeypatch, mocker, org_prefix, prefix_args, args, mods):
    args = prefix_args + org_prefix + ["channel"] + args

    monkeypatch.setattr(sys, "argv", ["/path/to/anaconda"] + args)

    runner = CliRunner()

    mock = mocker.patch("binstar_client.commands.channel.main")
    result = runner.invoke(anaconda_cli_base.cli.app, args)
    assert result.exit_code == 0, result.stdout

    defaults = dict(
        token=None,
        site=None,
        organization=None,
        copy=None,
        list=None,
        show=None,
        lock=None,
        unlock=None,
        remove=None,
    )
    expected = {**defaults, **mods}
    mock.assert_called_once_with(args=Namespace(**expected), name="channel", deprecated=True)
