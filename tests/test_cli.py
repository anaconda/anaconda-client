"""Test entrypoint to anaconda-cli-base"""
# pylint: disable=redefined-outer-name
import logging
import sys
from argparse import Namespace
from importlib import reload
from socket import gethostname
from typing import Any, Generator, Optional

import pytest
from pytest import LogCaptureFixture
from pytest import MonkeyPatch
from typer import Typer, rich_utils
from typer.testing import CliRunner

import anaconda_cli_base.cli

import binstar_client.plugins
import binstar_client.scripts.cli
from binstar_client import commands
from binstar_client.plugins import (
    ALL_SUBCOMMANDS,
    NON_HIDDEN_SUBCOMMANDS,
    DEPRECATED_SUBCOMMANDS,
    SUBCOMMANDS_WITH_NEW_CLI,
)
from binstar_client.utils.spec import parse_specs, group_spec
from binstar_client.utils.yaml import safe_load

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


@pytest.fixture(
    params=[
        pytest.param(("original", ""), id="orig-bare"),
        pytest.param(("wrapped", ""), id="wrapped-bare"),
        pytest.param(("wrapped", "org"), id="wrapped-prefix"),
        pytest.param(("new", ""), id="new-bare"),
        pytest.param(("new", "org"), id="new-prefix"),
    ]
)
def cli_mocker(request, monkeypatch: MonkeyPatch, mocker) -> Generator[None, None, None]:
    """Fixture returns a function that can be used to invoke the CLI via different methods.

    The different methods are various levels of gradual migration:
        * original: Uses the original argparse-based CLI parsing and direct call of main entrypoint function.
        * wrapped: Uses a common wrapper typer subcommand, that delegates to the main entrypoint function.
        * new: Uses the new typer subcommands if available.

    For the "wrapped" and "new" options, tests will be run both with and without the "org" prefix.

    Usage:
        mock = cli_mocker("path.to.mocked.main")
        mock.invoke(["upload", "some-file"], prefix_args=["--token", "TOKEN"])

    """

    parser, org_prefix = request.param

    if parser == "original":
        monkeypatch.delenv("ANACONDA_CLI_FORCE_NEW", raising=False)
        monkeypatch.setenv("ANACONDA_CLIENT_FORCE_STANDALONE", "true")
        monkeypatch.setenv("ANACONDA_CLI_DISABLE_PLUGINS", "true")
    elif parser == "wrapped":
        monkeypatch.setattr(binstar_client.plugins, "SUBCOMMANDS_WITH_NEW_CLI", set())
        monkeypatch.setenv("ANACONDA_CLI_FORCE_NEW", "true")
        monkeypatch.delenv("ANACONDA_CLIENT_FORCE_STANDALONE", raising=False)
    elif parser == "new":
        monkeypatch.setenv("ANACONDA_CLI_FORCE_NEW", "true")
        monkeypatch.delenv("ANACONDA_CLIENT_FORCE_STANDALONE", raising=False)
    else:
        raise ValueError(f"Incorrect param: {request.param}")

    reload(anaconda_cli_base.cli)
    reload(binstar_client.plugins)

    def f(args, prefix_args = None):
        if org_prefix:
            args = [org_prefix] + args
        if prefix_args:
            args = prefix_args + args

        monkeypatch.setattr(sys, "argv", ["/path/to/anaconda"] + args)
        if parser == "original":
            binstar_client.scripts.cli.main(args, allow_plugin_main=False)
            return Namespace(exit_code=0)
        else:
            runner = CliRunner()
            return runner.invoke(anaconda_cli_base.cli.app, args)

    def closure(main_func: str):
        return MockedCliInvoker(func=f, main_func=main_func, mocker=mocker, parser=parser)

    yield closure

    if isinstance(anaconda_cli_base.cli.app, Typer):
        # Clear out all the groups, commands, and callbacks from the top-level application
        anaconda_cli_base.cli.app.registered_groups.clear()
        anaconda_cli_base.cli.app.registered_commands.clear()
        anaconda_cli_base.cli.app.registered_callback = None


