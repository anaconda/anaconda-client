'''
Remove an object from your Anaconda repository.

example::

    anaconda remove mychannel/mypackage/1.2.0/mypackage.tar.gz

'''
from .base import BulkActionCommand, PackageSpec


class SubCommand(BulkActionCommand):
    name = "copy"

    def add_parser(self, subparsers):
        parser = subparsers.add_parser('copy',
                                       help='Copy packages from one channel to another',
                                       description=__doc__)

        parser.add_argument('specs', help=('Package - written as '
                                          '<channel>/<subchannel>[::<package>[/<version>[/<filename>]]]'
                                          'If filename is not given, copy all files in the version'),
                            type=PackageSpec.from_string, nargs='+')
        parser.add_argument('-d', '--destination', help='Channel to put all packages into', default=None)
        parser.add_argument('--family', default='conda', help='artifact family (i.e.: conda, pypy, cran)',
                            action='store_true')
        parser.set_defaults(main=self.main)

