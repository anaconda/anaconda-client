from binstar_client.errors import UserError


class PackageSpec(object):
    def __init__(self, user, package=None, version=None, basename=None, attrs=None, spec_str=None):
        self._user = user
        self._package = package
        self._version = version
        self._basename = basename
        self.attrs = attrs
        if spec_str:
            self.spec_str = spec_str
        else:
            spec_str = str(user)
            if package:
                spec_str = '%s/%s' % (spec_str, package)
            if version:
                spec_str = '%s/%s' % (spec_str, version)
            if basename:
                spec_str = '%s/%s' % (spec_str, basename)
            self.spec_str = spec_str

    def __str__(self):
        return self.spec_str

    def __repr__(self):
        return '<PackageSpec %r>' % (self.spec_str)

    @property
    def user(self):
        if self._user is None:
            raise UserError('user not given (got %r expected <username> )' % (self.spec_str,))
        return self._user

    @property
    def name(self):
        if self._package is None:
            raise UserError('package not given in spec (got %r expected <username>/<package> )' % (self.spec_str,))
        return self._package

    @property
    def package(self):
        if self._package is None:
            raise UserError('package not given in spec (got %r expected <username>/<package> )' % (self.spec_str,))
        return self._package

    @property
    def version(self):
        if self._version is None:
            raise UserError('version not given in spec (got %r expected <username>/<package>/<version> )' % (self.spec_str,))
        return self._version

    @property
    def basename(self):
        if self._basename is None:
            raise UserError('basename not given in spec (got %r expected <username>/<package>/<version>/<filename> )' % (self.spec_str,))
        return self._basename


def package_specs(spec):
    user = spec
    package = None
    attrs = {}
    if '/' in user:
        user, package = user.split('/', 1)
    if '/' in package:
        raise TypeError('invalid package spec')

    return PackageSpec(user, package, None, None, attrs, spec)


def parse_specs(spec):
    user = spec
    package = version = basename = None
    attrs = {}
    if '/' in user:
        user, package = user.split('/', 1)
    if package and '/' in package:
        package, version = package.split('/', 1)

    if version and '/' in version:
        version, basename = version.split('/', 1)

    if basename and '?' in basename:
        basename, qsl = basename.rsplit('?', 1)
        attrs = dict(urlparse.parse_qsl(qsl))

    return PackageSpec(user, package, version, basename, attrs, spec)
