# -*- coding: utf-8 -*-

"""Script to prepare .coveragerc file for the current OS."""

from __future__ import annotations

__all__ = ()

import os
import sys
import typing

import jinja2


ROOT: typing.Final[str] = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


TEMPLATE: typing.Final[str] = """# Use scripts/refresh_coveragerc.py to update this file

[report]
exclude_lines =
{%- for item in exclude %}
    {{ item }}
{%- endfor %}
    if __name__ == .__main__.:
    if typing.TYPE_CHECKING:
    if TYPE_CHECKING:
fail_under = 0
show_missing = true
skip_covered = true

[run]
data_file = .cache/.coverage
"""


def refresh_coveragerc() -> None:
    """Generate new .condarc file and put it in the project root."""
    exclude: typing.List[str] = ['cov-linux', 'cov-osx', 'cov-skip', 'cov-unix', 'cov-win']
    if os.name == 'nt':  # Windows
        exclude.remove('cov-win')
    else:  # Others, Unix-like
        exclude.remove('cov-unix')
        if sys.platform.startswith('linux'):  # Linux OS
            exclude.remove('cov-linux')
        elif sys.platform == 'darwin':  # OS X
            exclude.remove('cov-osx')
        else:
            raise ValueError('unexpected OS')

    environment: jinja2.Environment = jinja2.Environment()
    template: jinja2.Template = environment.from_string(TEMPLATE)
    content: str = template.render(exclude=exclude)

    stream: typing.TextIO
    with open(os.path.join(ROOT, '.coveragerc'), 'wt', encoding='utf-8') as stream:
        stream.write(content)


if __name__ == '__main__':
    refresh_coveragerc()
