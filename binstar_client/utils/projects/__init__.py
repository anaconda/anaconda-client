import inspect
import logging
import os
from os import path
from binstar_client.errors import BinstarError
from .filer import memory_tar
from .filters import filters
from .inspectors import inspectors

log = logging.getLogger('binstar.projects.upload')


class CondaProject(object):
    # TODO: This class will be moved into Anaconda-Project
    def __init__(self, project_path, *args, **kwargs):
        self.project_path = project_path
        self._name = None
        self.pfiles = []
        self.metadata = {
            'name': self.name,
            'summary': kwargs.get('summary', None),
            'description': kwargs.get('description', None),
            'version': kwargs.get('version', None)
        }
        self.metadata = dict((k, v) for k, v in self.metadata.iteritems() if v)

    @property
    def tar(self):
        return memory_tar(self.pfiles)

    @property
    def name(self):
        if self._name is None:
            self._name = self._get_project_name()
        return self._name

    def _get_project_name(self):
        if os.path.isdir(self.project_path):
            return os.path.basename(self.project_path)
        else:
            return os.path.splitext(os.path.basename(self.project_path))[0]


class PFile(object):
    def __init__(self, **kwargs):
        self.fullpath = kwargs.get('fullpath', None)
        self.basename = kwargs.get('basename', None)
        self.relativepath = kwargs.get('relativepath', None)
        self.size = kwargs.get('size', None)
        self.populate()

    def __str__(self):
        if self.is_dir():
            return self.relativepath
        else:
            return "[{}] {}".format(self.size, self.relativepath)

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return self.fullpath == other.fullpath

    def is_dir(self):
        return os.path.isdir(self.fullpath)

    def validate(self, validator):
        if inspect.isfunction(validator):
            return validator(basename=self.basename,
                             relativepath=self.relativepath,
                             fullpath=self.fullpath)
        elif inspect.isclass(validator):
            return validator(self)()
        raise BinstarError("Invalid validator {}".format(validator))

    def populate(self):
        if self.size is None:
            self.size = os.stat(self.fullpath).st_size
        if self.basename is None:
            self.basename = os.path.basename(self.fullpath)

    def to_dict(self):
        return {
            'basename': self.basename,
            'size': self.size,
            'relativepath': self.relativepath
        }


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


def upload_project(project_path, args):
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

    return [project.name, {}]
