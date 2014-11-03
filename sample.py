from fab import Group, Rewrite, Rule


g = Group(
    mods=[
        Rewrite('%?.o', '.obj/%?.o'),
    ],
    rules=[
        Rule('x', ('touch x',), dep=('a.c', 'b.c')),
        Rule('%?.o', ('touch %?.o',), dep=('%?.c',), rules=[
            Rule('%?.c', idep=('%?.h',)),
        ]),
    ],
)

g.build('a.c')
