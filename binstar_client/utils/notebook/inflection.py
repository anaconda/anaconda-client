# -*- coding: utf-8 -*-
import re
import unicodedata
"""
    parameterize method, same as RoR
    Taken from https://github.com/jpvanhal/inflection
"""


def parameterize(string, separator='-'):
    """
    Replace special characters in a string so that it may be used as part of a
    'pretty' URL.
    Example::
        >>> parameterize(u"Donald E. Knuth")
        'donald-e-knuth'
    """
    string = transliterate(string)
    # Turn unwanted chars into the separator
    string = re.sub(r"(?i)[^a-z0-9\-_]+", separator, string)
    if separator:
        re_sep = re.escape(separator)
        # No more than one of the separator in a row.
        string = re.sub(r'%s{2,}' % re_sep, separator, string)
        # Remove leading/trailing separator.
        string = re.sub(r"(?i)^%(sep)s|%(sep)s$" % {'sep': re_sep}, '', string)

    return string.lower()


def transliterate(string):
    """
    Replace non-ASCII characters with an ASCII approximation. If no
    approximation exists, the non-ASCII character is ignored. The string must
    be ``unicode``.
    Examples::
        >>> transliterate(u'älämölö')
        u'alamolo'
        >>> transliterate(u'Ærøskøbing')
        u'rskbing'
    """
    try:
        normalized = unicodedata.normalize('NFKD', unicode(string))
    except NameError:
        normalized = unicodedata.normalize('NFKD', string)
    return normalized.encode('ascii', 'ignore').decode('ascii')
