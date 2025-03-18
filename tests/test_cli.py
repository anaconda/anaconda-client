"""Test entrypoint to anaconda-cli-base"""
# pylint: disable=invalid-name
# pylint: disable=line-too-long
# pylint: disable=missing-function-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=redefined-builtin
# pylint: disable=redefined-outer-name
# pylint: disable=use-dict-literal

import shlex
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
from typer import rich_utils
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
from binstar_client.utils import parse_specs

BASE_COMMANDS = {"login", "logout", "whoami"}
HIDDEN_SUBCOMMANDS = ALL_SUBCOMMANDS - BASE_COMMANDS - NON_HIDDEN_SUBCOMMANDS


@pytest.fixture(autouse=True)
def ensure_wide_terminal(monkeypatch: MonkeyPatch) -> None:
    """Ensure the terminal is wide enough for long output to stdout to prevent line breaks."""
    monkeypatch.setattr(rich_utils, "MAX_WIDTH", 10000)


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

    if cmd not in SUBCOMMANDS_WITH_NEW_CLI:
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


class CLICase:
    # pylint: disable=too-few-public-methods

    def __init__(
        self,
        args: str = "",
        mods: Optional[Dict[str, Any]] = None,
        *,
        id: str,
        prefix: bool = False,
    ):
        args_list = shlex.split(args)

        if prefix:
            self.prefix_args, self.args = args_list, []
        else:
            self.prefix_args, self.args = [], args_list

        self.id = id
        self.mods = mods or {}
        self.marks = ()
        self.values = (self,)