class MockedCliInvoker:
    def __init__(self, func, main_func: str, mocker, parser):
        self._func = func
        self._main_mock = mocker.patch(main_func)
        self._invoked = False
        self.parser = parser

    def invoke(self, args: list[str], prefix_args: Optional[list[str]] = None):
        """Invoke the CLI with a list of arguments.

        The optional prefix_args are passed after the `anaconda` entrypoint.

        """
        result = self._func(args, prefix_args=prefix_args)
        self._invoked = True
        return result

    def assert_main_called_once(self) -> None:
        """Assert that the mocked main function was called once."""
        self._main_mock.assert_called_once()

    def assert_main_args_contains(self, d = None, /, **expected: Any) -> None:
        """Return True if the args passed to the main function is a superset of the kwargs provided."""
        assert self._invoked, "cli_mocker was never invoked"

        # args are either passed positionally, or as kwargs called "args" or "arguments"
        # This extracts the Namespace for all of those cases
        args, call_kwargs = self._main_mock.call_args
        actual = (args[0] if args else None) or call_kwargs.get("args") or call_kwargs.get("arguments")

        expected = {**(d or {}), **expected}

        # Now we can assert that the passed args are a superset of some expected dictionary of values
        assert vars(actual).items() >= expected.items()


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
    "prefix_args, args, mods",
    [
        pytest.param([], [], dict(), id="defaults"),
        pytest.param([], ["first-file"], dict(files=[["first-file"], ["some-file"]]), id="multiple-files"),
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
def test_arg_parsing_upload_command(cli_mocker, prefix_args, args, mods):
    """Test parsing of the arguments for the upload command. We call `anaconda org upload` both
    with and without the "org" subcommand.

    We check that the main upload function is called with the expected Namespace.

    """
    filename = "some-file"
    args = ["upload"] + args + [filename]

    mock = cli_mocker(main_func="binstar_client.commands.upload.main")

    if "--progress" in args and mock.parser == "original":
        return  # Skip because this option isn't handled by argparse

    result = mock.invoke(args, prefix_args=prefix_args)
    assert result.exit_code == 0, result.stdout
    mock.assert_main_called_once()

    defaults = dict(
        files=[[filename]],
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
    mock.assert_main_args_contains(expected)


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
def test_arg_parsing_copy_command(cli_mocker, prefix_args, args, mods):
    args = ["copy"] + args + ["some-spec"]

    mock = cli_mocker(main_func="binstar_client.commands.copy.main")

    result = mock.invoke(args, prefix_args=prefix_args)
    assert result.exit_code == 0, result.stdout
    mock.assert_main_called_once()

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
    mock.assert_main_args_contains(expected)


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
def test_arg_parsing_move_command(cli_mocker, prefix_args, args, mods):
    args = ["move"] + args + ["some-spec"]

    mock = cli_mocker(main_func="binstar_client.commands.move.main")

    result = mock.invoke(args, prefix_args=prefix_args)
    assert result.exit_code == 0, result.stdout
    mock.assert_main_called_once()

    defaults = dict(
        token=None,
        site=None,
        spec=parse_specs("some-spec"),
        from_label="main",
        to_label="main",
    )
    expected = {**defaults, **mods}
    mock.assert_main_args_contains(expected)


@pytest.mark.parametrize(
    "org_prefix",
    [[], ["org"]],
    ids=["bare", "org"],
)
@pytest.mark.parametrize(
    "prefix_args, args, mods",
    [
        pytest.param([], [], dict(), id="defaults"),
        pytest.param([], ["--package-type", "conda"], dict(package_type="conda"), id="package-type-long"),
        pytest.param([], ["-t", "conda"], dict(package_type="conda"), id="package-type-short"),
        pytest.param([], ["--release"], dict(release=True), id="release"),
        pytest.param([], ["--no-release"], dict(release=False), id="no-release"),
        pytest.param(["--token", "TOKEN"], [], dict(token="TOKEN"), id="token"),
        pytest.param(["--site", "my-site.com"], [], dict(site="my-site.com"), id="site"),
    ]
)
def test_arg_parsing_update_command(monkeypatch, mocker, tmp_path, org_prefix, prefix_args, args, mods):
    source_path = str(tmp_path / "metadata.json")
    with open(source_path, "w") as fp:
        fp.write("Hi")

    args = prefix_args + org_prefix + ["update"] + args + ["some-spec", source_path]

    monkeypatch.setattr(sys, "argv", ["/path/to/anaconda"] + args)

    runner = CliRunner()

    mock = mocker.patch("binstar_client.commands.update.main")

    result = runner.invoke(anaconda_cli_base.cli.app, args)
    assert result.exit_code == 0, result.stdout

    defaults = dict(
        token=None,
        site=None,
        spec=parse_specs("some-spec"),
        source=source_path,
        package_type=None,
        release=None,
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
        pytest.param([], ["--package-type", "conda"], dict(package_type="conda"), id="package-type-long"),
        pytest.param([], ["-t", "conda"], dict(package_type="conda"), id="package-type-short"),
        pytest.param([], ["--platform", "osx-64"], dict(platform="osx-64"), id="platform-long"),
        pytest.param([], ["-p", "osx-64"], dict(platform="osx-64"), id="platform-short"),
        pytest.param(["--token", "TOKEN"], [], dict(token="TOKEN"), id="token"),
        pytest.param(["--site", "my-site.com"], [], dict(site="my-site.com"), id="site"),
    ]
)
def test_arg_parsing_search_command(monkeypatch, mocker, org_prefix, prefix_args, args, mods):

    args = prefix_args + org_prefix + ["search"] + args + ["search-term"]

    monkeypatch.setattr(sys, "argv", ["/path/to/anaconda"] + args)

    runner = CliRunner()

    mock = mocker.patch("binstar_client.commands.search.search")

    result = runner.invoke(anaconda_cli_base.cli.app, args)
    assert result.exit_code == 0, result.stdout

    defaults = dict(
        token=None,
        site=None,
        name="search-term",
        package_type=None,
        platform=None,
    )
    expected = {**defaults, **mods}
    mock.assert_called_once_with(args=Namespace(**expected))


@pytest.mark.parametrize(
    "org_prefix",
    [[], ["org"]],
    ids=["bare", "org"],
)
@pytest.mark.parametrize(
    "platform, expected_exit_code",
    [
        ("osx-64", 0),
        ("atari-2600", 2),
    ]
)
def test_arg_parsing_search_command_platform_choice(monkeypatch, mocker, org_prefix, platform, expected_exit_code):

    args = org_prefix + ["search", "--platform", platform, "search-term"]

    monkeypatch.setattr(sys, "argv", ["/path/to/anaconda"] + args)

    runner = CliRunner()

    mocker.patch("binstar_client.commands.search.search")

    result = runner.invoke(anaconda_cli_base.cli.app, args)
    assert result.exit_code == expected_exit_code, result.stdout


@pytest.mark.parametrize(
    "org_prefix",
    [[], ["org"]],
    ids=["bare", "org"],
)
@pytest.mark.parametrize("command_name", ["label", "channel"])
@pytest.mark.parametrize(
    "prefix_args, args, mods",
    [
        pytest.param([], ["--organization", "some-org", "--list"], dict(organization="some-org", list=True), id="organization-long"),
        pytest.param([], ["-o", "some-org", "--list"], dict(organization="some-org", list=True), id="organization-short"),
        pytest.param([], ["--copy", "source-label", "dest-channel"], dict(copy=("source-label", "dest-channel")), id="copy"),
        pytest.param([], ["--list"], dict(list=True), id="list"),
        pytest.param([], ["--show", "label-name"], dict(show="label-name"), id="show"),
        pytest.param([], ["--lock", "label-name"], dict(lock="label-name"), id="lock"),
        pytest.param([], ["--unlock", "label-name"], dict(unlock="label-name"), id="unlock"),
        pytest.param([], ["--remove", "label-name"], dict(remove="label-name"), id="remove"),
        pytest.param(["--token", "TOKEN"], ["--list"], dict(token="TOKEN", list=True), id="token"),
        pytest.param(["--site", "site.com"], ["--list"], dict(site="site.com", list=True), id="site"),
    ]
)
def test_arg_parsing_channel_command(monkeypatch, mocker, org_prefix, command_name, prefix_args, args, mods):
    args = prefix_args + org_prefix + [command_name] + args

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



@pytest.mark.parametrize(
    "opts, error_opt, conflict_opt",
    [
        pytest.param(["--list", "--copy", "from", "to"], "'--copy'", "'--list'"),
        pytest.param(["--list", "--show", "some-label"], "'--show'", "'--list'"),
        pytest.param(["--list", "--lock", "some-label"], "'--lock'", "'--list'"),
        pytest.param(["--list", "--unlock", "some-label"], "'--unlock'", "'--list'"),
        pytest.param(["--list", "--remove", "some-label"], "'--remove'", "'--list'"),
    ]
)
def test_channel_mutually_exclusive_options(monkeypatch, mocker, opts, error_opt, conflict_opt):
    # We need to ensure the terminal is wide enough for long output to stdout
    monkeypatch.setattr(rich_utils, "MAX_WIDTH", 1000)

    mock = mocker.patch("binstar_client.commands.channel.main")

    args = ["org", "channel"] + opts
    monkeypatch.setattr(sys, "argv", ["/path/to/anaconda"] + args)
    runner = CliRunner()
    result = runner.invoke(anaconda_cli_base.cli.app, args)

    assert result.exit_code == 2, result.stdout
    assert f"Invalid value for {error_opt}: mutually exclusive with {conflict_opt}" in result.stdout, result.stdout

    mock.assert_not_called()


def test_channel_mutually_exclusive_options_required(monkeypatch, mocker):
    # We need to ensure the terminal is wide enough for long output to stdout
    monkeypatch.setattr(rich_utils, "MAX_WIDTH", 1000)

    mock = mocker.patch("binstar_client.commands.channel.main")

    args = ["org", "channel"]
    monkeypatch.setattr(sys, "argv", ["/path/to/anaconda"] + args)
    runner = CliRunner()
    result = runner.invoke(anaconda_cli_base.cli.app, args)

    assert result.exit_code == 2, result.stdout
    assert "one of --copy, --list, --show, --lock, --unlock, or --remove must be provided" in result.stdout, result.stdout

    mock.assert_not_called()


@pytest.mark.parametrize(
    "org_prefix",
    [[], ["org"]],
    ids=["bare", "org"],
)
@pytest.mark.parametrize(
    "prefix_args, args, mods",
    [
        pytest.param([], ["add"], dict(action="add"), id="action-add"),
        pytest.param([], ["show"], dict(action="show"), id="action-show"),
        pytest.param([], ["members"], dict(action="members"), id="action-members"),
        pytest.param([], ["add_member"], dict(action="add_member"), id="action-add-member"),
        pytest.param([], ["remove_member"], dict(action="remove_member"), id="action-remove-member"),
        pytest.param([], ["packages"], dict(action="packages"), id="action-packages"),
        pytest.param([], ["add_package"], dict(action="add_package"), id="action-add-package"),
        pytest.param([], ["remove_package"], dict(action="remove_package"), id="action-remove-package"),
        pytest.param([], ["--perms", "read", "add"], dict(perms="read", action="add"), id="perms-read"),
        pytest.param([], ["--perms", "write", "add"], dict(perms="write", action="add"), id="perms-write"),
        pytest.param([], ["--perms", "admin", "add"], dict(perms="admin", action="add"), id="perms-admin"),
        pytest.param(["--token", "TOKEN"], ["add"], dict(token="TOKEN", action="add"), id="token"),
        pytest.param(["--site", "my-site.com"], ["add"], dict(site="my-site.com", action="add"), id="site"),
    ]
)
def test_arg_parsing_groups_command(monkeypatch, mocker, org_prefix, prefix_args, args, mods):

    spec = "my-org/my-group/my-member"
    args = prefix_args + org_prefix + ["groups"] + args + [spec]

    monkeypatch.setattr(sys, "argv", ["/path/to/anaconda"] + args)

    runner = CliRunner()

    mock = mocker.patch("binstar_client.commands.groups.main")

    result = runner.invoke(anaconda_cli_base.cli.app, args)
    assert result.exit_code == 0, result.stdout

    defaults = dict(
        token=None,
        site=None,
        action=None,
        spec=group_spec(spec),
        perms="read",
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
        pytest.param(["--token", "TOKEN"], [], dict(token="TOKEN"), id="token"),
        pytest.param(["--site", "my-site.com"], [], dict(site="my-site.com"), id="site"),
    ]
)
def test_arg_parsing_show_command(monkeypatch, mocker, org_prefix, prefix_args, args, mods):

    spec = "someone/some-package/some-version"
    args = prefix_args + org_prefix + ["show"] + args + [spec]

    monkeypatch.setattr(sys, "argv", ["/path/to/anaconda"] + args)

    runner = CliRunner()

    mock = mocker.patch("binstar_client.commands.show.main")

    result = runner.invoke(anaconda_cli_base.cli.app, args)
    assert result.exit_code == 0, result.stdout

    defaults = dict(
        token=None,
        site=None,
        spec=parse_specs(spec),
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
        pytest.param([], ["--force"], dict(force=True), id="force-long"),
        pytest.param([], ["-f"], dict(force=True), id="force-short"),
        pytest.param(["--token", "TOKEN"], [], dict(token="TOKEN"), id="token"),
        pytest.param(["--site", "my-site.com"], [], dict(site="my-site.com"), id="site"),
    ]
)
def test_arg_parsing_remove_command(monkeypatch, mocker, org_prefix, prefix_args, args, mods):

    spec_1 = "some-user/some-package/some-version/some-file"
    spec_2 = "some-user/some-package/some-version/some-other-file"

    args = prefix_args + org_prefix + ["remove"] + args + [spec_1, spec_2]

    monkeypatch.setattr(sys, "argv", ["/path/to/anaconda"] + args)

    runner = CliRunner()

    mock = mocker.patch("binstar_client.commands.remove.main")

    result = runner.invoke(anaconda_cli_base.cli.app, args)
    assert result.exit_code == 0, result.stdout

    defaults = dict(
        token=None,
        site=None,
        specs=[parse_specs(spec_1), parse_specs(spec_2)],
        force=False
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
        pytest.param([], ["--name", "my-token", "--info"], dict(name="my-token", info=True), id="name-long"),
        pytest.param([], ["-n", "my-token", "--info"], dict(name="my-token", info=True), id="name-short"),
        pytest.param([], ["--organization", "my-org", "--info"], dict(organization="my-org", info=True), id="organization-long"),
        pytest.param([], ["--org", "my-org", "--info"], dict(organization="my-org", info=True), id="organization-mid"),
        pytest.param([], ["-o", "my-org", "--info"], dict(organization="my-org", info=True), id="organization-short"),
        pytest.param([], ["--list-scopes"], dict(list_scopes=True), id="list-scopes-long"),
        pytest.param([], ["-x"], dict(list_scopes=True), id="list-scopes-short"),
        pytest.param([], ["--list"], dict(list=True), id="list-long"),
        pytest.param([], ["-l"], dict(list=True), id="list-short"),
        pytest.param([], ["--create"], dict(create=True), id="create-long"),
        pytest.param([], ["-c"], dict(create=True), id="create-short"),
        pytest.param([], ["--current-info"], dict(info=True), id="info-long"),
        pytest.param([], ["--info"], dict(info=True), id="info-mid"),
        pytest.param([], ["-i"], dict(info=True), id="info-short"),
        pytest.param([], ["--remove", "token-1"], dict(remove=["token-1"]), id="remove-long-single"),
        pytest.param([], ["--remove", "token-1", "--remove", "token-2"], dict(remove=["token-1", "token-2"]), id="remove-long-multiple"),
        pytest.param([], ["-r", "token-1", "-r", "token-2"], dict(remove=["token-1", "token-2"]), id="remove-short-multiple"),
        pytest.param([], ["--create", "--strength", "strong"], dict(create=True, strength="strong"), id="create-strength-strong"),
        pytest.param([], ["--create", "--strength", "weak"], dict(create=True, strength="weak"), id="create-strength-weak"),
        pytest.param([], ["--create", "--strong"], dict(create=True, strength="strong"), id="create-strong"),
        pytest.param([], ["--create", "--weak"], dict(create=True, strength="weak"), id="create-weak-long"),
        pytest.param([], ["--create", "-w"], dict(create=True, strength="weak"), id="create-weak-short"),
        pytest.param([], ["--create", "--url", "some-repo.com"], dict(create=True, url="some-repo.com"), id="url"),
        pytest.param([], ["--create", "--max-age", "3600"], dict(create=True, max_age=3600), id="max-age"),
        pytest.param([], ["--create", "--scopes", "repo"], dict(create=True, scopes=["repo"]), id="scopes-single-long"),
        pytest.param([], ["--create", "--scopes", "repo", "--scopes", "conda:download"], dict(create=True, scopes=["repo", "conda:download"]), id="scopes-multiple-long"),
        pytest.param([], ["--create", "-s", "repo", "-s", "conda:download"], dict(create=True, scopes=["repo", "conda:download"]), id="scopes-multiple-short"),
        pytest.param(["--token", "TOKEN"], ["--info"], dict(token="TOKEN", info=True), id="token"),
        pytest.param(["--site", "my-site.com"], ["--info"], dict(site="my-site.com", info=True), id="site"),
    ]
)
def test_arg_parsing_auth_command(monkeypatch, mocker, org_prefix, prefix_args, args, mods):

    args = prefix_args + org_prefix + ["auth"] + args + []

    monkeypatch.setattr(sys, "argv", ["/path/to/anaconda"] + args)

    runner = CliRunner()

    mock = mocker.patch("binstar_client.commands.authorizations.main")

    result = runner.invoke(anaconda_cli_base.cli.app, args)
    assert result.exit_code == 0, result.stdout

    class NotNone:
        # Just a hack to test the out parameter, which I am not actually testing
        def __eq__(self, other):
            return other is not None

    defaults = dict(
        token=None,
        site=None,
        name=f"anaconda_token:{gethostname()}",
        organization=None,
        list_scopes=False,
        list=False,
        create=False,
        info=False,
        remove=[],
        # Token creation options
        strength="strong",
        url='http://anaconda.org',
        max_age=None,
        scopes=[],
        out=NotNone(),
    )
    expected = {**defaults, **mods}
    mock.assert_called_once_with(args=Namespace(**expected))



