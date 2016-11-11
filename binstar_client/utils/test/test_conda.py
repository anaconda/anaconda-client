import os

from binstar_client.utils import conda


def test_conda_root():
    from binstar_client.utils.conda import get_conda_root

    assert get_conda_root() is not None


def test_conda_root_outside_root_environment(monkeypatch):
    called_mock = { 'called' : False }
    def mock_import_conda_root():
        called_mock['called'] = True
        raise ImportError("did not import it")

    monkeypatch.setattr('binstar_client.utils.conda._import_conda_root', mock_import_conda_root)

    from binstar_client.utils.conda import get_conda_root

    assert get_conda_root() is not None

    assert called_mock['called']


def test_conda_root_from_conda_info(monkeypatch):
    from binstar_client.utils.conda import _conda_root_from_conda_info

    conda_root = _conda_root_from_conda_info()
    assert conda_root is not None
    assert os.path.isdir(conda_root)