@pytest.mark.parametrize(
    "case",
    [
        CLICase(id="defaults"),
        CLICase("-l some-label", dict(labels=["some-label"]), id="labels-short-single"),
        CLICase("--label some-label", dict(labels=["some-label"]), id="labels-long-single"),
        CLICase("-l some-label -l another", dict(labels=["some-label", "another"]), id="labels-short-multiple"),  # noqa: E501
        CLICase("--label some-label --label another", dict(labels=["some-label", "another"]), id="labels-long-multiple"),  # noqa: E501
        CLICase("-l some-label --label another", dict(labels=["some-label", "another"]), id="labels-mixed-multiple"),  # noqa: E501
        CLICase("-c some-label --channel another", dict(labels=["some-label", "another"]), id="channels-mixed-multiple"),  # noqa: E501
        CLICase("--no-progress", dict(no_progress=True), id="no-progress"),
        CLICase("-u username", dict(user="username"), id="username-short"),
        CLICase("--user username", dict(user="username"), id="username-long"),
        CLICase("--keep-basename", dict(keep_basename=True), id="keep-basename-long"),
        CLICase("-p my_package", dict(package="my_package"), id="package-short"),
        CLICase("--package my_package", dict(package="my_package"), id="package-long"),
        CLICase("--version 1.2.3", dict(version="1.2.3"), id="version-long"),
        CLICase("-v 1.2.3", dict(version="1.2.3"), id="version-short"),
        CLICase("--summary 'Some package summary'", dict(summary="Some package summary"), id="summary-long"),  # noqa: E501
        CLICase("-s 'Some package summary'", dict(summary="Some package summary"), id="summary-short"),
        CLICase("--package-type conda", dict(package_type="conda"), id="package-type-long"),
        CLICase("-t conda", dict(package_type="conda"), id="package-type-short"),
        CLICase("--description 'Some package description'", dict(description="Some package description"), id="description-long"),  # noqa: E501
        CLICase("-d 'Some package description'", dict(description="Some package description"), id="description-short"),  # noqa: E501
        CLICase("--thumbnail /path/to/thumbnail", dict(thumbnail="/path/to/thumbnail"), id="thumbnail-long"),  # noqa: E501
        CLICase("--private", dict(private=True), id="private-long"),
        CLICase("--register", dict(auto_register=True), id="register-long"),
        CLICase("--no-register", dict(auto_register=False), id="no-register-long"),
        CLICase("--build-id BUILD123", dict(build_id="BUILD123"), id="build-id-long"),
        CLICase("-i", dict(mode="interactive"), id="interactive-short"),
        CLICase("--interactive", dict(mode="interactive"), id="interactive-long"),
        CLICase("-f", dict(mode="fail"), id="fail-short"),
        CLICase("--fail", dict(mode="fail"), id="fail-long"),
        CLICase("--force", dict(mode="force"), id="force-long"),
        CLICase("--skip-existing", dict(mode="skip"), id="skip-existing-long"),
        CLICase("-m", dict(force_metadata_update=True), id="force-metadata-update-short"),
        CLICase("--force-metadata-update", dict(force_metadata_update=True), id="force-metadata-update-long"),  # noqa: E501
        CLICase("--token TOKEN", dict(token="TOKEN"), id="token", prefix=True),  # nosec
        CLICase("--site my-site.com", dict(site="my-site.com"), id="site", prefix=True),
        CLICase("--disable-ssl-warnings", dict(disable_ssl_warnings=True), id="disable-ssl-warnings", prefix=True),
        CLICase("--show-traceback", dict(show_traceback=True), id="show-traceback", prefix=True),
        CLICase("--verbose", dict(log_level=logging.DEBUG), id="verbose-long", prefix=True),
        CLICase("-v", dict(log_level=logging.DEBUG), id="verbose-short", prefix=True),
        CLICase("--quiet", dict(log_level=logging.WARNING), id="quiet-long", prefix=True),
        CLICase("-q", dict(log_level=logging.WARNING), id="quiet-short", prefix=True),
    ]
)
def test_upload_arg_parsing(
    case: CLICase, cli_mocker: InvokerFactory
) -> None:
    filename = "some-file"
    args = ["upload"] + case.args + [filename]
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
    expected = {**defaults, **case.mods}

    mock = cli_mocker("binstar_client.commands.upload.main")
    result = mock.invoke(args, prefix_args=case.prefix_args)
    assert result.exit_code == 0, result.stdout
    mock.assert_main_called_once()
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
def test_upload_mutually_exclusive_options(opts, error_opt, conflict_opt, mocker):
    mock = mocker.patch("binstar_client.commands.upload.main")

    runner = CliRunner()
    args = ["org", "upload"] + opts + ["./some-file"]
    result = runner.invoke(anaconda_cli_base.cli.app, args)

    assert result.exit_code == 2, result.stdout
    assert f"Invalid value for {error_opt}: mutually exclusive with {conflict_opt}" in result.stdout, result.stdout

    mock.assert_not_called()


@pytest.mark.parametrize(
    "case",
    [
        CLICase(id="defaults"),
        CLICase("--to-owner some-recipient", dict(to_owner="some-recipient"), id="to-owner"),
        CLICase("--from-label source-label", dict(from_label="source-label"), id="from-label"),
        CLICase("--to-label destination-label", dict(to_label="destination-label"), id="to-label"),
        CLICase("--replace", dict(replace=True), id="replace"),
        CLICase("--update", dict(update=True), id="update"),
        CLICase("--token TOKEN", dict(token="TOKEN"), id="token", prefix=True),  # nosec
        CLICase("--site my-site.com", dict(site="my-site.com"), id="site", prefix=True),
        CLICase("--disable-ssl-warnings", dict(disable_ssl_warnings=True), id="disable-ssl-warnings", prefix=True),
        CLICase("--show-traceback", dict(show_traceback=True), id="show-traceback", prefix=True),
        CLICase("--verbose", dict(log_level=logging.DEBUG), id="verbose-long", prefix=True),
        CLICase("-v", dict(log_level=logging.DEBUG), id="verbose-short", prefix=True),
        CLICase("--quiet", dict(log_level=logging.WARNING), id="quiet-long", prefix=True),
        CLICase("-q", dict(log_level=logging.WARNING), id="quiet-short", prefix=True),
    ]
)
def test_copy_arg_parsing(
    case: CLICase, cli_mocker: InvokerFactory
) -> None:
    args = ["copy"] + case.args + ["some-spec"]
    defaults: Dict[str, Any] = dict(
        spec=parse_specs("some-spec"),
        to_owner=None,
        from_label="main",
        to_label="main",
        replace=False,
        update=False,
    )
    expected = {**defaults, **case.mods}

    mock = cli_mocker("binstar_client.commands.copy.main")
    result = mock.invoke(args, prefix_args=case.prefix_args)
    assert result.exit_code == 0, result.stdout
    mock.assert_main_called_once()
    mock.assert_main_args_contains(expected)


