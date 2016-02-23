import inspect
import os
import logging
from binstar_client.errors import BinstarError

log = logging.getLogger('binstar.projects.upload')


class DocumentationExtractor(object):
    valid_names = [
        'README.md',
        'README.rst',
        'README.txt',
        'README'
    ]

    def __init__(self, files):
        self.files = files

    def get(self):
        for f in self.files:
            if f.validate(self.is_documentation):
                with open(f.full_path) as fdoc:
                    return fdoc.read()
        return None

    def is_documentation(self, **kwargs):
        basename = kwargs.get('basename', None)
        return basename is not None and basename in self.valid_names


class PFile(object):
    def __init__(self, filename, **kwargs):
        self.filename = filename
        self.root = kwargs.get('root', None)
        self.replace = kwargs.get('replace', './')

    def __str__(self):
        if self.is_dir():
            return self.printable
        else:
            return "[{}] {}".format(self.size, self.printable)

    def __repr__(self):
        return self.__str__()

    def is_dir(self):
        return os.path.isdir(self.full_path)

    def validate(self, validator):
        if inspect.isfunction(validator):
            return validator(basename=self.basename,
                             filename=self.filename,
                             full_path=self.full_path)
        elif inspect.isclass(validator):
            return validator(self)()
        raise BinstarError("Invalid validator {}".format(validator))

    @property
    def printable(self):
        return self.full_path.replace(self.replace, '', 1)

    @property
    def basename(self):
        return os.path.basename(self.filename)

    @property
    def size(self):
        return os.stat(self.full_path).st_size

    @property
    def full_path(self):
        if self.root is None:
            return self.filename
        else:
            return os.path.join(self.root, self.filename)


def get_project_name(filename, args):
    if os.path.isdir(filename):
        return os.path.basename(filename)
    else:
        return os.path.splitext(os.path.basename(filename))[0]


def get_pfiles(project_location, args):
    output = []
    if os.path.isdir(project_location):
        for root, directories, filenames in os.walk(project_location):
            for filename in filenames:
                output.append(PFile(filename, root=root, replace=project_location))
        return output
    else:
        return [PFile(project_location)]


def post_process(pfiles, metadata={}):
    pass


class Filter(object):
    def __init__(self, pfiles, *args, **kwargs):
        self.pfiles = pfiles

    def __call__(self):
        return True

    def update_metadata(self, metadata={}):
        return metadata


class RVSFilter(Filter):
    def __call__(self, pfile):
        log.debug("Filtering: {}".format(pfile))
        return True


class LargeFilesFilter(Filter):
    pass


filters = [RVSFilter, LargeFilesFilter]


def projects_uploader(project_location, args):
    metadata = {'name': get_project_name(project_location, args)}
    pfiles = get_pfiles(project_location, args)

    for pFilter in filters:
        pfilter = pFilter(pfiles, args)
        pfiles = filter(pfilter, pfiles)
        metadata = pfilter.update_metadata(metadata)

    post_process(pfiles, metadata)
