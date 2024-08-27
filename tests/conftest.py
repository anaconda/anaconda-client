import logging
import unittest

import pytest

from tests.fixture import AnyIO
from tests.urlmock import Registry


@pytest.fixture(autouse=True)
def auto():
    """Pytest fixture version of CLITestCase.setUp and CLITestCase.tearDown."""
    get_config_patch = unittest.mock.patch('binstar_client.utils.get_config')
    get_config = get_config_patch.start()
    get_config.return_value = {}

    load_token_patch = unittest.mock.patch('binstar_client.utils.config.load_token')
    load_token = load_token_patch.start()
    load_token.return_value = '123'

    store_token_patch = unittest.mock.patch('binstar_client.utils.config.store_token')
    store_token_patch = store_token_patch.start()

    setup_logging_patch = unittest.mock.patch('binstar_client.utils.logging_utils.setup_logging')
    setup_logging_patch.start()

    logger = logging.getLogger('binstar')
    logger.setLevel(logging.INFO)
    stream = AnyIO()
    hndlr = logging.StreamHandler(stream=stream)
    hndlr.setLevel(logging.INFO)
    logger.addHandler(hndlr)

    yield

    setup_logging_patch.stop()
    get_config_patch.stop()
    load_token_patch.stop()
    store_token_patch.stop()

    logger.removeHandler(hndlr)


@pytest.fixture()
def registry():
    with Registry() as r:
        yield r