@pytest.mark.parametrize(
    "case",
    [
        CLICase(id="defaults"),
        CLICase("--from-label source-label", dict(from_label="source-label"), id="from-label"),
        CLICase("--to-label destination-label", dict(to_label="destination-label"), id="to-label"),
        CLICase("--token TOKEN", dict(token="TOKEN"), id="token", prefix=True),  # nosec
        CLICase("--site my-site.com", dict(site="my-site.com"), id="site", prefix=True),
    ]
)
def test_move_arg_parsing(case: CLICase, cli_mocker: InvokerFactory) -> None:
    args = ["move"] + case.args + ["some-spec"]
    defaults: Dict[str, Any] = dict(
        token=None,
        site=None,
        spec=parse_specs("some-spec"),
        from_label="main",
        to_label="main",
    )
    expected = {**defaults, **case.mods}

    mock = cli_mocker("binstar_client.commands.move.main")
    result = mock.invoke(args, prefix_args=case.prefix_args)
    assert result.exit_code == 0, result.stdout
    mock.assert_main_called_once()
    mock.assert_main_args_contains(expected)


@pytest.mark.parametrize(
    "subcommand", ["channel", "label"],
)
@pytest.mark.parametrize(
    "case",
    [
        CLICase("--copy from to", dict(copy=["from", "to"]), id="copy"),
        CLICase("--list --organization some-org", dict(organization="some-org", list=True), id="organization-long"),
        CLICase("--list -o some-org", dict(organization="some-org", list=True), id="organization-short"),
        CLICase("--list", dict(list=True), id="list"),
        CLICase("--show label-name", dict(show="label-name"), id="show"),
        CLICase("--lock label-name", dict(lock="label-name"), id="lock"),
        CLICase("--unlock label-name", dict(unlock="label-name"), id="unlock"),
        CLICase("--remove label-name", dict(remove="label-name"), id="remove"),
    ]
)
def test_channel_arg_parsing(subcommand: str, case: CLICase, cli_mocker: InvokerFactory) -> None:
    args = [subcommand] + case.args
    defaults = dict(
        token=None,
        site=None,
        organization=None,
        copy=None,
        list=False,
        show=None,
        lock=None,
        unlock=None,
        remove=None,
    )
    expected = {**defaults, **case.mods}

    mock = cli_mocker("binstar_client.commands.channel.main")
    result = mock.invoke(args, prefix_args=case.prefix_args)
    assert result.exit_code == 0, result.stdout
    mock.assert_main_called_once()
    mock.assert_main_args_contains(expected)


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
def test_channel_mutually_exclusive_options(opts, error_opt, conflict_opt, mocker):
    mock = mocker.patch("binstar_client.commands.channel.main")

    runner = CliRunner()
    args = ["org", "channel"] + opts
    result = runner.invoke(anaconda_cli_base.cli.app, args)

    assert result.exit_code == 2, result.stdout
    assert f"Invalid value for {error_opt}: mutually exclusive with {conflict_opt}" in result.stdout, result.stdout

    mock.assert_not_called()


def test_channel_mutually_exclusive_options_required(mocker):
    mock = mocker.patch("binstar_client.commands.channel.main")

    runner = CliRunner()
    args = ["org", "channel", "--organization", "need-some-argument-to-prevent-help"]
    result = runner.invoke(anaconda_cli_base.cli.app, args)

    assert result.exit_code == 2, result.stdout
    assert "one of --copy, --list, --show, --lock, --unlock, or --remove must be provided" in result.stdout, result.stdout  # noqa: E501

    mock.assert_not_called()
