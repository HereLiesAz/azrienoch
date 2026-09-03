# Axes

| Axis | Tag | Range | Default |
|---|---|---|---|
| Weight | `wght` | 180-900 | 400 |
| Width | `wdth` | 75-100 | 100 |
| Serif | `SERF` | 0-100 | 0 |
| Grade | `GRAD` | -50-50 | 0 |

`wght` and `wdth` are registered OpenType axes; `SERF` and `GRAD` are
custom (uppercase-tagged) axes, `GRAD` matching Roboto Flex's own
`GRAD` convention. See [`design.md`](./design.md) for what each axis
actually does to the letterforms, and `tools/params.py` for the master
grid these ranges expand into (currently 4 `wght` x 2 `wdth` x 2
`SERF` x 3 `GRAD` = 48 masters).

## Deliberately not axes

Two of Roboto Flex's registered axes are fixed rather than exposed, on
purpose rather than by omission:

- **`opsz` (optical size)** would let letterforms open up at small
  sizes and tighten at large ones -- exactly the kind of size-driven
  shape change "height as a matter of weight, not of font size"
  (`design.md`) exists to opt out of. Exposing it would reintroduce,
  through a side door, the coupling between point size and proportions
  the `wght` axis is built to replace. Fixed at Roboto Flex's own
  default (24).
- **`slnt` (slant)** is fixed at 0 (upright). Roboto Flex's own `slnt`
  axis only reaches -10 degrees at its extreme -- a barely-there lean,
  not a real italic -- and a genuine italic needs redrawn letterforms
  (different 'a'/'e'/'f' constructions, not just a shear), which is
  out of scope here. Azrienoch has no italic.

Both are trimmed out of the vendored Roboto Flex source entirely
(`fontTools.varLib.instancer`, instanced out at their fixed defaults
and dropped) rather than just left unexposed, which shrinks the
vendored file from ~1.78 MB to ~0.68 MB with no behavior change --
`tools/roboto_source.py::roboto_location` always requested those same
fixed values from the untrimmed font anyway.

See [`IDEAS.md`](./IDEAS.md) for axes that have come up as possible
future directions without being decided on.
