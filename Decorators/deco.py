#!/usr/bin/env python
# -*- coding: utf-8 -*-

from functools import update_wrapper
from functools import wraps


def disable(func):
    '''
    Disable a decorator by re-assigning the decorator's name
    to this function. For example, to turn off memoization:

    >>> memo = disable

    '''
    return func


def decorator(d):
    '''
    Decorate a decorator so that it inherits the docstrings
    and stuff from the function it's decorating.
    '''
    #@wraps(d)
    def _inner(func):
        return update_wrapper(d(func), func)
    update_wrapper(_inner, d)
    return d



def countcalls(func):
    '''Decorator that counts calls made to the function decorated.'''
    @wraps(func)
    def wrapper(*args, **kwargs):
        wrapper.calls += 1
        return func(*args, **kwargs)
    wrapper.calls = 0
    return wrapper

def memo(func):
    '''
    Memoize a function so that it caches all return values for
    faster future lookups.
    '''
    memo_calls = {}
    @wraps(func)
    def helper(*x, **y):
        key = tuple(x) if not y else tuple([tuple(x), tuple(y.items())])
        if key not in memo_calls:
            memo_calls[key] = func(*x, **y)
            print "added cache"
        return memo_calls[key]
    return helper



def n_ary(func):
    '''
    Given binary function f(x, y), return an n_ary function such
    that f(x, y, z) = f(x, f(y,z)), etc. Also allow f(x) = x.
    '''
    def n_ary_f(x, *args):
        return x if not args else func(x, n_ary_f(*args))
    return n_ary_f


def decorator_maker(decorator_arg1, decorator_arg2):
    print "Decorator make args:", decorator_arg1, decorator_arg2
    def decorator(func):
        print "Decorator args:", decorator_arg1, decorator_arg2
        def wrapper(*args, **kwargs) :
            print "Wrapper args:", args, kwargs
            return func(*args, **kwargs)

        return wrapper
    return decorator



def trace(delimiter):
    '''Trace calls made to function decorated.

    @trace("____")
    def fib(n):
        ....

    >>> fib(3)
     --> fib(3)
    ____ --> fib(2)
    ________ --> fib(1)
    ________ <-- fib(1) == 1
    ________ --> fib(0)
    ________ <-- fib(0) == 1
    ____ <-- fib(2) == 2
    ____ --> fib(1)
    ____ <-- fib(1) == 1
     <-- fib(3) == 3

    '''


    def wrapped(func):
        @wraps(func)
        def inner(*args):
            called_func = '{}({})'.format(func.__name__, ', '.join(map(repr, args)))
            print('{}--> {}'.format(trace.level*delimiter, called_func))
            trace.level += 1
            try:
                result = func(*args)
                print('{}<-- {} == {}'.format(
                    (trace.level - 1)*delimiter, called_func, result))
            finally:
                trace.level -= 1
            return result
        trace.level = 0
        return inner
    return wrapped




@memo
@countcalls
@n_ary
def foo(a, b):
    return a + b


@countcalls
@memo
@n_ary
def bar(a, b):
    return a * b


@countcalls
@trace("####")
@memo
def fib(n):
    """Some doc"""
    return 1 if n <= 1 else fib(n-1) + fib(n-2)


def main():
    print foo(4, 3)
    print foo(4, 3, 2)
    print foo(4, 3)
    print "foo was called", foo.calls, "times"

    print bar(4, 3)
    print bar(4, 3, 2)
    print bar(4, 3, 2, 1)
    print "bar was called", bar.calls, "times"

    print fib.__doc__
    fib(3)
    print fib.calls, 'calls made'


if __name__ == '__main__':
    main()
