from yaml import SafeLoader, safe_dump, safe_load

SafeLoader.add_constructor('tag:yaml.org,2002:python/unicode', SafeLoader.construct_yaml_str)  # type: ignore


def yaml_load(stream):
    """Loads a dictionary from a stream"""
    return safe_load(stream)


def yaml_dump(data, stream=None):
    """Dumps an object to a YAML string"""
    return safe_dump(data, stream=stream, default_flow_style=False)
