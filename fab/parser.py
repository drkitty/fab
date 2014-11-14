from contextlib import contextmanager
from itertools import tee
from traceback import print_stack

from . import DEBUG


class Invalid(Exception):
    pass


class End(Exception):
    pass


class Stream(object):
    def __init__(self, iterable=None):
        self.b = []  # backtrackable chars
        self.q = []  # queue
        if iterable is None:
            self.i = None
        else:
            self.i = iter(iterable)

    def next(self):
        return next(self.i, None)

    def get(self):
        if self.q:
            c = self.q.pop(0)
        else:
            c = self.next()
        if c is not None:
            self.b.append(c)
        if DEBUG:
            print("... get {}".format(repr(c)))
        return c

    def __enter__(self):
        dup = self.__class__()
        dup.i = self.i
        dup.q = self.q
        self.child = dup
        return dup

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type in (End, Invalid):
            if DEBUG:
                print("... unget '{}'".format(''.join(self.child.b)))
            self.q.extend(self.child.b)


class FileStream(Stream):
    def __init__(self, filename=None):
        if filename is None:
            f = None
        else:
            f = open(filename, 'r')
        super().__init__(f)


    def fetch_line(self):
        line = next(self.i, None)
        if DEBUG:
            print("... fetch line {}".format(repr(line)))
        if line is None:
            return
        for c in line:
            self.q.append(c)

    def next(self):
        self.fetch_line()
        return self.q.pop(0)


def parse(s, *fs, exc=Invalid):
    for f in fs:
        try:
            with s as ss:
                return f(ss)
        except Invalid:
            pass
    raise exc()


def char(cond):
    def inner(s):
        c = s.get()
        if c is None or not cond(c):
            raise Invalid()
        return c
    return inner
