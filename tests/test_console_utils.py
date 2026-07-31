# -*- coding: utf-8 -*-

"""Tests for binstar_client.utils.console_utils."""

import io

import pytest

import binstar_client.utils.console_utils as console_utils


@pytest.fixture(autouse=True)
def _reset_configured_flag(monkeypatch):
    # configure_console_encoding does its work only once; reset the module-level
    # guard so each test exercises it fresh.
    monkeypatch.setattr(console_utils, "_configured", False)


def _make_stream(encoding):
    return io.TextIOWrapper(io.BytesIO(), encoding=encoding, errors="backslashreplace")


def test_no_op_on_non_windows(monkeypatch):
    monkeypatch.setattr(console_utils.sys, "platform", "linux")

    stream = _make_stream("cp1252")
    monkeypatch.setattr(console_utils.sys, "stdout", stream)
    monkeypatch.setattr(console_utils.sys, "stderr", stream)

    console_utils.configure_console_encoding()

    assert stream.encoding == "cp1252"


def test_reconfigures_streams_on_windows(monkeypatch):
    monkeypatch.setattr(console_utils.sys, "platform", "win32")

    stdout = _make_stream("cp1252")
    stderr = _make_stream("cp1252")
    monkeypatch.setattr(console_utils.sys, "stdout", stdout)
    monkeypatch.setattr(console_utils.sys, "stderr", stderr)

    console_utils.configure_console_encoding()

    assert stdout.encoding == "utf-8"
    assert stderr.encoding == "utf-8"


def test_box_characters_encode_after_reconfigure(monkeypatch):
    """The box-drawing chars that broke on Windows now round-trip as UTF-8."""
    monkeypatch.setattr(console_utils.sys, "platform", "win32")

    raw = io.BytesIO()
    stream = io.TextIOWrapper(raw, encoding="cp1252", errors="backslashreplace")
    monkeypatch.setattr(console_utils.sys, "stdout", stream)
    monkeypatch.setattr(console_utils.sys, "stderr", stream)

    console_utils.configure_console_encoding()

    stream.write("┏━┳┓")
    stream.flush()

    assert raw.getvalue().decode("utf-8") == "┏━┳┓"


def test_already_utf8_stream_untouched(monkeypatch):
    monkeypatch.setattr(console_utils.sys, "platform", "win32")

    calls = []

    class Stream(io.TextIOWrapper):
        def reconfigure(self, *args, **kwargs):  # pragma: no cover - should not run
            calls.append((args, kwargs))

    stream = Stream(io.BytesIO(), encoding="utf-8")
    monkeypatch.setattr(console_utils.sys, "stdout", stream)
    monkeypatch.setattr(console_utils.sys, "stderr", stream)

    console_utils.configure_console_encoding()

    assert calls == []


def test_reconfigure_failure_is_swallowed(monkeypatch):
    monkeypatch.setattr(console_utils.sys, "platform", "win32")

    class Stream(io.TextIOWrapper):
        def reconfigure(self, *args, **kwargs):
            raise OSError("cannot reconfigure")

    stream = Stream(io.BytesIO(), encoding="cp1252")
    monkeypatch.setattr(console_utils.sys, "stdout", stream)
    monkeypatch.setattr(console_utils.sys, "stderr", stream)

    # Must not raise.
    console_utils.configure_console_encoding()


def test_runs_only_once(monkeypatch):
    monkeypatch.setattr(console_utils.sys, "platform", "win32")

    calls = []

    class Stream(io.TextIOWrapper):
        def reconfigure(self, *args, **kwargs):
            calls.append(1)

    stream = Stream(io.BytesIO(), encoding="cp1252")
    monkeypatch.setattr(console_utils.sys, "stdout", stream)
    monkeypatch.setattr(console_utils.sys, "stderr", stream)

    console_utils.configure_console_encoding()
    first = len(calls)
    console_utils.configure_console_encoding()

    assert len(calls) == first
