"""
Manage your Anaconda repository channels.
"""

from __future__ import unicode_literals, print_function
import socket
import sys
from datetime import datetime, timedelta
import logging
import argparse
from argparse import FileType
from .. import errors
from .base import SubCommandBase

logger = logging.getLogger('repo_cli')


class SubCommand(SubCommandBase):
    name = "auth"

    def main(self):
        if self.args.info:
            self.show_token_info()
        elif self.args.list:
            self.show_tokens()
            return
        elif self.args.remove:
            self.remove_tokens(self.args.remove)
            return
        elif self.args.list_scopes:
            self.show_scopes()
        elif self.args.create:
            self.create_token(self.args.name, self.args.scopes, self.args.max_age)

    def create_token(self, name, scopes, max_age):
        # for this one we need to ask with the JWT...
        if not self.api._jwt:
            token = self.parent.auth_manager.interactive_get_token()

        if not self.api._jwt:
            self.log.info('Failed to authenticate...')
            return
        if not scopes:
            self.log.warning("You have not specified the scope of this token with the '--scopes' argument.")
            self.log.warning("This token will grant full access to %s's account" % (self.parent.auth_manager.username))
            self.log.warning("Use the --list-scopes option to see a listing of your options")
            scopes = self.api.get_scopes()

        expiration = str(datetime.now().date() + timedelta(seconds=max_age))
        data = self.api.create_user_token(name, expiration, scopes=scopes, resources=None)
        self.log.info('Token succesfully created with id: %s' % data['id'])

    def show_scopes(self):
        scopes = self.api.get_scopes()
        self.log.info('')
        self.log.info('Available scopes:')
        self.log.info('')
        self.log.info(','.join(sorted(scopes)))
        self.log.info('')

    def remove_tokens(self, tokens):
        for token in tokens:
            self.api.remove_user_token(token)
            self.log.info('Token %s successfully removed.' % token)

    def show_token_info(self):
        if not self.api._access_token:
            raise errors.Unauthorized()
        data = self.api.get_token_info()
        self.log.info('')
        self.log.info('Token: %s' % self.api._access_token)
        self.log.info('Expiration: %s' % data.get('expires_at', 'n/a'))

    def show_tokens(self):
        # for this one we need to ask with the JWT...
        if not self.api._jwt:
            token = self.parent.auth_manager.interactive_get_token()

        if not self.api._jwt:
            self.log.info('Failed to authenticate...')
            return

        data = self.api.get_user_tokens()

        if data:
            self.log.info('')
            self.log.info("Tokens count: %s" % len(data['items']))

            for token in data['items']:
                self.log.info("-----------------")
                self.log.info("id: %s" % token['id'])
                self.log.info("name: %s" % token['name'])
                self.log.info("created_at: %s" % token['created_at'])
                self.log.info("expires_at: %s" % token['expires_at'])
                self.log.info("type: %s" % token['type'])
                self.log.info("-----------------")
            self.log.info('')

    def add_parser(self, subparsers):
        description = 'Manage Authorization Tokens'
        parser = subparsers.add_parser(self.name,
                                       help=description,
                                       description=description,
                                       epilog=__doc__,
                                       formatter_class=argparse.RawDescriptionHelpFormatter)

        parser.add_argument('-n', '--name', default='conda_repo:%s' % (socket.gethostname()),
                            help='A unique name so you can identify this token later.')

        # parser.add_argument('-o', '--org', '--organization', help='Set the token owner (must be an organization)',
        #                     dest='organization')

        g = parser.add_argument_group('token creation arguments',
                                      'These arguments are only valid with the `--create` action')

        # g.add_argument('--strength', choices=['strong', 'weak'], default='strong', dest='strength')
        # g.add_argument('--strong', action='store_const', const='strong', dest='strength',
        #                help='Create a longer token (default)')
        # g.add_argument('-w', '--weak', action='store_const', const='weak', dest='strength',
        #                help='Create a shorter token')

        # g.add_argument('--url', default='http://anaconda.org',
        #                help='The url of the application that will use this token')
        age_in_days = 30
        default_age = 86400 * age_in_days # 30 days
        g.add_argument('--max-age', type=int, default=default_age,
                       help='The maximum age in seconds that this token will be valid for (default value is' \
                            ' %s that equals to %s days' % (default_age, age_in_days))
        g.add_argument('-s', '--scopes', action='append',
                       help=('Scopes for token. For example if you want to limit this token to conda '
                             'downloads only you would use --scopes "repo artifact:download"'), default=[])

        g.add_argument('--out', default=sys.stdout, type=FileType('w'))

        group = parser.add_argument_group("actions")
        group = group.add_mutually_exclusive_group(required=True)
        group.add_argument('-x', '--list-scopes', action='store_true', help='list all authentication scopes')
        group.add_argument('-l', '--list', action='store_true', help='list all user authentication tokens')
        group.add_argument('-r', '--remove', metavar='ID', nargs='+', help='remove authentication tokens')
        group.add_argument('-c', '--create', action='store_true', help='Create an authentication token')
        group.add_argument('-i', '--info', '--current-info', dest='info',
                           action='store_true', help='Show information about the current authentication token')

        parser.set_defaults(main=self.main)

