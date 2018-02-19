from __future__ import unicode_literals

import codecs
import logging

from io import BytesIO, StringIO

import six
import requests

from requests.packages.urllib3.filepost import choose_boundary, iter_fields

logger = logging.getLogger('binstar.requests_ext')


def encode_multipart_formdata_stream(fields, boundary=None):
    """
    Encode a dictionary of ``fields`` using the multipart/form-data MIME format.

    :param fields:
        Dictionary of fields or list of (key, value) or (key, value, MIME type)
        field tuples.  The key is treated as the field name, and the value as
        the body of the form-data bytes. If the value is a tuple of two
        elements, then the first element is treated as the filename of the
        form-data section and a suitable MIME type is guessed based on the
        filename. If the value is a tuple of three elements, then the third
        element is treated as an explicit MIME type of the form-data section.

        Field names and filenames must be unicode.

    :param boundary:
        If not specified, then a random boundary will be generated using
        :func:`mimetools.choose_boundary`.
    """
    body = []

    def body_write(item):
        if isinstance(item, six.binary_type):
            item = BytesIO(item)
        elif isinstance(item, six.text_type):
            item = StringIO(item)
        body.append(item)

    body_write_encode = lambda item: body.append(BytesIO(item.encode('utf-8')))

    if boundary is None:
        boundary = choose_boundary()

    for fieldname, value in iter_fields(fields):
        body_write_encode('--%s\r\n' % (boundary))

        if isinstance(value, tuple):
            if len(value) == 3:
                filename, data, content_type = value
            else:
                filename, data = value
                from mimetypes import guess_type
                content_type, _ = guess_type(filename)
                if content_type is None:
                    content_type = 'application/octet-stream'
            body_write_encode('Content-Disposition: form-data; name="%s"; '
                              'filename="%s"\r\n' % (fieldname, filename))
            body_write_encode('Content-Type: %s\r\n\r\n' %
                              (content_type,))
        else:
            data = value
            body_write_encode('Content-Disposition: form-data; name="%s"\r\n'
                               % (fieldname))
            body_write(b'\r\n')

        if isinstance(data, six.integer_types):
            data = six.text_type(data)  # Backwards compatibility

        if isinstance(data, six.text_type):
            body_write_encode(data)
        else:
            body_write(data)

        body_write(b'\r\n')

    body_write_encode('--%s--\r\n' % (boundary))

    content_type = 'multipart/form-data; boundary=%s' % (boundary)

    return body, content_type


class MultiPartIO(object):
    def __init__(self, body, callback=None):
        self.to_read = body
        self.have_read = []
        self._total = 0
        self.callback = callback

    def read(self, n= -1):
        if self.callback:
            self.callback(self.tell(), self._total)

        if n == -1:
            return b''.join(fd.read() for fd in self.to_read)

        if not self.to_read:
            return b''

        while self.to_read:
            data = self.to_read[0].read(n)

            if data:
                return data

            fd = self.to_read.pop(0)
            self.have_read.append(fd)

        return b''

    def tell(self):
        cursor = sum(fd.tell() for fd in self.have_read)
        if self.to_read:
            cursor += self.to_read[0].tell()
        return cursor

    def seek(self, pos, mode=0):
        assert pos == 0
        if mode is 0:
            self.to_read = self.have_read + self.to_read
            self.have_read = []
            [fd.seek(pos, mode) for fd in self.to_read]
            self.cursor = 0

        elif mode is 2:
            self.have_read = self.have_read + self.to_read
            self.to_read = []
            [fd.seek(pos, mode) for fd in self.have_read]
            self._total = self.tell()


def stream_multipart(data, files=None, callback=None):
    from itertools import chain
    if files:
        fields = chain(iter_fields(data), iter_fields(files))
    else:
        fields = data

    body, content_type = encode_multipart_formdata_stream(fields)
    data = MultiPartIO(body, callback=callback)
    headers = {'Content-Type':content_type}
    return data, headers


class NullAuth(requests.auth.AuthBase):
    """force requests to ignore the ``.netrc``

    Some sites do not support regular authentication, but we still
    want to store credentials in the ``.netrc`` file and submit them
    as form elements. Without this, requests would otherwise use the
    .netrc which leads, on some sites, to a 401 error.

    https://github.com/kennethreitz/requests/issues/2773

    Use with::

        requests.get(url, auth=NullAuth())
    """
    def __call__(self, r):
        return r
