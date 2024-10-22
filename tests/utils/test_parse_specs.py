# pylint: disable=missing-module-docstring,missing-function-docstring
import binstar_client.utils.spec


def test_parse_specs():
    spec = binstar_client.utils.spec.parse_specs("bkreider/foo/1.2.3/blah-1.2.3.tar.bz2?x=1")
    assert spec.user == "bkreider"
    assert spec.name == "foo"
    assert spec.version == "1.2.3"
    assert spec.basename == "blah-1.2.3.tar.bz2"
    assert spec.attrs == {"x": "1"}
