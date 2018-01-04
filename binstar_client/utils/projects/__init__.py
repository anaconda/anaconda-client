from __future__ import print_function

import logging
import os
import shutil
import sys
import tempfile

from binstar_client import errors

logger = logging.getLogger('binstar.projects.upload')


class _TmpDir(object):
    def __init__(self, prefix):
        self._dir = tempfile.mkdtemp(prefix=prefix)

    def __exit__(self, type, value, traceback):
        try:
            shutil.rmtree(path=self._dir)
        except Exception as e:
            # prefer original exception to rmtree exception
            if value is None:
                print("Exception cleaning up TmpDir %s: %s" % (self._dir, str(e)), file=sys.stderr)
                raise e
            else:
                print("Failed to clean up TmpDir %s: %s" % (self._dir, str(e)), file=sys.stderr)
                raise value

    def __enter__(self):
        return self._dir


def _real_upload_project(project, args, username):
    from anaconda_project import project_ops

    print("Uploading project: {}".format(project.name))

    status = project_ops.upload(project, site=args.site, username=username,
                                token=args.token, log_level=args.log_level)

    for log in status.logs:
        print(log)
    if not status:
        for error in status.errors:
            print(error, file=sys.stderr)
        print(status.status_description, file=sys.stderr)
        raise errors.BinstarError(status.status_description)
    else:
        print(status.status_description)
        return [project.name, status.url]


def upload_project(project_path, args, username):
    try:
        from anaconda_project import project_ops
    except ImportError:
        raise errors.BinstarError("To upload projects such as {}, install the anaconda-project package.".format(project_path))

    from anaconda_project import project

    if os.path.exists(project_path) and not os.path.isdir(project_path):
        # make the single file into a temporary project directory
        with (_TmpDir(prefix="anaconda_upload_")) as dirname:
            shutil.copy(project_path, dirname)
            basename_no_extension = os.path.splitext(os.path.basename(project_path))[0]
            project = project_ops.create(dirname, name=basename_no_extension)
            return _real_upload_project(project, args, username)
    else:
        project = project.Project(directory_path=project_path)
        return _real_upload_project(project, args, username)
