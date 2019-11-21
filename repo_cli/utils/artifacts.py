from six.moves.urllib.parse import urlparse
import sys
from argparse import RawTextHelpFormatter
from .. import errors


class PackageSpec(object):
    def __init__(self, channel, package=None, version=None, filename=None, attrs=None, spec_str=None):
        self._user = channel
        self._package = package
        self._version = version
        self._filename = filename
        self.attrs = attrs
        if spec_str:
            self.spec_str = spec_str
        else:
            spec_str = str(channel)
            if package:
                spec_str = '%s/%s' % (spec_str, package)
            if version:
                spec_str = '%s/%s' % (spec_str, version)
            if filename:
                spec_str = '%s/%s' % (spec_str, filename)
            self.spec_str = spec_str

    @classmethod
    def from_string(cls, spec_string):
        channel = spec_string
        package = version = filename = None
        attrs = {}
        if '::' in channel:
            channel, package = channel.split('::', 1)
        if package and '/' in package:
            package, version = package.split('/', 1)

        if version and '/' in version:
            version, filename = version.split('/', 1)

        if filename and '?' in filename:
            filename, qsl = filename.rsplit('?', 1)
            attrs = dict(urlparse.parse_qsl(qsl))

        return PackageSpec(channel, package, version, filename, attrs, spec_string)

    def __str__(self):
        return self.spec_str

    def __repr__(self):
        return '<PackageSpec %r>' % (self.spec_str)

    @property
    def channel(self):
        if self._user is None:
            raise errors.UserError('user not given (got %r expected <username> )' % (self.spec_str,))
        return self._user

    @property
    def name(self):
        if self._package is None:
            raise errors.UserError('package not given in spec (got %r expected <username>/<package> )' % (self.spec_str,))
        return self._package

    @property
    def package(self):
        if self._package is None:
            raise errors.UserError('package not given in spec (got %r expected <username>/<package> )' % (self.spec_str,))
        return self._package

    @property
    def version(self):
        if self._version is None:
            raise errors.UserError('version not given in spec (got %r expected <username>/<package>/<version> )' % (self.spec_str,))
        return self._version

    @property
    def filename(self):
        if self._filename is None:
            raise errors.UserError('filename not given in spec (got %r expected <username>/<package>/<version>/<filename> )' % (self.spec_str,))
        return self._filename

class SimplePackageSpec(object):
    def __init__(self, channel, package=None, version=None, filename=None, attrs=None, spec_str=None):
        self.channel = channel
        self.package = package
        self.version = version
        self.filename = filename
        self.attrs = attrs

        if spec_str:
            self.spec_str = spec_str
        else:
            spec_str = str(channel)
            if package:
                spec_str = '%s/%s' % (spec_str, package)
            if version:
                spec_str = '%s/%s' % (spec_str, version)
            if filename:
                spec_str = '%s/%s' % (spec_str, filename)
            self.spec_str = spec_str

    @classmethod
    def from_string(cls, spec_string):
        channel = spec_string
        package = version = filename = None
        attrs = {}
        if '::' in channel:
            channel, package = channel.split('::', 1)
        if package and '/' in package:
            package, version = package.split('/', 1)

        if version and '/' in version:
            version, filename = version.split('/', 1)

        if filename and '?' in filename:
            filename, qsl = filename.rsplit('?', 1)
            attrs = dict(urlparse.parse_qsl(qsl))

        return SimplePackageSpec(channel, package, version, filename, attrs, spec_string)

    def __str__(self):
        return self.spec_str

    def __repr__(self):
        return '<PackageSpec %r>' % (self.spec_str)
