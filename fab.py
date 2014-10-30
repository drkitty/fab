import subprocess
import shlex
from os import stat


class Target(object):
    def __init__(self, name, *, cmd=[], dep=[], idep=[], children=[]):
        self.name = name
        self.cmd = cmd
        self.dep = dep
        self.idep = idep
        self.children = children

    @property
    def mtime(self):
        try:
            return stat(self.name).st_mtime
        except FileNotFoundError:
            return None

    def build(self, *, mtime=None):
        stale = False

        if mtime is None:
            mtime = self.mtime
            if mtime is None:
                stale = True

        for d in self.dep:
            d_mtime = d.mtime
            if d_mtime is None or (mtime is not None and d_mtime > mtime):
                d.build(mtime=d_mtime)
                stale = True

        if not stale:
            for i in self.idep:
                if i.mtime > mtime:
                    stale = True
                    break

        if stale:
            for line in self.cmd:
                print(line)
                subprocess.call(('bash', '-c', line))
