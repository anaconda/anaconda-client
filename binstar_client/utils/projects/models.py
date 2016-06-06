import inspect
import os
import tarfile
from tempfile import SpooledTemporaryFile
from binstar_client.errors import BinstarError


class CondaProject(object):
    # TODO: This class will be moved into Anaconda-Project
    def __init__(self, project_path, *args, **kwargs):
        self.project_path = project_path
        self._name = None
        self._tar = None
        self._size = None
        self.pfiles = []
        self.metadata = {
            'summary': kwargs.get('summary', None),
            'description': kwargs.get('description', None),
            'version': kwargs.get('version', None)
        }
        self.metadata = dict((k, v) for k, v in self.metadata.items() if v)

    def tar_it(self, fd=SpooledTemporaryFile()):
        with tarfile.open(mode='w', fileobj=fd) as tar:
            for pfile in self.pfiles:
                tar.add(pfile.fullpath, arcname=pfile.relativepath)
        fd.seek(0)
        self._tar = fd
        return fd

    def to_project_creation(self):
        return {
            'name': self.name,
            'access': 'public',
            'profile': {
                'description': self.metadata.get('description', ''),
                'summary': self.metadata.get('summary', ''),
            }
        }

    def to_stage(self):
        return {
            'basename': self.basename,
            'configuration': self.configuration,
        }

    @property
    def tar(self):
        if self._tar is None:
            self.tar_it()
        return self._tar

    @property
    def configuration(self):
        output = self.metadata.get('configuration', {})
        output.update({
            'size': self.size,
            'num_of_files': self.get_file_count()
        })
        return output

    def get_file_count(self):
        if os.path.isfile(self.project_path):
            return 1
        else:
            return len(self.pfiles)

    @property
    def basename(self):
        return "{}.tar".format(self.name)

    @property
    def size(self):
        if self._size is None:
            spos = self._tar.tell()
            self._tar.seek(0, os.SEEK_END)
            self._size = self._tar.tell() - spos
            self._tar.seek(spos)
        return self._size

    @property
    def name(self):
        if self._name is None:
            self._name = self._get_project_name()
        return self._name

    def _get_project_name(self):
        if os.path.isdir(self.project_path):
            return os.path.basename(os.path.abspath(self.project_path))
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
