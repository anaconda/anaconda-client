"""Test entrypoint to anaconda-cli-base"""
# pylint: disable=line-too-long
# pylint: disable=redefined-outer-name
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=use-dict-literal

import sys
import logging
from argparse import Namespace
from importlib import reload
from typing import Any, Callable, Dict, Generator, List, Optional

import pytest
from pytest import FixtureRequest
from pytest import LogCaptureFixture
from pytest import MonkeyPatch
from typer import Typer
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


class MockedCliInvoker:
    def __init__(self, func: Callable, main_func: str, mocker: Any, parser: Any):
        self._func = func
        self._main_mock = mocker.patch(main_func)
        self._invoked = False
        self.parser = parser

    def invoke(self, args: List[str], prefix_args: Optional[List[str]] = None) -> Any:
        """Invoke the CLI with a list of arguments.

        The optional prefix_args are passed after the `anaconda` entrypoint.

        """
        result = self._func(args, prefix_args=prefix_args)
        self._invoked = True
        return result

    def assert_main_called_once(self) -> None:
        """Assert that the mocked main function was called once."""
        self._main_mock.assert_called_once()

    def assert_main_args_contains(self, expected: Dict) -> None:
        """Return True if the args passed to the main function is a superset of the kwargs provided."""
        assert self._invoked, "cli_mocker was never invoked"

        # This extracts the Namespace for all of those cases
        args, _ = self._main_mock.call_args
        namespace = args[0]
        actual = vars(namespace)

        # Now we can assert that the passed args are a superset of some expected dictionary of values
        assert actual.items() >= expected.items()


InvokerFactory = Callable[[str], MockedCliInvoker]


@pytest.fixture(
    params=[
        pytest.param(("original", ""), id="orig-bare"),
        pytest.param(("wrapped", ""), id="wrapped-bare"),
        pytest.param(("wrapped", "org"), id="wrapped-prefix"),
        pytest.param(("new", ""), id="new-bare"),
        pytest.param(("new", "org"), id="new-prefix"),
    ]
)
def cli_mocker(
    request: FixtureRequest,
    monkeypatch: MonkeyPatch,
    mocker: Any,
) -> Generator[InvokerFactory, None, None]:
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

    def func(args, prefix_args=None):
        if org_prefix:
            args = [org_prefix] + args
        if prefix_args:
            args = prefix_args + args

        monkeypatch.setattr(sys, "argv", ["/path/to/anaconda"] + args)
        if parser == "original":
            binstar_client.scripts.cli.main(args, allow_plugin_main=False)
            return Namespace(exit_code=0)
        runner = CliRunner()
        return runner.invoke(anaconda_cli_base.cli.app, args)

    def closure(main_func: str) -> MockedCliInvoker:
        return MockedCliInvoker(func=func, main_func=main_func, mocker=mocker, parser=parser)

    yield closure

    if isinstance(anaconda_cli_base.cli.app, Typer):
        # Clear out all the groups, commands, and callbacks from the top-level application
        anaconda_cli_base.cli.app.registered_groups.clear()
        anaconda_cli_base.cli.app.registered_commands.clear()
        anaconda_cli_base.cli.app.registered_callback = None


def test_entrypoint() -> None:
    """Has the entrypoint been loaded?"""

    groups = [grp.name for grp in anaconda_cli_base.cli.app.registered_groups]
    assert "org" in groups


@pytest.mark.parametrize("flag", ["--help", "-h"])
def test_org_subcommand_help(flag: str) -> None:
    """anaconda org -h and anaconda --help are both available"""

    runner = CliRunner()
    result = runner.invoke(anaconda_cli_base.cli.app, ["org", flag])
    assert result.exit_code == 0


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

    runner = CliRunner()
    result = runner.invoke(anaconda_cli_base.cli.app, args)
    assert result.exit_code == 0
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

    args = ["-t", "TOKEN", "-s", "some-site.com", cmd, "-h"]  # nosec
    monkeypatch.setattr(sys, "argv", ["/path/to/anaconda"] + args)

    runner = CliRunner()
    result = runner.invoke(anaconda_cli_base.cli.app, args)
    assert result.exit_code == 0
    assert "usage:" in result.stdout.lower()

    if cmd not in SUBCOMMANDS_WITH_NEW_CLI:
        assert_binstar_args(["-t", "TOKEN", "-s", "some-site.com", cmd, "-h"])  # nosec


