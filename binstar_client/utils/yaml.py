# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from yaml import safe_dump, safe_load


def yaml_load(stream):
    """Loads a dictionary from a stream"""
    return safe_load(stream)


def yaml_dump(data, stream=None):
    """Dumps an object to a YAML string"""
    return safe_dump(data, stream=stream, default_flow_style=False)
