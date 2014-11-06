from fab import Group, Rewrite, Rule


g = Group(
    mods=[
        Rewrite('%?.o', '.obj/%?.o'),
    ],
    rules=[
        Rule('x', ('touch x',), deps=('a.c', 'b.c')),
        Rule('%?.o', ('touch %?.o',), deps=('%?.c',), rules=[
            Rule('%?.c', ideps=('%?.h',)),
        ]),
    ],
)

g.build('a.o')
