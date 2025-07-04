"""
Copy packages from one account to another
"""

from __future__ import unicode_literals, print_function

import argparse
import logging
from typing import Optional

import typer

from binstar_client.utils import get_server_api, parse_specs
from binstar_client import errors

logger = logging.getLogger('binstar.copy')


def main(args):
    aserver_api = get_server_api(args.token, args.site)

    spec = args.spec

    channels = aserver_api.list_channels(spec.user)
    label_text = 'label' if (args.from_label and args.to_label) else 'channel'

    from_label = args.from_label
    to_label = args.to_label
    if from_label not in channels:
        raise errors.UserError(
            '{} {} does not exist\n\tplease choose from: {}'.format(label_text.title(), from_label, ', '.join(channels))
        )

    files = aserver_api.copy(
        spec.user,
        spec.package,
        spec.version,
        spec._basename,
        to_owner=args.to_owner,
        from_label=from_label,
        to_label=to_label,
        replace=args.replace,
        update=args.update,
    )

    for binstar_file in files:
        print('Copied file: %(basename)s' % binstar_file)
    update_msg = (
        '\nNOTE: copy command with --update option doesn`t copy already existing files.'
        + ' Try to use --replace to overwrite existing data'
    )
    no_copied_files = 'Did not copy any files. Please check your inputs with\n\n\tanaconda show {}'.format(spec)

    logger.info('Copied %s files! %s', len(files), update_msg if args.update else '')

    if not (files or args.update):
        logger.warning(no_copied_files)


def add_parser(subparsers):
    parser = subparsers.add_parser('copy', help='Copy packages from one account to another', description=__doc__)

    parser.add_argument(
        'spec',
        help=(
            'Package - written as user/package/version[/filename] '
            'If filename is not given, copy all files in the version'
        ),
        type=parse_specs,
    )
    parser.add_argument('--to-owner', help='User account to copy package to (default: your account)')

    _from = parser.add_mutually_exclusive_group()
    _to = parser.add_mutually_exclusive_group()

    _from.add_argument('--from-label', help='Label to copy packages from', default='main')
    _to.add_argument('--to-label', help='Label to put all packages into', default='main')

    method_group = parser.add_mutually_exclusive_group()

    method_group.add_argument('--replace', help='Overwrite destination package metadata', action='store_true')
    method_group.add_argument(
        '--update', help='Update missing data in destination package metadata', action='store_true'
    )
    parser.set_defaults(main=main)


def _exclusive_method(ctx: typer.Context, param: typer.CallbackParam, value: str) -> str:
    """Check for exclusivity of method arguments.

    To do this, we attach a new special attribute onto the typer Context the first time
    one of the options in the group is used.

    """
    if getattr(ctx, '_methods', None) is None:
        ctx._methods = set()  # type: ignore[attr-defined]
    if value:
        if ctx._methods:  # type: ignore[attr-defined]
            (used_mode,) = ctx._methods  # type: ignore[attr-defined]
            raise typer.BadParameter(f'mutually exclusive with {used_mode}')
        ctx._methods.add(' / '.join(f"'{o}'" for o in param.opts))  # type: ignore[attr-defined]
    return value


def mount_subcommand(app: typer.Typer, name: str, hidden: bool, help_text: str, context_settings: dict) -> None:
    @app.command(
        name=name,
        hidden=hidden,
        help=help_text,
        context_settings=context_settings,
        no_args_is_help=True,
    )
    def copy(
        ctx: typer.Context,
        spec: str = typer.Argument(
            help=(
                'Package - written as user/package/version[/filename]. '
                'If filename is not given, copy all files in the version'
            ),
            callback=parse_specs,
        ),
        to_owner: Optional[str] = typer.Option(
            None,
            help='User account to copy package to (default: your account)',
        ),
        from_label: str = typer.Option(
            'main',
            help='Label to copy packages from',
        ),
        to_label: str = typer.Option(
            'main',
            help='Label to put all packages into',
        ),
        replace: bool = typer.Option(
            False,
            help='Overwrite destination package metadata',
            callback=_exclusive_method,
        ),
        update: bool = typer.Option(
            False,
            help='Update missing data in destination package metadata',
            callback=_exclusive_method,
        ),
    ) -> None:
        args = argparse.Namespace(
            token=ctx.obj.params.get('token'),
            site=ctx.obj.params.get('site'),
            spec=spec,
            to_owner=to_owner,
            from_label=from_label,
            to_label=to_label,
            replace=replace,
            update=update,
        )

        main(args)
