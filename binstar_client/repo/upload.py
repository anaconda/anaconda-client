"""Upload command implementation for repo-core (v6) servers."""

from __future__ import annotations

import argparse
import logging
import os

from binstar_client import errors
from binstar_client.repo.api import RepoApi

logger = logging.getLogger('binstar.repo')


def upload_main(arguments: argparse.Namespace, channel: str) -> None:
    """Upload to a repo-core server instead of anaconda.org."""
    api = RepoApi(user_token=arguments.token)

    for filepath_list in arguments.files:
        for filepath in filepath_list:
            if not os.path.exists(filepath):
                logger.error(f'File "{filepath}" does not exist')
                raise errors.BinstarError(f'File "{filepath}" does not exist')

            logger.info(f'Uploading {filepath} to channel {channel}...')
            response = api.upload_file(
                filepath=filepath,
                channel=channel,
                package_type='conda1',
                name=arguments.package,
                version=arguments.version,
            )

            if response.status_code in [200, 201]:
                logger.info(f'Successfully uploaded {filepath} to {channel}')
            else:
                msg = (
                    f'Error: Failed to upload {filepath}\n'
                    f'Status: {response.status_code}\n'
                    f'Details: {response.text[:500] if response.text else "No details"}'
                )
                logger.error(msg)
                raise errors.BinstarError(msg)
