"""Configuration for the repocore API client."""

import logging

logger = logging.getLogger(__name__)

UPLOAD_TYPE_MAPPING = {
    "conda": "conda1",
    "pypi": "bdist_wheel",
    "sdist": "sdist",
}


def get_repo_api(site=None):
    """Create a RepoCoreClient configured from anaconda-auth domain handling.

    URL construction is delegated entirely to anaconda-auth's BaseClient,
    which reads domain from config.toml / env vars automatically.
    """
    from binstar_client.repocore import RepoCoreClient

    return RepoCoreClient(site=site)
