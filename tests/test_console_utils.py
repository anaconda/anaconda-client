# -*- coding: utf-8 -*-

"""Tests for binstar_client.utils.console_utils."""

import io

import pytest

import binstar_client.utils.console_utils as console_utils


@pytest.fixture(autouse=True)
def _reset_configured_flag(monkeypatch):
    # The work runs at most once per process; reset the guard so each test is fresh.
    monkeypatch.setattr(console_utils, "_configured", False)


def _install_streams(monkeypatch, platform, encoding, cls=io.TextIOWrapper):
    monkeypatch.setattr(console_utils.sys, "platform", platform)
    stdout = cls(io.BytesIO(), encoding=encoding, errors="backslashreplace")
    stderr = cls(io.BytesIO(), encoding=encoding, errors="backslashreplace")
    monkeypatch.setattr(console_utils.sys, "stdout", stdout)
    monkeypatch.setattr(console_utils.sys, "stderr", stderr)
    return stdout, stderr


def test_leaves_streams_alone_off_windows(monkeypatch):
    stdout, stderr = _install_streams(monkeypatch, "linux", "cp1252")

    console_utils.configure_console_encoding()

    assert stdout.encoding == "cp1252"
    assert stderr.encoding == "cp1252"


def test_reconfigures_both_streams_on_windows(monkeypatch):
    stdout, stderr = _install_streams(monkeypatch, "win32", "cp1252")

    console_utils.configure_console_encoding()

    assert stdout.encoding == "utf-8"
    assert stderr.encoding == "utf-8"


def test_box_characters_round_trip_after_reconfigure(monkeypatch):
    """The bug's payoff: box-drawing chars encode instead of becoming \\uXXXX."""
    stdout, _ = _install_streams(monkeypatch, "win32", "cp1252")

    console_utils.configure_console_encoding()
    stdout.write("┏━┳┓")
    stdout.flush()

    assert stdout.buffer.getvalue().decode("utf-8") == "┏━┳┓"


def test_survives_non_reconfigurable_stream(monkeypatch):
    class Stubborn(io.TextIOWrapper):
        def reconfigure(self, *args, **kwargs):
            raise OSError("cannot reconfigure")

    _install_streams(monkeypatch, "win32", "cp1252", cls=Stubborn)

    # A stream that refuses reconfiguration must not crash the CLI.
    console_utils.configure_console_encoding()
