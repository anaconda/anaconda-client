"""
Log out from conda repo
"""
from ..utils .config import remove_token
import logging

from .base import SubCommandBase

logger = logging.getLogger('repo_cli')


class SubCommand(SubCommandBase):
    name = "logout"


    def main(self):
        if self.access_token:
            # call remove token that will remove the token from the current selected site...
            remove_token(self.args)
            self.log.info("logout successful")
        else:
            self.log.info("You are not logged in")

    def add_parser(self, subparsers):
        self.subparser = subparsers.add_parser('logout', help='Log out from your Anaconda repository',
                                          description=__doc__)

        self.subparser.set_defaults(main=self.main)