@pytest.mark.parametrize(
    "opts, error_opt, conflict_opt",
    [
        pytest.param(["--list-scopes", "--list"], "'-l' / '--list'", "'-x' / '--list-scopes'"),
        pytest.param(["--list-scopes", "--create"], "'-c' / '--create'", "'-x' / '--list-scopes'"),
        pytest.param(["--list-scopes", "--info"], "'-i' / '--info' / '--current-info'", "'-x' / '--list-scopes'"),
        pytest.param(["--list-scopes", "--remove", "token-name"], "'-r' / '--remove'", "'-x' / '--list-scopes'"),
    ]
)
def test_auth_mutually_exclusive_options(monkeypatch, mocker, opts, error_opt, conflict_opt):
    # We need to ensure the terminal is wide enough for long output to stdout
    monkeypatch.setattr(rich_utils, "MAX_WIDTH", 1000)

    mock = mocker.patch("binstar_client.commands.authorizations.main")

    args = ["org", "auth"] + opts
    monkeypatch.setattr(sys, "argv", ["/path/to/anaconda"] + args)
    runner = CliRunner()
    result = runner.invoke(anaconda_cli_base.cli.app, args)

    assert result.exit_code == 2, result.stdout
    assert f"Invalid value for {error_opt}: mutually exclusive with {conflict_opt}" in result.stdout, result.stdout

    mock.assert_not_called()


