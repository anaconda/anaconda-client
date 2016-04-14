import logging
import os
from os import path
from binstar_client.utils import get_server_api
from .filters import filters
from .inspectors import inspectors
from .uploader import ProjectUploader
from .models import CondaProject, PFile

log = logging.getLogger('binstar.projects.upload')


def get_files(project_path, klass=None):
    output = []
    project_path = os.path.normpath(project_path)
    if path.isdir(project_path):
        for root, directories, filenames in os.walk(project_path):
            for f in filenames:
                fullpath = path.join(root, f)
                relativepath = path.relpath(fullpath, project_path)
                tmp = {
                    'fullpath': fullpath,
                    'relativepath': relativepath,
                    'basename': path.basename(fullpath),
                    'size': os.stat(fullpath).st_size
                }

                if klass is None:
                    output.append(tmp)
                else:
                    output.append(klass(**tmp))
    return output


def upload_project(project_path, args, username):
    project = CondaProject(
        project_path,
        description=args.description,
        summary=args.summary,
        version=args.version
    )

    print("Uploading project: {}".format(project.name))

    pfiles = get_files(project_path, klass=PFile)
    for pFilter in filters:
        pfilter = pFilter(pfiles, args, basepath=project_path)
        if pfilter.can_filter():
            pfiles = list(filter(pfilter.run, pfiles))

    project.pfiles = pfiles
    [inspector(pfiles).update(project.metadata) for inspector in inspectors]
    project.tar_it()

    api = get_server_api(
        token=args.token,
        site=args.site,
        log_level=args.log_level,
        cls=ProjectUploader,
        username=username,
        project=project)
    api.upload()

    return [project.name, {}]
