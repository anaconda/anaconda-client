# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

try:
    import ruamel_yaml as yaml
except ImportError:                                         # pragma: no cover
    try:                                                    # pragma: no cover
        import ruamel.yaml as yaml                          # pragma: no cover
    except ImportError:                                     # pragma: no cover
        raise ImportError("No yaml library available.\n"    # pragma: no cover
                            "To proceed, conda install "      # pragma: no cover
                            "ruamel_yaml")                    # pragma: no cover

def yaml_load(stream):
    """Loads a dictionary from a stream"""
    return yaml.load(stream, Loader=yaml.RoundTripLoader, version="1.2")


def yaml_dump(data, stream=None):
    """Dumps an object to a YAML string"""
    return yaml.dump(data, stream=stream, Dumper=yaml.RoundTripDumper,
                     block_seq_indent=2, default_flow_style=False,
                     indent=2)
