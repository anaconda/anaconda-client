import inspect
import logging
import os
from os import path
from binstar_client.errors import BinstarError
from .filters import filters
from .inspectors import inspectors

log = logging.getLogger('binstar.projects.upload')


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


def get_project_name(filename, args):
    # TODO: This method will be moved into Anaconda-Project
    if os.path.isdir(filename):
        return os.path.basename(filename)
    else:
        return os.path.splitext(os.path.basename(filename))[0]


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


def post_process(pfiles, metadata, **args):
    print(metadata)


def projects_uploader(project_path, args):
    metadata = {'name': get_project_name(project_path, args)}
    pfiles = get_files(project_path, klass=PFile)

    print("Uploading {}".format(metadata['name']))
    for pFilter in filters:
        pfilter = pFilter(pfiles, args, basepath=project_path)
        if pfilter.can_filter():
            pfiles = list(filter(pfilter.run, pfiles))

    [inspectorKlass(pfiles).update(metadata) for inspectorKlass in inspectors]
    post_process(pfiles, metadata)