def test_auth_mutually_exclusive_options_required(monkeypatch, mocker):
    # We need to ensure the terminal is wide enough for long output to stdout
    monkeypatch.setattr(rich_utils, "MAX_WIDTH", 1000)

    mock = mocker.patch("binstar_client.commands.authorizations.main")

    args = ["org", "auth"]
    monkeypatch.setattr(sys, "argv", ["/path/to/anaconda"] + args)
    runner = CliRunner()
    result = runner.invoke(anaconda_cli_base.cli.app, args)

    assert result.exit_code == 2, result.stdout
    assert "one of --list-scopes, --list, --list, --info, or --remove must be provided" in result.stdout, result.stdout

    mock.assert_not_called()


@pytest.mark.parametrize(
    "org_prefix",
    [[], ["org"]],
    ids=["bare", "org"],
)
@pytest.mark.parametrize(
    "prefix_args, args, mods",
    [
        pytest.param([], ["--set", "key", "value"], dict(set=[("key", "value")]), id="set-single"),
        pytest.param([], ["--set", "key", "value", "--set", "key2", "val2"], dict(set=[("key", "value"), ("key2", "val2")]), id="set-multiple"),
        pytest.param([], ["--get", "key"], dict(get="key"), id="get"),
        pytest.param([], ["--remove", "key"], dict(remove=["key"]), id="remove-single"),
        pytest.param([], ["--remove", "key1", "--remove", "key2"], dict(remove=["key1", "key2"]), id="remove-multiple"),
        pytest.param([], ["--show"], dict(show=True), id="show"),
        pytest.param([], ["--files"], dict(files=True), id="files"),
        pytest.param([], ["--show-sources"], dict(show_sources=True), id="show-sources"),
        pytest.param([], ["--user"], dict(user=True), id="user-long"),
        pytest.param([], ["-u"], dict(user=True), id="user-short"),
        pytest.param([], ["--system"], dict(user=False), id="system-long"),
        pytest.param([], ["-s"], dict(user=False), id="system-short"),
        pytest.param([], ["--site"], dict(user=False), id="site"),
        pytest.param(["--token", "TOKEN"], ["--type", "int"], dict(token="TOKEN", type=int), id="token"),
        pytest.param(["--site", "my-site.com"], ["--type", "int"], dict(site="my-site.com", type=int), id="site"),
    ]
)
def test_arg_parsing_config_command(monkeypatch, mocker, org_prefix, prefix_args, args, mods):

    args = prefix_args + org_prefix + ["config"] + args + []

    monkeypatch.setattr(sys, "argv", ["/path/to/anaconda"] + args)

    runner = CliRunner()

    mock = mocker.patch("binstar_client.commands.config.main")

    result = runner.invoke(anaconda_cli_base.cli.app, args)
    assert result.exit_code == 0, result.stdout

    defaults = dict(
        token=None,
        site=None,
        type=safe_load,
        set=[],
        get=None,
        remove=[],
        show=False,
        files=False,
        show_sources=False,
        user=True,
    )
    expected = {**defaults, **mods}
    mock.assert_called_once_with(args=Namespace(**expected))


