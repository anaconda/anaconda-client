# pylint: disable=missing-module-docstring,missing-function-docstring,import-outside-toplevel
import os
import unittest

from unittest import mock


def test_conda_root():
    from binstar_client.utils.conda import get_conda_root

    assert get_conda_root() is not None  # nosec


@mock.patch('binstar_client.utils.conda._import_conda_root')
def test_conda_root_outside_root_environment(mock_import_conda_root):
    def _import_conda_root():
        raise ImportError('did not import it')

    mock_import_conda_root.side_effect = _import_conda_root
    from binstar_client.utils.conda import get_conda_root

    assert get_conda_root() is not None  # nosec

    assert mock_import_conda_root.called  # nosec


@unittest.skip('Disabling temporarily for conda 4.4')
def test_conda_root_from_conda_info():
    from binstar_client.utils.conda import _conda_root_from_conda_info

    conda_root = _conda_root_from_conda_info()
    assert conda_root is not None  # nosec
    assert os.path.isdir(conda_root)  # nosec
