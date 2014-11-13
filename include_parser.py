#!/usr/bin/env python3

from parser import char, End, FileStream, Invalid, parse


class Header(object):
    def __init__(self, name, depth):
        self.name = name
        self.depth = depth
        self.parent = None
        self.children = []

    def __repr__(self):
        return "<Header: {}>".format(self.name)

    def add_child(self, child):
        child.parent = self
        self.children.append(child)


def line(s):
    dots = 0
    while True:
        c = s.get()
        if c == '.':
            dots += 1
        elif c == ' ':
            break
        else:
            raise Invalid()
    name = ''
    while True:
        c = s.get()
        if c == '\n':
            break
        name += c
    return Header(name, dots)


def list(s):
    headers = []
    try:
        while True:
            headers.append(parse(s, line, exc=End))
    except End:
        pass

    root = Header('', 0)
    depth = 0
    prev = root
    for curr in headers:
        for i in range(prev.depth - curr.depth + 1):
            prev = prev.parent
        prev.add_child(curr)
        prev = curr

    return root


s = FileStream('includes')
x = list(s)
