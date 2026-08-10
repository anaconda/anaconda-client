# -*- coding: utf-8 -*-

"""Tests for binstar_client.utils.console_utils."""

import io

import pytest

import binstar_client.utils.console_utils as console_utils

BOX = "┏━┳┓"


@pytest.fixture(autouse=True)
def _reset_configured_flag(monkeypatch):
    # The work runs at most once per process; reset the guard so each test is fresh.
    monkeypatch.setattr(console_utils, "_configured", False)


def _install_streams(monkeypatch, encoding, errors, cls=io.TextIOWrapper):
    stdout = cls(io.BytesIO(), encoding=encoding, errors=errors)
    stderr = cls(io.BytesIO(), encoding=encoding, errors=errors)
    monkeypatch.setattr(console_utils.sys, "stdout", stdout)
    monkeypatch.setattr(console_utils.sys, "stderr", stderr)
    return stdout, stderr


def test_reconfigures_narrow_codec_to_utf8(monkeypatch):
    stdout, stderr = _install_streams(monkeypatch, "cp1252", "backslashreplace")

    console_utils.configure_console_encoding()

    assert stdout.encoding == "utf-8"
    assert stderr.encoding == "utf-8"


def test_fixes_backslashreplace_even_when_encoding_is_utf8(monkeypatch):
    # The exact broken Windows state: encoding *reports* utf-8, but the
    # backslashreplace handler still escapes box chars to \uXXXX literals.
    stdout, stderr = _install_streams(monkeypatch, "utf-8", "backslashreplace")

    console_utils.configure_console_encoding()

    assert stdout.errors == "replace"
    assert stderr.errors == "replace"


def test_leaves_healthy_utf8_stream_untouched(monkeypatch):
    stdout, _ = _install_streams(monkeypatch, "utf-8", "strict")

    console_utils.configure_console_encoding()

    # Already UTF-8 with a safe handler — no reconfigure, no rewrap.
    assert stdout.encoding == "utf-8"
    assert stdout.errors == "strict"


def test_box_characters_encode_instead_of_becoming_uXXXX(monkeypatch):
    """The bug's payoff: borders land as real bytes, never as \\uXXXX literals."""
    stdout, _ = _install_streams(monkeypatch, "cp1252", "backslashreplace")

    console_utils.configure_console_encoding()
    stdout.write(BOX)
    stdout.flush()

    written = stdout.buffer.getvalue()
    assert written.decode("utf-8") == BOX
    assert b"\\u" not in written


def test_fallback_rewraps_non_reconfigurable_stream(monkeypatch):
    class Stubborn(io.TextIOWrapper):
        def reconfigure(self, *args, **kwargs):
            raise OSError("cannot reconfigure")

    stdout, _ = _install_streams(monkeypatch, "cp1252", "backslashreplace", cls=Stubborn)

    console_utils.configure_console_encoding()

    # reconfigure() refused, so the raw buffer was rewrapped as a fresh UTF-8 stream.
    assert console_utils.sys.stdout is not stdout
    assert console_utils.sys.stdout.encoding == "utf-8"

    console_utils.sys.stdout.write(BOX)
    console_utils.sys.stdout.flush()
    assert stdout.buffer.getvalue().decode("utf-8") == BOX


def test_runs_at_most_once(monkeypatch):
    stdout, _ = _install_streams(monkeypatch, "cp1252", "backslashreplace")
    console_utils.configure_console_encoding()

    # Swap in a fresh broken stream; a second call must be a no-op (guard set).
    replacement, _ = _install_streams(monkeypatch, "cp1252", "backslashreplace")
    console_utils.configure_console_encoding()

    assert replacement.encoding == "cp1252"


def test_ignores_non_textiowrapper_stream(monkeypatch):
    class NotATextStream:
        encoding = "cp1252"
        errors = "backslashreplace"

    stub = NotATextStream()
    monkeypatch.setattr(console_utils.sys, "stdout", stub)
    monkeypatch.setattr(console_utils.sys, "stderr", stub)

    # Non-TextIOWrapper streams (redirected pipes, test doubles) are left as-is.
    console_utils.configure_console_encoding()

    assert console_utils.sys.stdout is stub


def test_survives_stream_without_buffer(monkeypatch):
    class NoBuffer(io.TextIOWrapper):
        def reconfigure(self, *args, **kwargs):
            raise OSError("cannot reconfigure")

        @property
        def buffer(self):
            return None

    _install_streams(monkeypatch, "cp1252", "backslashreplace", cls=NoBuffer)

    # No reconfigure and no buffer to rewrap: must degrade quietly, not crash.
    console_utils.configure_console_encoding()
