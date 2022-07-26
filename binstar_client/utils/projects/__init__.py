# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
from __future__ import print_function

import logging
import os
import shutil
import sys
import tempfile

from binstar_client import errors

logger = logging.getLogger('binstar.projects.upload')


class _TmpDir:
    def __init__(self, prefix):
        self._dir = tempfile.mkdtemp(prefix=prefix)

    def __exit__(self, _type, value, traceback):
        try:
            shutil.rmtree(path=self._dir)
        except Exception as error:  # pylint: disable=broad-except
            # prefer original exception to rmtree exception
            if value is None:
                print('Exception cleaning up TmpDir %s: %s' % (self._dir, str(error)), file=sys.stderr)
                raise error
            print('Failed to clean up TmpDir %s: %s' % (self._dir, str(error)), file=sys.stderr)
            raise value from error

    def __enter__(self):
        return self._dir


def _real_upload_project(project, args, username):
    try:
        from anaconda_project import project_ops  # pylint: disable=import-outside-toplevel
    except ImportError as error:
        raise errors.BinstarError('anaconda-project package is not installed') from error

    print('Uploading project: {}'.format(project.name))

    status = project_ops.upload(
        project, site=args.site, username=username, token=args.token, log_level=args.log_level,
    )

    if not status:
        for error in status.errors:  # type: ignore
            print(error, file=sys.stderr)
        print(status.status_description, file=sys.stderr)
        raise errors.BinstarError(status.status_description)

    print(status.status_description)
    return [project.name, status.url]


def upload_project(project_path, args, username):
    try:
        from anaconda_project import project  # pylint: disable=import-outside-toplevel
        from anaconda_project import project_ops  # pylint: disable=import-outside-toplevel
    except ImportError as error:
        raise errors.BinstarError(
            'To upload projects such as {}, install the anaconda-project package.'.format(project_path),
        ) from error

    if os.path.exists(project_path) and not os.path.isdir(project_path):
        # make the single file into a temporary project directory
        with (_TmpDir(prefix='anaconda_upload_')) as dirname:
            shutil.copy(project_path, dirname)
            basename_no_extension = os.path.splitext(os.path.basename(project_path))[0]
            new_project = project_ops.create(dirname, name=basename_no_extension)
            return _real_upload_project(new_project, args, username)
    else:
        new_project = project.Project(directory_path=project_path)
        return _real_upload_project(new_project, args, username)
