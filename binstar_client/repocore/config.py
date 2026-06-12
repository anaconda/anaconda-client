"""Configuration for the repocore API client."""

import os
import logging

logger = logging.getLogger(__name__)

UPLOAD_TYPE_MAPPING = {
    "conda": "conda1",
    "env": "anaconda_env",
    "ipynb": "jupyter_notebook",
    "project": "anaconda_project",
    "pypi": "bdist_wheel",
    "sbom": "sbom",
    "sdist": "sdist",
    "gra": "gra_file",
}


def get_repo_api(site=None):
    """Create a RepoCoreClient configured from anaconda-auth or env var override."""
    from binstar_client.repocore import RepoCoreClient

    base_url = os.environ.get("ANACONDA_REPO_URL")

    if not base_url:
        try:
            from anaconda_auth.config import AnacondaAuthConfig

            config = AnacondaAuthConfig(site=site) if site else AnacondaAuthConfig()
            base_url = f"https://{config.domain}/api"
        except Exception as e:
            logger.debug(f"Failed to load anaconda-auth config: {e}")
            raise RuntimeError(
                "Cannot determine repocore URL. Set ANACONDA_REPO_URL or configure anaconda-auth."
            ) from e

    return RepoCoreClient(base_url=base_url, site=site)
