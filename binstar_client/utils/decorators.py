# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
from collections import Hashable
from types import GeneratorType

from six import wraps


def memoize(func):
    """
    Decorator to cause a function to cache it's results for each combination of
    inputs and return the cached result on subsequent calls.  Does not support
    named arguments or arg values that are not hashable.

    >>> @memoize
    ... def foo(x):
    ...     print('running function with', x)
    ...     return x+3
    ...
    >>> foo(10)
    running function with 10
    13
    >>> foo(10)
    13
    >>> foo(11)
    running function with 11
    14
    >>> @memoize
    ... def range_tuple(limit):
    ...     print('running function')
    ...     return tuple(i for i in range(limit))
    ...
    >>> range_tuple(3)
    running function
    (0, 1, 2)
    >>> range_tuple(3)
    (0, 1, 2)
    >>> @memoize
    ... def range_iter(limit):
    ...     print('running function')
    ...     return (i for i in range(limit))
    ...
    >>> range_iter(3)
    Traceback (most recent call last):
    TypeError: Can't memoize a generator or non-hashable object!
    """
    func._result_cache = {}  # pylint: disable-msg=W0212

    @wraps(func)
    def _memoized_func(*args, **kwargs):
        key = (args, tuple(sorted(kwargs.items())))
        if key in func._result_cache:  # pylint: disable-msg=W0212
            return func._result_cache[key]  # pylint: disable-msg=W0212
        else:
            result = func(*args, **kwargs)
            if isinstance(result, GeneratorType) or not isinstance(result, Hashable):
                raise TypeError("Can't memoize a generator or non-hashable object!")
            func._result_cache[key] = result  # pylint: disable-msg=W0212
            return result

    return _memoized_func
