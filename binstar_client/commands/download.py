"""
Usage:
    anaconda download <package_name>
    anaconda download <channel_name>/<package_name>
"""

from __future__ import unicode_literals

import argparse
import logging
import os
from collections import OrderedDict
from contextlib import suppress
from time import mktime
from typing import List

import typer
from dateutil.parser import parse as parse_date

from binstar_client import errors
from binstar_client.errors import BinstarError, DestinationPathExists
from binstar_client.utils import get_server_api
from binstar_client.utils.config import PackageType

logger = logging.getLogger('binstar.download')


def parse(handle):
    """
    >>> parse("user/notebook")
    ('user', 'notebook')
    >>> parse("notebook")
    (None, 'notebook')

    :param handle: String
    :return: username, notebooks
    """

    components = handle.split('/', 1)
    if len(components) == 1:
        return None, components[0]
    if len(components) == 2:
        return components[0], components[1]
    raise BinstarError("{} can't be parsed".format(handle))


class Downloader:
    """
    Download files from your Anaconda repository.
    """

    def __init__(self, aserver_api, username, notebook):
        self.aserver_api = aserver_api
        self.username = username
        self.notebook = notebook
        self.output = None

    def __call__(self, package_types, output='.', force=False):
        self.output = output
        self.ensure_output()
        return self.download_files(package_types, force)

    def list_download_files(self, package_types, output='.', force=False):
        """
        This additional method was created to better handle the log output
        as files are downloaded one by one on the commands/download.py.
        """
        self.output = output
        self.ensure_output()
        files = OrderedDict()
        for file in self.list_files():
            pkg_type = file.get('type', '')
            with suppress(ValueError):
                pkg_type = PackageType(pkg_type)

            if pkg_type in package_types:
                if self.can_download(file, force):
                    files[file['basename']] = file
                else:
                    raise DestinationPathExists(file['basename'])
        return files

    def download_files(self, package_types, force=False):
        output = []
        for file in self.list_files():
            # Check type
            pkg_type = file.get('type', '')
            with suppress(ValueError):
                pkg_type = PackageType(pkg_type)

            if pkg_type in package_types:
                if self.can_download(file, force):
                    self.download(file)
                    output.append(file['basename'])
                else:
                    raise DestinationPathExists(file['basename'])
        return sorted(output)

    def download(self, dist):
        """
        Download file into location.
        """
        filename = dist['basename']
        requests_handle = self.aserver_api.download(self.username, self.notebook, dist['version'], filename)

        if not os.path.exists(os.path.dirname(filename)):
            try:
                os.makedirs(os.path.dirname(filename))
            except OSError:
                pass

        with open(os.path.join(self.output, filename), 'wb') as fdout:
            for chunk in requests_handle.iter_content(4096):
                fdout.write(chunk)

    def can_download(self, dist, force=False):
        """
        Can download if location/file does not exist or if force=True
        :param dist:
        :param force:
        :return: True/False
        """
        return not os.path.exists(os.path.join(self.output, dist['basename'])) or force

    def ensure_output(self):
        """
        Ensure output's directory exists
        """
        if not os.path.exists(self.output):
            os.makedirs(self.output)

    def list_files(self):
        """
        List available files in a project (aka notebook).
        :return: list
        """
        output = []
        tmp = {}

        files = self.aserver_api.package(self.username, self.notebook)['files']

        for file in files:
            if file['basename'] in tmp:
                tmp[file['basename']].append(file)
            else:
                tmp[file['basename']] = [file]

        for basename, versions in tmp.items():
            try:
                output.append(max(versions, key=lambda x: int(x['version'])))
            except ValueError:
                output.append(max(versions, key=lambda x: mktime(parse_date(x['upload_time']).timetuple())))
            except Exception:
                output.append(versions[-1])

        return output


def add_parser(subparsers):
    description = 'Download packages from your Anaconda repository'
    parser = subparsers.add_parser(
        'download',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help=description,
        description=description,
        epilog=__doc__,
    )

    parser.add_argument('handle', help='<channel_name>/<package_name>', action='store')

    parser.add_argument('-f', '--force', help='Overwrite', action='store_true')

    parser.add_argument('-o', '--output', help='Download as', default='.')
    pkg_types = ', '.join(pkg_type.value for pkg_type in PackageType)
    parser.add_argument(
        '-t',
        '--package-type',
        help='Set the package type [{0}]. Defaults to downloading all package types available'.format(pkg_types),
        action='append',
    )
    parser.set_defaults(main=main)


def main(args):
    aserver_api = get_server_api(args.token, args.site)
    username, package_name = parse(args.handle)
    username = username or aserver_api.user()['login']
    downloader = Downloader(aserver_api, username, package_name)
    packages_types = list(map(PackageType, args.package_type) if args.package_type else PackageType)

    try:
        download_files = downloader.list_download_files(packages_types, output=args.output, force=args.force)
        for download_file, download_dist in download_files.items():
            downloader.download(download_dist)
            logger.info('%s has been downloaded as %s', args.handle, download_file)
    except (errors.DestinationPathExists, errors.NotFound, errors.BinstarError, OSError) as err:
        logger.info(err)


def mount_subcommand(app: typer.Typer, name: str, hidden: bool, help_text: str, context_settings: dict) -> None:
    pkg_types = ', '.join(pkg_type.value for pkg_type in PackageType)

    @app.command(
        name=name,
        hidden=hidden,
        help=help_text,
        context_settings=context_settings,
        no_args_is_help=True,
    )
    def download(
        ctx: typer.Context,
        handle: str = typer.Argument(help='<channel_name>/<package_name>'),
        force: bool = typer.Option(
            False,
            '-f',
            '--force',
            help='Overwrite',
        ),
        output: str = typer.Option(
            '.',
            '-o',
            '--output',
            help='Download as',
        ),
        package_type: List[str] = typer.Option(
            None,
            '-t',
            '--package-type',
            help='Set the package type [{0}]. Defaults to downloading all package types available'.format(pkg_types),
        ),
    ) -> None:
        args = argparse.Namespace(
            token=ctx.obj.params.get('token'),
            site=ctx.obj.params.get('site'),
            handle=handle,
            force=force,
            output=output,
            package_type=package_type or None,
        )

        main(args)
