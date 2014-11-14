import re
import subprocess
import shlex
from os import path, stat

from . import DEBUG


def get_mtime(name):
    try:
        return stat(name).st_mtime
    except FileNotFoundError:
        return 0


def pattern_to_re(pattern):
    if pattern.find('%?') != pattern.rfind('%?'):
        raise Exception("Repeated '%?' in pattern not allowed")
    return re.compile(re.escape(pattern).replace(r'\%\?', '([^/]*)') + '$')


class Group(object):
    parent = None

    def __init__(self, *, mods=[], rules=[]):
        self.mods = mods
        self.rules = rules
        for rule in self.rules:
            rule.parent = self

    def setup(self, mods=None):
        if mods:
            mods = mods + self.mods  # copy
        else:
            mods = self.mods[:]  # copy
        for rule in self.rules:
            rule.setup(self.mods)

    def search(self, name, *, ascend=True):
        for rule in self.rules:
            if rule.regex:
                if rule.regex.match(name):
                    return rule
            else:
                if rule.name == name:
                    return rule
        if self.parent:
            return self.parent.search(name)

    def modify(self, x):
        for mod in self.mods:
            mod.modify(x)
        if self.parent:
            self.parent.modify(x)

    def build(self, name):
        for rule in self.rules:
            mtime = rule.build(name)
            if mtime:
                return mtime


class Rule(Group):
    def __init__(self, name, cmds=(), deps=(), ideps=(), child=None):
        self.name = name
        self.cmds = cmds
        self.deps = deps
        self.ideps = ideps
        self.child = child

    def __repr__(self):
        return "<Rule: '{}'>".format(self.name)

    def setup(self, mods):
        for mod in mods:
            mod.modify(self)
        self.create_regex()
        if self.child:
            self.child.setup(mods)

    def search(self, name, *, ascend=True):
        if self.child:
            rule = self.child.search(name, ascend=False)
            if rule:
                return rule
        if ascend and self.parent:
            return self.parent.search(name)
        return None

    def create_regex(self):
        if '%?' in self.name:
            self.regex = pattern_to_re(self.name)
        else:
            self.regex = None

    def build(self, name):
        """Build `name` if possible and necessary

        Returns the mtime of `name` if it's now up to date, or 0 otherwise.
        """

        if DEBUG:
            print("Considering building '{}' with {}".format(name, repr(self)))

        if self.regex:
            m = self.regex.match(name)
            if not m:
                return None
            q = m.group(1)

            deps = list(self.deps)
            for i in range(len(deps)):
                deps[i] = deps[i].replace('%?', q)
            ideps = list(self.ideps)
            for i in range(len(ideps)):
                ideps[i] = ideps[i].replace('%?', q)
        else:
            if self.name != name:
                return None
            deps = self.deps
            ideps = self.ideps

        mtime = get_mtime(name)
        fake_mtime = 0

        stale = not mtime

        for dep in deps:
            dep_rule = self.search(dep)
            if not dep_rule:
                return None
            if DEBUG:
                print("Looking at dep '{}' of {}".format(dep, repr(self)))
            dep_mtime = dep_rule.build(dep)
            if not dep_mtime:
                return 0
            if dep_mtime > mtime:
                stale = True

        if stale:
            self.run_commands(name)
            mtime = get_mtime(name)
        else:
            for idep in ideps:
                if DEBUG:
                    print("Looking at idep '{}' of {}".format(
                        idep, repr(self)))
                idep_mtime = get_mtime(idep)
                if idep_mtime > mtime:
                    mtime = max(mtime, idep_mtime)

        return mtime

    def run_commands(self, name):
        for cmd in self.cmds:
            if name:
                cmd = cmd.replace('%@', name)
            print(cmd)
            if subprocess.call(shlex.split(cmd), posix=True) > 0:
                raise Exception("Command '{}' failed".format(cmd))


class Mod(object):
    def modify(self, x):
        raise Exception('Not implemented')

    def apply(self, x, *, func):
        x.name = func(x.name)
        for i in range(len(x.deps)):
            x.deps[i] = func(x.deps[i])
        for i in range(len(x.ideps)):
            x.ideps[i] = func(x.ideps[i])


class Rewrite(Mod):
    def __init__(self, name, name2):
        self.name = name
        if '%?' in name:
            self.regex = pattern_to_re(name)
        else:
            if '%?' in name2:
                raise Exception("'%?' not allowed in non-pattern name")
            self.regex = None

        self.name2 = name2

    def __repr__(self):
        return '<Rewrite: "{}" -> "{}">'.format(self.name, self.name2)

    def modify(self, x):
        if self.regex:
            def m(s):
                h = self.regex.match(s)
                if h:
                    return self.name2.replace('%?', h.group(1))
                else:
                    return s
        else:
            def m(s):
                if self.name == s:
                    return self.name2
                else:
                    return s

        self.apply(x, func=m)


class AddDir(Mod):
    def __init__(self, name, directory):
        self.name = name
        if '%?' in name:
            self.regex = pattern_to_re(name)
        else:
            self.regex = None
        self.dir = directory

    def modify(self, x):
        if self.regex:
            def m(s):
                if self.regex.match(s) == s:
                    return path.join(self.dir, s)
                else:
                    return s
        else:
            def m(s):
                if self.name == s:
                    return path.join(self.dir, s)
                else:
                    return s

        self.apply(x, func=m)
