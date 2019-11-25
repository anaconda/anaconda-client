from .base import SubCommandBase
from ..utils import format

class SubCommand(SubCommandBase):
    name = "search"

    def main(self):
        self.search(self.args.name[0], package_type=self.args.package_type, platform=self.args.platform)

    def search(self, name, package_type=None, platform=None, limit=50):
        packages = self.api.get_artifacts(name)
        format.format_packages(self.log, packages)
        # logger.info("\nRun 'anaconda show <USER/PACKAGE>' to get installation details")

    def add_parser(self, subparsers):
        parser = subparsers.add_parser(
            self.name,
            help='Search in your Anaconda repository',
            description='Search in your Anaconda repository',
            epilog=__doc__
        )
        parser.add_argument('name', nargs=1, type=str, help='Search string')
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
