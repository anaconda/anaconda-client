# -*- coding: utf8 -*-
# pylint: disable=missing-function-docstring

"""Tests for notices command."""
import json

from tests.fixture import CLITestCase, main
from tests.urlmock import urlpatch


class Test(CLITestCase):
    """
    Tests for notices command

    These test all use a mock HTTP backend
    """

    @urlpatch
    def test_get_notices(self, registry):
        """
        Ensures notices are fetched and displayed as we expect
        """
        main(["notices", "--get", "--label", "test"])

    @urlpatch
    def test_set_notices(self, registry):
        """
        Ensures notices are set as we expect
        """
        registry.register(method="GET", path="/conda/")
        notices_json = json.dumps({
            "notices": [{
                "id": 1,
                "message": "test message",
                "level": "info",
                "created_at": "2024-02-22T14:31:24.715857",
                "updated_at": "2024-02-22T14:31:24.715857",
            }]
        })

        main(["notices", "--create", notices_json])

    @urlpatch
    def test_remove_notices(self, registry):
        """
        Ensures notices are removed as we expect
        """
        main(["notices", "--remove", "--label", "test"])
