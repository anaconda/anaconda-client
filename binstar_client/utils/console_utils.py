# -*- coding: utf-8 -*-

"""Console/terminal helpers shared across CLI commands.

Rich writes Unicode box-drawing borders (``┏━┳┃``) straight to ``sys.stdout``.
When Rich believes the stream is UTF-8 it emits those characters verbatim; if
the stream then encodes with the ``backslashreplace`` error handler over a codec
that can't represent them, each one lands as an escaped ``\\uXXXX`` literal
instead of a border — the classic broken table seen on Windows consoles.

We defend against that by pinning the standard streams to UTF-8 with the
``replace`` error handler (a real char, never ``\\uXXXX``), matching the clean
output macOS/Linux already produce.
"""

from __future__ import annotations

__all__ = ('configure_console_encoding',)

import io
import sys

_configured = False


def configure_console_encoding() -> None:
    """Pin stdout/stderr to UTF-8 so Rich borders render as characters.

    Safe to call multiple times; does its work at most once. Never raises — a
    stream that can't be reconfigured is left as-is rather than taking down the
    CLI.
    """
    global _configured
    if _configured:
        return
    _configured = True

    for stream in (sys.stdout, sys.stderr):
        _pin_stream_to_utf8(stream)


def _pin_stream_to_utf8(stream: object) -> None:
    """Ensure a single text stream encodes as UTF-8 with a safe error handler.

    Prefers ``TextIOWrapper.reconfigure``; when that isn't available (older or
    non-standard streams) rewraps the underlying binary buffer. Both paths use
    ``errors='replace'`` so an unencodable char degrades to ``?`` rather than a
    ``\\uXXXX`` literal. ``backslashreplace`` is treated as "needs fixing" even
    when the encoding already reports UTF-8, since that handler is exactly what
    produces the escaped-literal borders.
    """
    if not isinstance(stream, io.TextIOWrapper):
        return

    encoding_ok = (getattr(stream, 'encoding', '') or '').lower().replace('-', '') == 'utf8'
    errors_ok = getattr(stream, 'errors', '') not in ('backslashreplace', 'xmlcharrefreplace')
    if encoding_ok and errors_ok:
        return

    # Preferred path: reconfigure in place (Python 3.7+ standard streams).
    reconfigure = getattr(stream, 'reconfigure', None)
    if callable(reconfigure):
        try:
            reconfigure(encoding='utf-8', errors='replace')
            return
        except (ValueError, OSError):
            pass

    # Fallback: rewrap the raw buffer. Flush first so buffered bytes aren't lost,
    # and keep line_buffering so interactive output still appears promptly.
    buffer = getattr(stream, 'buffer', None)
    if buffer is None:
        return
    try:
        stream.flush()
        wrapped = io.TextIOWrapper(
            buffer,
            encoding='utf-8',
            errors='replace',
            newline='',
            line_buffering=getattr(stream, 'line_buffering', False),
        )
    except (ValueError, OSError):
        return

    if stream is sys.stdout:
        sys.stdout = wrapped
    elif stream is sys.stderr:
        sys.stderr = wrapped
