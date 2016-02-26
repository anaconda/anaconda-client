import inspect
import logging
import os
from os.path import basename, isdir, join, relpath
from binstar_client.errors import BinstarError
from .filters import VCSFilter, LargeFilesFilter, ProjectIgnoreFilter

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


class ProjectfileInspector(object):
    pass


class DocumentationInspector(object):
    valid_names = [
        'README.md',
        'README.rst',
        'README.txt',
        'README'
    ]

    def __init__(self, pfiles):
        self.pfiles = pfiles

    def get(self):
        for f in self.pfiles:
            if f.validate(self.is_documentation):
                with open(f.fullpath) as fdoc:
                    return fdoc.read()
        return None

    def is_documentation(self, **kwargs):
        basename = kwargs.get('basename', None)
        return basename is not None and basename in self.valid_names


def get_project_name(filename, args):
    if os.path.isdir(filename):
        return os.path.basename(filename)
    else:
        return os.path.splitext(os.path.basename(filename))[0]


def get_files(project_path, klass=None):
    output = []
    project_path = os.path.normpath(project_path)
    if isdir(project_path):
        for root, directories, filenames in os.walk(project_path):
            for f in filenames:
                fullpath = join(root, f)
                relativepath = relpath(fullpath, project_path)
                tmp = {
                    'fullpath': fullpath,
                    'relativepath': relativepath,
                    'basename': basename(fullpath),
                    'size': os.stat(fullpath).st_size
                }

                if klass is None:
                    output.append(tmp)
                else:
                    output.append(klass(**tmp))
    return output


def post_process(**args):
    pass


def projects_uploader(project_path, args):
    filters = [VCSFilter, ProjectIgnoreFilter, LargeFilesFilter]
    inspectors = [ProjectfileInspector]

    metadata = {'name': get_project_name(project_path, args)}
    pfiles = get_files(project_path, klass=PFile)

    print("Uploading {}".format(metadata['name']))
    for pFilter in filters:
        pfilter = pFilter(pfiles, args, basepath=project_path)
        if pfilter.can_filter():
            pfiles = list(filter(pfilter.run, pfiles))

    for pfile in pfiles:
        for inspector in inspectors:
            metadata = inspector(pfile).update(metadata)

    for pfile in pfiles:
        print(pfile)

    post_process(pfiles, metadata)
