"""
Manage Authentication tokens

See also:

  * [Using Anaconda Cloud Tokens](http://docs.anaconda.org/using.html#Tokens)

"""
from __future__ import print_function

import argparse
import getpass
import logging
import socket
import sys

from argparse import FileType
from datetime import datetime

import pytz

from dateutil.parser import parse as parse_date
from six.moves import input

from binstar_client import errors
from binstar_client.utils import get_server_api


logger = logging.getLogger('binstar.auth')


SCOPE_EXAMPLES = """

Examples

To allow access to only conda downloads from your account you can run:

    anaconda auth --create --scopes 'repos conda:download'

To allow full access to your account:

    anaconda auth --create --scopes 'all'

"""


def utcnow():
    now = datetime.utcnow()
    return now.replace(tzinfo=pytz.utc)


def format_timedelta(date, expired=True):
    if not date:
        return 'Never'

    now = utcnow()

    if date < now:
        if expired:
            return  'expired'
        else:
            tmp = date
            date = now
            now = tmp

    delta = date - now

    if delta.days:
        days = (delta.days + (delta.seconds / (60. * 60. * 24.0)))
        if days > 3:
            days = int(days)
            return '%i days' % days
        else:
            return '%.1f days' % days
    elif delta.seconds > 60 * 60:
        return  '%.1f hours' % (delta.seconds / (60. * 60))
    elif delta.seconds > 60:
        return '%i minutes' % (delta.seconds // 60)
    else:
        return '%i seconds' % delta.seconds


def show_auths(authentications):
    header = {'id': 'ID',
              'application': 'Application',
              'remote_addr':'Remote Addr',
              'hostname':'Host',
              'expires':'Expires In',
              'scopes':'Scopes'}

    template = '%(id)-25s | %(application)-35s | %(remote_addr)-20s | %(hostname)-25s | %(expires)-15s | %(scopes)-25s'
    logger.info('')
    logger.info(template % header)
    logger.info('%s-+-%s-+-%s-+-%s-+-%s-+-%s' % ('-' * 25, '-' * 35, '-' * 20, '-' * 25, '-' * 15, '-' * 25))

    for auth in authentications:
        if auth['expires']:
            expires = parse_date(auth['expires'])
        else:
            expires = None
        auth['expires'] = format_timedelta(expires)

        first_time = True
        scope_items = auth['scopes']
        if scope_items:
            for scope in scope_items:
                if first_time:
                    auth['scopes'] = scope
                    logger.info(template % auth)
                    first_time = False
                else:
                    auth['id'] = ''
                    auth['application'] = ''
                    auth['remote_addr'] = ''
                    auth['hostname'] = ''
                    auth['expires'] = ''
                    auth['scopes'] = scope
                    logger.info(template % auth)
        else:
            auth['scopes'] = 'NO_SCOPE'
            logger.info(template % auth)


def main(args):
    aserver_api = get_server_api(args.token, args.site)
    if args.info:
        data = aserver_api.authentication()
        logger.info('Name: %s' % data['application'])
        logger.info('Id: %s' % data['id'])
    if args.list:
        show_auths(aserver_api.authentications())
        return
    elif args.remove:
        for auth_name in args.remove:
            aserver_api.remove_authentication(auth_name, args.organization)
            logger.info("Removed token %s" % auth_name)
        return
    elif args.list_scopes:
        scopes = aserver_api.list_scopes()
        for key in sorted(scopes):
            logger.info(key)
            logger.info('  ' + scopes[key])
            logger.info('')
        logger.info(SCOPE_EXAMPLES)

    elif args.create:
        auth_type = aserver_api.authentication_type()

        try:
            current_user = aserver_api.user()
            username = current_user['login']
        except:
            if auth_type == 'kerberos':
                logger.error("Kerberos authentication needed, please use 'anaconda login' to authenticate")
                return

            current_user = None
            sys.stderr.write('Username: ')
            sys.stderr.flush()
            username = input('')

        scopes = [scope for scopes in args.scopes for scope in scopes.split()]
        if not scopes:
            logger.warning("You have not specified the scope of this token with the '--scopes' argument.")
            logger.warning("This token will grant full access to %s's account" % (args.organization or username))
            logger.warning("Use the --list-scopes option to see a listing of your options")

        for _ in range(3):
            try:
                if auth_type == 'kerberos':
                    token = aserver_api._authenticate(
                        None,
                        args.name,
                        application_url=args.url,
                        scopes=scopes,
                        for_user=args.organization,
                        max_age=args.max_age,
                        created_with=' '.join(sys.argv),
                        strength=args.strength,
                        fail_if_already_exists=True
                    )
                else:
                    sys.stderr.write("Please re-enter %s's " % username)
                    password = getpass.getpass()
                    token = aserver_api.authenticate(
                        username, password,
                        args.name,
                        application_url=args.url,
                        scopes=scopes,
                        for_user=args.organization,
                        max_age=args.max_age,
                        created_with=' '.join(sys.argv),
                        strength=args.strength,
                        fail_if_already_exists=True
                    )
                args.out.write(token)
                break
            except errors.Unauthorized:
                logger.error('Invalid Username password combination, please try again')
                continue


def add_parser(subparsers):

    description = 'Manage Authorization Tokens'
    parser = subparsers.add_parser('auth',
                                    help=description,
                                    description=description,
                                    epilog=__doc__,
                                    formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('-n', '--name', default='binstar_token:%s' % (socket.gethostname()),
                        help='A unique name so you can identify this token later. View your tokens at anaconda.org/settings/access')

    parser.add_argument('-o', '--org', '--organization', help='Set the token owner (must be an organization)', dest='organization')

    g = parser.add_argument_group('token creation arguments', 'These arguments are only valid with the `--create` action')

    g.add_argument('--strength', choices=['strong', 'weak'], default='strong', dest='strength')
    g.add_argument('--strong', action='store_const', const='strong', dest='strength' , help='Create a longer token (default)')
    g.add_argument('-w', '--weak', action='store_const', const='weak', dest='strength', help='Create a shorter token')

    g.add_argument('--url', default='http://anaconda.org', help='The url of the application that will use this token')
    g.add_argument('--max-age', type=int, help='The maximum age in seconds that this token will be valid for')
    g.add_argument('-s', '--scopes', action='append', help=('Scopes for token. '
                                                                 'For example if you want to limit this token to conda downloads only you would use '
                                                                 '--scopes "repo conda:download"'), default=[])

    g.add_argument('--out', default=sys.stdout,
                        type=FileType('w'))

    group = parser.add_argument_group("actions")
    group = group.add_mutually_exclusive_group(required=True)
    group.add_argument('-x', '--list-scopes', action='store_true', help='list all authentication scopes')
    group.add_argument('-l', '--list', action='store_true', help='list all user authentication tokens')
    group.add_argument('-r', '--remove', metavar='NAME', nargs='+', help='remove authentication tokens')
    group.add_argument('-c', '--create', action='store_true', help='Create an authentication token')
    group.add_argument('-i', '--info', '--current-info', dest='info',
                       action='store_true', help='Show information about the current authentication token')

    parser.set_defaults(main=main)
