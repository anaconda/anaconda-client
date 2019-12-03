from .base import SubCommandBase
from ..utils import format

class SubCommand(SubCommandBase):
    name = "search"

    def main(self):
        self.search(self.args.name[0], package_type=self.args.package_type, platform=self.args.platform,
                    limit=self.args.limit, offset=self.args.offset, sort=self.args.sort)

    def search(self, name, limit=50, offset=0, sort="-download_count",
               package_type=None, platform=None):
        data = self.api.get_artifacts(name, limit=limit, offset=offset, sort=sort)
        packages = data.pop('items')
        data['limit'] = limit
        data['offset'] = offset
        data['sort'] = sort
        format.format_packages(packages, data, self.log)

    def add_parser(self, subparsers):
        parser = subparsers.add_parser(
            self.name,
            help='Search in your Anaconda repository',
            description='Search in your Anaconda repository',
            epilog=__doc__
        )
        parser.add_argument('name', nargs=1, type=str, help='Search string')
        parser.add_argument(
            '-o', '--offset', default=0, type=int,
            help='Offset when displaying the results'
        )
        parser.add_argument(
            '-l', '--limit', default=50, type=int,
            help='Offset when displaying the results'
        )
        parser.add_argument(
            '-s', '--sort', default='download_count', type=str,
            help='Offset when displaying the results'
        )
        parser.add_argument(
            '-t', '--package-type', choices=['conda', 'pypi'],
            help='only search for packages of this type'
        )
        parser.add_argument(
            '-p', '--platform',
            choices=['osx-32', 'osx-64', 'win-32', 'win-64', 'linux-32', 'linux-64',
                     'linux-armv6l', 'linux-armv7l', 'linux-ppc64le', 'noarch'],
            help='only search for packages of the chosen platform'
        )
        parser.set_defaults(main=self.main)
