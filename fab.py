import re
import subprocess
import shlex
from os import stat


def get_mtime(name):
    try:
        return stat(name).st_mtime
    except FileNotFoundError:
        return None


def pattern_to_re(pattern):
    if pattern.find('%?') != pattern.rfind('%?'):
        raise Exception("Repeated '%?' in pattern not allowed")
    return re.compile(re.escape(pattern).replace(r'\%\?', '([^/]*)') + '$')


class Group(object):
    def __init__(self, *, mods=[], rules=[], parent=None):
        self.mods = mods
        self.rules = rules
        self.parent = parent

    def modify(self, name):
        for mod in self.mods:
            name = mod.modify(name)
        if self.parent:
            name = self.parent.modify(name)
        return name

    def build(self, name):
        name = self.modify(name)

        mtime = get_mtime(self.name)

        for rule in self.rules:
            res = rule.match(name)
            if isinstance(res, str):
                if rule.build(q=res, mtime=mtime):
                    return True
            elif res is True:
                if rule.build(name=name, mtime=mtime):
                    return True

        return mtime is not None


class Mod(object):
    def modify(self, name):
        pass


class Rewrite(Mod):
    def __init__(self, name, name2):
        if '%?' in name:
            self.name = pattern_to_re(name)
        else:
            self.name = name
            if '%?' in name2:
                raise Exception("'%?' not allowed in non-pattern name")

        self.name2 = name2

    def modify(self, name):
        if isinstance(self.name, str):
            if self.name == name:
                return self.name2
        else:
            m = self.name.match(name)
            if m is None:
                return name
            else:
                return self.name2.replace('%?', m.group(0))
