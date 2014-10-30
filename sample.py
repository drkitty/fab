#!/usr/bin/env python3


from fab import Target


if __name__ == '__main__':
    t = Target(
        'x', cmd=['cat a b >x'],
        dep=[
            Target('a', cmd=['echo line one >a']),
            Target('b', cmd=['echo line two >b']),
        ]
    )

    t.build()