@pytest.mark.parametrize(
    "prefix_args, args, mods",
    [
        pytest.param([], ["--add-collaborator", "jim"], dict(add_collaborator="jim"), id="add-collaborator"),
        pytest.param([], ["--list-collaborators"], dict(list_collaborators=True), id="list-collaborators"),
        pytest.param([], ["--create"], dict(create=True), id="create"),
        pytest.param([], ["--summary", "SUMMARY", "--create"], dict(summary="SUMMARY", create=True), id="summary"),
        pytest.param([], ["--license", "MIT", "--create"], dict(license="MIT", create=True), id="license"),
        pytest.param([], ["--license-url", "license.com", "--create"], dict(license_url="license.com", create=True), id="license-url"),
        pytest.param([], ["--personal", "--create"], dict(access="personal", create=True), id="personal"),
        pytest.param([], ["--private", "--create"], dict(access="private", create=True), id="private"),
        pytest.param(["--token", "TOKEN"], ["--create"], dict(token="TOKEN", create=True), id="token"),
        pytest.param(["--site", "my-site.com"], ["--create"], dict(site="my-site.com", create=True), id="site"),
    ]
)
def test_arg_parsing_package_command(cli_mocker, prefix_args, args, mods):
    spec = "user/package"
    args = ["package"] + args + [spec]

    mock = cli_mocker(main_func="binstar_client.commands.package.main")
    result = mock.invoke(args, prefix_args=prefix_args)
    assert result.exit_code == 0, result.stdout
    mock.assert_main_called_once()

    defaults = dict(
        token=None,
        site=None,
        spec=parse_specs(spec),
        add_collaborator=None,
        list_collaborators=False,
        create=False,
        summary=None,
        license=None,
        license_url=None,
        access=None,
    )
    expected = {**defaults, **mods}
    mock.assert_main_args_contains(expected)


