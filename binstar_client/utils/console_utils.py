# -*- coding: utf-8 -*-

"""Console/terminal helpers shared across CLI commands.

Rich writes Unicode box-drawing borders straight to ``sys.stdout``. On Windows
the standard streams often use a legacy code page (e.g. ``cp1252``) that can't
represent them, so with the ``backslashreplace`` error handler they render as
escaped ``\\uXXXX`` literals instead of characters like ``┏━┳``. Reconfiguring
the streams to UTF-8 fixes this, matching macOS/Linux output.
"""

from __future__ import annotations

__all__ = ('configure_console_encoding',)

import io
import sys

_configured = False


def configure_console_encoding() -> None:
    """Reconfigure Windows stdout/stderr to UTF-8 so Rich borders render.

    No-op off Windows and safe to call multiple times; runs its work at most once.
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
    """Switch a single text stream to UTF-8, ignoring streams that can't.

    A non-reconfigurable or detached stream must never take down the CLI, so
    failures fall back to prior behavior rather than raising.
    """
    if not isinstance(stream, io.TextIOWrapper):
        return

    if (getattr(stream, 'encoding', '') or '').lower().replace('-', '') == 'utf8':
        return

    try:
        stream.reconfigure(encoding='utf-8', errors='backslashreplace')
    except (ValueError, OSError):
        pass
