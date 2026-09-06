# Axes

| Axis | Tag | Range | Default |
|---|---|---|---|
| Weight | `wght` | 100-900 | 400 |
| Width | `wdth` | 75-100 | 100 |
| Serif | `SERF` | 0-100 | 0 |
| Grade | `GRAD` | -50-50 | 0 |

`wght` and `wdth` are registered OpenType axes; `SERF` and `GRAD` are
custom (uppercase-tagged) axes. See [`design.md`](./design.md) for what
each axis actually does to the letterforms, and `tools/params.py` for
the master grid these ranges expand into (3 `wght` x 2 `wdth` x 2
`SERF` x 3 `GRAD` = 36 masters).

## No `opsz`/`slnt`

Jost, this project's own donor font, doesn't have an optical-size or
slant axis to begin with -- there's nothing to trim or fix at a
default, unlike a donor that ships them natively. A genuine italic
would need redrawn letterforms (different 'a'/'e'/'f' constructions,
not just a shear), which is out of scope here. Azrienoch has no italic.

See [`IDEAS.md`](./IDEAS.md) for axes that have come up as possible
future directions without being decided on.