@pytest.mark.parametrize(
    "opts, error_opt, conflict_opt",
    [
        pytest.param(["--add-collaborator", "joe", "--list-collaborators"], "'--list-collaborators'", "'--add-collaborator'"),
        pytest.param(["--add-collaborator", "joe", "--create"], "'--create'", "'--add-collaborator'"),
    ]
)
def test_package_mutually_exclusive_options(monkeypatch, mocker, opts, error_opt, conflict_opt):
    # We need to ensure the terminal is wide enough for long output to stdout
    monkeypatch.setattr(rich_utils, "MAX_WIDTH", 1000)

    mock = mocker.patch("binstar_client.commands.package.main")

    args = ["org", "package"] + opts + ["spec"]
    monkeypatch.setattr(sys, "argv", ["/path/to/anaconda"] + args)
    runner = CliRunner()
    result = runner.invoke(anaconda_cli_base.cli.app, args)

    assert result.exit_code == 2, result.stdout
    assert f"Invalid value for {error_opt}: mutually exclusive with {conflict_opt}" in result.stdout, result.stdout

    mock.assert_not_called()


def test_package_mutually_exclusive_options_required(monkeypatch, mocker):
    # We need to ensure the terminal is wide enough for long output to stdout
    monkeypatch.setattr(rich_utils, "MAX_WIDTH", 1000)

    mock = mocker.patch("binstar_client.commands.package.main")

    args = ["org", "package", "spec"]
    monkeypatch.setattr(sys, "argv", ["/path/to/anaconda"] + args)
    runner = CliRunner()
    result = runner.invoke(anaconda_cli_base.cli.app, args)

    assert result.exit_code == 2, result.stdout
    assert "one of --add-collaborator, --list-collaborators, or --create must be provided" in result.stdout, result.stdout

    mock.assert_not_called()
