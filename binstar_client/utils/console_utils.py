# -*- coding: utf-8 -*-

"""Console/terminal helpers shared across CLI commands.

The main entry point here is :func:`configure_console_encoding`, which works
around a Windows-specific rendering problem: ``anaconda channel list`` (and any
other Rich-rendered table) prints its box-drawing borders as raw escaped Unicode
literals (``\\u250f``, ``\\u2501``, ...) instead of the actual characters
(``┏``, ``━``, ...).

Root cause: Rich writes Unicode box-drawing characters straight to
``sys.stdout``. On Windows the interpreter's standard streams frequently default
to a legacy code page (e.g. ``cp1252``) that cannot represent those characters.
When such a stream is configured with the ``backslashreplace`` error handler,
the box characters are silently turned into their ``\\uXXXX`` escape sequences
rather than raising or rendering. Reconfiguring the streams to UTF-8 makes the
characters encode correctly, matching the clean output seen on macOS/Linux.
"""

from __future__ import annotations

__all__ = ('configure_console_encoding',)

import io
import sys

_configured = False


def configure_console_encoding() -> None:
    """Ensure the standard streams can render Unicode box-drawing characters.

    On Windows the standard streams may use a non-UTF-8 code page, which causes
    Rich table borders to be emitted as escaped ``\\uXXXX`` literals. This
    reconfigures ``stdout``/``stderr`` to UTF-8 so those characters render
    correctly. It is a no-op on non-Windows platforms, when the stream is
    already UTF-8, and on any stream that does not support reconfiguration
    (e.g. a redirected pipe wrapped in something without ``reconfigure``).

    Safe to call multiple times; the work is performed at most once.
    """
    global _configured
    if _configured:
        return
    _configured = True

    if sys.platform != 'win32':
        return

    for stream in (sys.stdout, sys.stderr):
        _reconfigure_stream_to_utf8(stream)


def _reconfigure_stream_to_utf8(stream: object) -> None:
    """Best-effort switch of a single text stream to UTF-8 output.

    Any failure is swallowed: an unwritable or non-reconfigurable stream should
    never take down the CLI. Worst case, output falls back to the prior
    (possibly mangled) behavior rather than raising.
    """
    if not isinstance(stream, io.TextIOWrapper):
        return

    if (getattr(stream, 'encoding', '') or '').lower().replace('-', '') == 'utf8':
        return

    try:
        # ``backslashreplace`` keeps output from ever crashing on a character
        # the (now UTF-8) stream still can't encode, while UTF-8 itself covers
        # the full box-drawing range.
        stream.reconfigure(encoding='utf-8', errors='backslashreplace')
    except (ValueError, OSError):
        # ValueError: stream detached / does not support reconfigure.
        # OSError: underlying handle rejected the change.
        pass
