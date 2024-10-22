# pylint: disable=missing-module-docstring,missing-function-docstring
import binstar_client.utils.spec


def test_parse_specs():
    # Reproducing for https://github.com/anaconda/anaconda-client/issues/642
    spec = binstar_client.utils.spec.parse_specs("someuser/foo/1.2.3/blah-1.2.3.tar.bz2?x=1")
    assert spec.user == "someuser"
    assert spec.name == "foo"
    assert spec.version == "1.2.3"
    assert spec.basename == "blah-1.2.3.tar.bz2"
    assert spec.attrs == {"x": "1"}
