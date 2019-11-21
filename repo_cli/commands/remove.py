'''
Remove an object from your Anaconda repository.

example::

    anaconda remove sean/meta/1.2.0/meta.tar.gz

'''
# from binstar_client.utils import get_server_api, # parse_specs, \
    # bool_input
from six.moves.urllib.parse import urlparse
import sys
from argparse import RawTextHelpFormatter
from .. import errors
from .base import SubCommandBase
import logging

logger = logging.getLogger('binstar.remove')


def bool_input(prompt, default=True):
    default_str = '[Y|n]' if default else '[y|N]'
    while 1:
        inpt = input('%s %s: ' % (prompt, default_str))
        if inpt.lower() in ['y', 'yes'] and not default:
            return True
        elif inpt.lower() in ['', 'n', 'no'] and not default:
            return False
        elif inpt.lower() in ['', 'y', 'yes']:
            return True
        elif inpt.lower() in ['n', 'no']:
            return False
        else:
            sys.stderr.write('please enter yes or no\n')


WAIT_SECONDS = 15


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

class SubCommand(SubCommandBase):
    name = "remove"

    def main(self):

        for spec in self.args.specs:
            try:
                if spec._filename:
                    self.remove_artifact(spec.channel, self.args.family, spec.package, spec.version, spec.filename, spec)
                elif spec._version:
                    self.remove_artifact(spec.channel, self.args.family, spec.package, spec.version, spec=spec)
                elif spec._package:
                    self.remove_artifact(spec.channel, self.args.family, spec.package, spec=spec)
                else:
                    logger.error('Invalid package specification: %s', spec)

            except errors.NotFound:
                if self.args.force:
                    logger.warning('', exc_info=True)
                    continue
                else:
                    raise

    def remove_artifact(self, channel, family, artifact, version=None, filename=None, spec=None):
        base_item = {
                "name": artifact,
                "family": family,
        }

        items = []
        if version or filename:
            packages = self.api.get_channel_artifacts_files(channel, family, artifact, version, filename)

            if not packages:
                logger.warning('No files matches were found for the provided spec: %s\n' % (spec))
                return

            files_descr = []
            for filep in packages:
                files_descr.append('PACKAGE: {name}:{version}-{ckey}; PLATFORM: {platform}; FILENAME: {fn}'.format(**filep))
                item = dict(base_item)
                item['ckey'] = filep['ckey']
                items.append(item)

            affected_files = '\n'.join(files_descr)
            msg = 'Are you sure you want to remove the package release %s ? The following ' \
                  'will be affected: \n\n %s\n\nConfirm?' % (spec, affected_files)

        else:
            msg = 'Are you sure you want to remove the package %s ? (and all data with it?)' % (spec,)
            items = [base_item]

        if self.args.force or bool_input(msg, False):
            self.api.channel_artifacts_bulk_actions(channel, 'delete', items)
            self.log.info('Spec %s succesfully removed\n' % (spec))
        else:
            self.log.warning('Not removing release %s\n' % (spec))


    def add_parser(self, subparsers):

        parser = subparsers.add_parser('remove',
                                          help='Remove an object from your Anaconda repository. Must refer to the '
                                               'formal package name as it appears in the URL of the package. Also '
                                               'use anaconda show <USERNAME> to see list of package names. '
                                               'Example: anaconda remove continuumio/empty-example-notebook',
                                          description=__doc__, formatter_class=RawTextHelpFormatter)

        parser.add_argument('specs', help='Package written as <channel>/<subchannel>[::<package>[/<version>[/<filename>]]]',
                            type=PackageSpec.from_string, nargs='+')
        parser.add_argument('-f', '--force', help='Do not prompt removal', action='store_true')
        parser.add_argument('--family', default='conda', help='artifact family (i.e.: conda, pypy, cran)', action='store_true')



        parser.set_defaults(main=self.main)
