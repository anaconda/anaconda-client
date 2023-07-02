# -*- coding: utf8 -*-

"""Tests for :mod:`binstar_client.utils.conda`."""

from __future__ import annotations

__all__ = ()

import os
import typing

from binstar_client.utils import conda


def test_find_conda() -> None:
    """Check :func:`~binstar_client.utils.conda.find_conda`."""
    conda_info: conda.CondaInfo = typing.cast(conda.CondaInfo, conda.find_conda())
    assert conda_info

    assert conda_info['CONDA_EXE']
    assert os.path.isfile(conda_info['CONDA_EXE'])

    assert conda_info['CONDA_PREFIX']
    assert os.path.isdir(conda_info['CONDA_PREFIX'])

    assert conda_info['CONDA_ROOT']
    assert os.path.isdir(conda_info['CONDA_ROOT'])


def test_conda_vars() -> None:
    """Check lazy :data:`~binstar_client.utils.conda.CONDA_INFO` and other related lazy module properties."""
    assert conda.CONDA_INFO

    assert conda.CONDA_EXE
    assert conda.CONDA_EXE is typing.cast(conda.CondaInfo, conda.CONDA_INFO)['CONDA_EXE']
    assert os.path.isfile(conda.CONDA_EXE)

    assert conda.CONDA_PREFIX
    assert conda.CONDA_PREFIX is typing.cast(conda.CondaInfo, conda.CONDA_INFO)['CONDA_PREFIX']
    assert os.path.isdir(conda.CONDA_PREFIX)

    assert conda.CONDA_ROOT
    assert conda.CONDA_ROOT is typing.cast(conda.CondaInfo, conda.CONDA_INFO)['CONDA_ROOT']
    assert os.path.isdir(conda.CONDA_ROOT)
