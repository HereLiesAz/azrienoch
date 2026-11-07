# Axes

| Axis | Tag | Range | Default |
|---|---|---|---|
| Weight | `wght` | 100-900 | 400 |
| Width | `wdth` | 0-100 | 100 |
| Serif | `SERF` | 0-100 | 0 |
| Grade | `GRAD` | -50-50 | 0 |

`wght` and `wdth` are registered OpenType axes; `SERF` and `GRAD` are
custom (uppercase-tagged) axes. See [`design.md`](./design.md) for what
each axis actually does to the letterforms, and `tools/params.py` for
the master grid these ranges expand into (3 `wght` x 3 `wdth` x 2
`SERF` x 3 `GRAD` = 54 masters).

## Width stops

`wdth` has three masters: 100 (Normal), 75 (Condensed) and 0 (Mono).
At 0 every glyph has the same advance (`MONO_ADVANCE`, 620 units) and
kerning is absent; between 0 and 75 the advances, shapes and kerning
blend linearly. The Mono shapes are the Condensed shapes, compressed
where they exceed the cell and centered in it (`tools/monospace.py`).
Zero-advance glyphs (combining marks) keep a zero advance.

## No `opsz`/`slnt`

Jost, this project's own donor font, doesn't have an optical-size or
slant axis to begin with -- there's nothing to trim or fix at a
default, unlike a donor that ships them natively. A genuine italic
would need redrawn letterforms (different 'a'/'e'/'f' constructions,
not just a shear), which is out of scope here. Azrienoch has no italic.