@pytest.mark.parametrize(
    "prefix_args, args, mods",
    [
        pytest.param([], [], dict(), id="defaults"),
        pytest.param(["--token", "TOKEN"], [], dict(token="TOKEN"), id="token"),  # nosec
        pytest.param(["--site", "my-site.com"], [], dict(site="my-site.com"), id="site"),
    ]
)
def test_whoami_arg_parsing(
    prefix_args: List[str], args: List[str], mods: Dict[str, Any], cli_mocker: InvokerFactory
) -> None:
    args = ["whoami"] + args
    defaults = dict(
        token=None,
        site=None,
    )
    expected = {**defaults, **mods}

    mock = cli_mocker("binstar_client.commands.whoami.main")
    result = mock.invoke(args, prefix_args=prefix_args)
    assert result.exit_code == 0, result.stdout
    mock.assert_main_called_once()
    mock.assert_main_args_contains(expected)


@pytest.mark.parametrize(
    "prefix_args, args, mods",
    [
        pytest.param([], [], dict(), id="defaults"),
        pytest.param([], ["-l", "some-label"], dict(labels=["some-label"]), id="labels-short-single"),
        pytest.param([], ["--label", "some-label"], dict(labels=["some-label"]), id="labels-long-single"),
        pytest.param([], ["-l", "some-label", "-l", "another"], dict(labels=["some-label", "another"]), id="labels-short-multiple"),  # noqa: E501
        pytest.param([], ["--label", "some-label", "--label", "another"], dict(labels=["some-label", "another"]), id="labels-long-multiple"),  # noqa: E501
        pytest.param([], ["-l", "some-label", "--label", "another"], dict(labels=["some-label", "another"]), id="labels-mixed-multiple"),  # noqa: E501
        pytest.param([], ["-c", "some-label", "--channel", "another"], dict(labels=["some-label", "another"]), id="channels-mixed-multiple"),  # noqa: E501
        pytest.param([], ["--no-progress"], dict(no_progress=True), id="no-progress"),
        pytest.param([], ["-i"], dict(mode="interactive"), id="interactive-short"),
        pytest.param([], ["--interactive"], dict(mode="interactive"), id="interactive-long"),
        pytest.param([], ["-u", "username"], dict(user="username"), id="username-short"),
        pytest.param([], ["--user", "username"], dict(user="username"), id="username-long"),
        pytest.param([], ["--keep-basename"], dict(keep_basename=True), id="keep-basename-long"),
        pytest.param([], ["-p", "my_package"], dict(package="my_package"), id="package-short"),
        pytest.param([], ["--package", "my_package"], dict(package="my_package"), id="package-long"),
        pytest.param([], ["--version", "1.2.3"], dict(version="1.2.3"), id="version-long"),
        pytest.param([], ["-v", "1.2.3"], dict(version="1.2.3"), id="version-short"),
        pytest.param([], ["--summary", "Some package summary"], dict(summary="Some package summary"), id="summary-long"),  # noqa: E501
        pytest.param([], ["-s", "Some package summary"], dict(summary="Some package summary"), id="summary-short"),
        pytest.param([], ["--package-type", "conda"], dict(package_type="conda"), id="package-type-long"),
        pytest.param([], ["-t", "conda"], dict(package_type="conda"), id="package-type-short"),
        pytest.param([], ["--description", "Some package description"], dict(description="Some package description"), id="description-long"),  # noqa: E501
        pytest.param([], ["-d", "Some package description"], dict(description="Some package description"), id="description-short"),  # noqa: E501
        pytest.param(["--token", "TOKEN"], [], dict(token="TOKEN"), id="token"),  # nosec
        pytest.param(["--site", "my-site.com"], [], dict(site="my-site.com"), id="site"),
    ]
)
def test_upload_arg_parsing(
    prefix_args: List[str], args: List[str], mods: Dict[str, Any], cli_mocker: InvokerFactory
) -> None:
    filename = "some-file"
    args = ["upload"] + args + [filename]
    defaults: Dict[str, Any] = dict(
        token=None,
        site=None,
        files=[[filename]],
        disable_ssl_warnings=False,
        show_traceback=False,
        log_level=20,
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
        json_help=None
    )
    expected = {**defaults, **mods}

    mock = cli_mocker("binstar_client.commands.upload.main")
    result = mock.invoke(args, prefix_args=prefix_args)
    assert result.exit_code == 0, result.stdout
    mock.assert_main_called_once()
    mock.assert_main_args_contains(expected)
