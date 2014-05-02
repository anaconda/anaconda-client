'''
Created on May 2, 2014

@author: sean
'''

from binstar_client.utils import jencode
from binstar_client.errors import BinstarError

class ChannelsMixin(object):
    def _mk_channel_url(self, channel, owner, package=None, version=None, filename=None):
        url = '%s/channel/%s/%s' % (self.domain, channel, owner)
        if package:
            url += '/%s' % package
            if version:
                url += '/%s' % version
                if filename:
                    url += '/%s' % filename
            elif filename:
                raise BinstarError("version can not be none if filename is given")
        elif version or filename:
            raise BinstarError("package can not be none if version or filename is given")

    def add_channel(self, channel, owner, package=None, version=None, filename=None):
        '''
        Add a channel to the specified files
        
        :param channel: channel to add
        :param owner: The user to add the channel to (all files of all packages for this user)
        :param package: The package to add the channel to (all files in this package)
        :param version: The version to add the channel to (all files in this version of the package)
        :param filename: The exact file to add the channel to
        
        '''
        url = self._mk_channel_url(channel, owner, package, version, filename)
        res = self.session.post(url)
        self._check_response(res, [201])

    def remove_channel(self, channel, owner, package=None, version=None, filename=None):
        '''
        Remove a channel from the specified files
        
        :param channel: channel to remove
        :param owner: The user to remove the channel from (all files of all packages for this user)
        :param package: The package to remove the channel from (all files in this package)
        :param version: The version to remove the channel to (all files in this version of the package)
        :param filename: The exact file to remove the channel from
        
        '''
        url = self._mk_channel_url(channel, owner, package, version, filename)
        res = self.session.delete(url)
        self._check_response(res, [201])

    def copy_channel(self, channel, owner, to_channel):
        '''
        Tag all files in channel <channel> also as channel <to_channel> 
        
        :param channel: channel to copy
        :param owner: Perform this operation on all packages of this user
        :param to_channel: Destination name (may be a channel that already exists)
        
        '''
        url = '%s/copy-channel/%s/%s/%s' % (self.domain, channel, owner, to_channel)
        res = self.session.delete(url)
        self._check_response(res, [201])

