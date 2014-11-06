import re
import subprocess
import shlex
from os import path, stat


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
    parent = None

    def __init__(self, *, mods=[], rules=[]):
        for mod in mods:
            mod.parent = self
        self.mods = mods
        for rule in rules:
            rule.parent = self
        self.rules = rules

    def search(self, name):
        for rule in self.rules:
            if isinstance(rule.name, str):
                if rule.name == name:
                    return rule
            else:
                if rule.name.match(name):
                    return rule
        if self.parent:
            return self.parent.search(name)

    def modify(self, name):
        for mod in self.mods:
            name = mod.modify(name)
        if self.parent:
            name = self.parent.modify(name)
        return name

    def build(self, name):
        name = self.modify(name)

        for rule in self.rules:
            print("Looking at rule for '{}'".format(rule.name))
            mtime = rule.build(name)
            if mtime:
                return mtime


class Rule(Group):
    def __init__(self, name, cmds=(), deps=(), ideps=(), **kwargs):
        super().__init__(**kwargs)

        if '%?' in name:
            self.name = pattern_to_re(name)
        else:
            self.name = name
        self.cmds = cmds
        self.deps = deps
        self.ideps = ideps

    def __repr__(self):
        if isinstance(self.name, str):
            return "<Rule: '{}'>".format(self.name)
        else:
            return "<Rule: '{}'>".format(self.name.pattern)

    def build(self, name):
        """Build `name` if possible and necessary

        Returns the mtime of `name` if it's now up to date, or None otherwise.
        """

        if isinstance(self.name, str):
            if self.name != name:
                return None
            deps = self.deps
            ideps = self.ideps
        else:
            m = self.name.match(name)
            if m is None:
                return None
            q = m.group(0)

            deps = list(self.deps)
            for i in range(len(deps)):
                deps[i] = deps[i].replace('%?', q)
            ideps = list(self.ideps)
            for i in range(len(ideps)):
                ideps[i] = ideps[i].replace('%?', q)

        deps = filter(None, (self.search(dep) for dep in deps))
        ideps = filter(None, (self.search(idep) for idep in ideps))

        mtime = get_mtime(name)

        stale = mtime is None

        for dep in deps:
            print("Looking at dep '{}'".format(dep.name))
            dep_mtime = dep.build(name)
            if dep_mtime and dep_mtime > mtime:
                stale = True

        if not stale:
            for idep in ideps:
                print("Looking at idep '{}'".format(idep.name))
                if get_mtime(idep):
                    stale = True
                    break

        if stale:
            self.run_commands()
            mtime = get_mtime(name)

        return mtime

    def run_commands(self, q=None):
        for cmd in self.cmds:
            if q:
                cmd = cmd.replace('%?', q)
            if subprocess.call(shlex.split(cmd)) > 0:
                raise Exception("Command '{}' failed".format(cmd))


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
            if m is not None:
                return self.name2.replace('%?', m.group(0))
        return name


class AddDir(Mod):
    def __init__(self, name, directory):
        if '%?' in name:
            self.name = pattern_to_re(name)
        else:
            self.name = name
        self.dir = directory

    def modify(self, name):
        if isinstance(self.name, str):
            if self.name == name:
                return path.join(self.dir, name)
        else:
            if self.name.match(name):
                return path.join(self.dir, name)
        return name
