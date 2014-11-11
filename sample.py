from fab import Group, Rewrite, Rule


g = Group(
    mods=[
        Rewrite('%?.o', '.obj/%?.o'),
    ],
    rules=[
        Rule('x', ('touch x',), deps=['a.o', 'b.o']),
        Rule('%?.o', ('touch %@',), deps=['%?.c'], child=Group(
            rules=[Rule('%?.c', ideps=['%?.h'])]
        )),
    ],
)

g.setup()
g.build('x')
