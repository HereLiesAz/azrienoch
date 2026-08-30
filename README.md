# Multiplex

A variable font that multiplexes several axes of control into one
typeface: weight, width, and a sans/serif toggle, with cap-height and
x-height themselves tied to the weight axis rather than to point size or
line height.

This repository previously held [Graduate](https://github.com/etunni/Graduate-Variable-Font),
a 12-axis variable font by Eduardo Tunni that served as this project's
model for how far a single variable font's axis system can go. Multiplex
replaces it: same ambition for axis versatility, a different letterform
foundation and a narrower, more deliberate set of axes.

## Design

Multiplex's letterforms, spacing and kerning come from
[Roboto Flex](https://github.com/googlefonts/roboto-flex) (SIL OFL 1.1),
not from a from-scratch drawing. Roboto Flex is real, professionally
hinted and kerned type-design engineering, with nine independent
"parametric" axes controlling stroke weight and vertical proportions
separately from its registered `wght`/`wdth` axes. Multiplex's own work
is in what it does with that space:

- **Height as a matter of weight.** Roboto Flex deliberately keeps
  weight and height independent -- that's the whole point of exposing
  `YTUC`/`YTLC`/`YTAS`/`YTDE`/`XOPQ`/`YOPQ` as separate axes. Multiplex
  deliberately does the opposite: its `wght` axis is mapped onto a
  correlated path through that same space (see
  `tools/roboto_source.py::_HEIGHT_AXES_AT_WGHT`), so cap-height,
  x-height and stroke weight all grow together. A heavier Multiplex
  instance is a genuinely *taller* one, independent of the type size or
  line height the reader chooses.
- **A variable serif axis (`SERF`, 0-100).** Roboto Flex has no serifs.
  `tools/serifs.py` scans one reference instance for short, already-flat
  horizontal stem terminals (round strokes never present one, so bowls
  and curves are naturally skipped) and grows a slab foot on each,
  driven by the `SERF` axis. Multiplex is sans by default.
- **Automatic, weight/width-aware spacing and kerning.** Advance widths
  and kerning are extracted straight out of Roboto Flex's own `hmtx`
  and (per-master, since it's decompiled from a fully instanced,
  therefore static, `GPOS`) `kern` feature at each of Multiplex's master
  locations -- see `tools/roboto_source.py::extract_kerning`. That
  inherits Roboto Flex's own tuning: pairs tighten at heavier weights
  and stay legible when condensed, without Multiplex reimplementing an
  optical-kerning algorithm of its own.
- **A horizontal-terminal design principle.** Roboto Flex's own grotesque
  terminals are already cut flat (horizontal or vertical), not on the
  stroke's own angle -- Multiplex's slab serifs follow the same rule
  (they're rectangles, by construction), and no reshaping was needed to
  bring the inherited letterforms into line with it.

The letterform character itself aims for an analytical neo-grotesque:
Roboto Flex's own modern, systematic proportions, read with some of
Helvetica/Akzidenz-Grotesk's rational flat-terminal directness.

## Axes

| Axis | Tag | Range | Default |
|---|---|---|---|
| Weight | `wght` | 100-900 | 400 |
| Width | `wdth` | 75-100 | 100 |
| Serif | `SERF` | 0-100 | 0 |

## Repository layout

```
fonts/variable/Multiplex-VF.ttf   compiled variable font (build output)
sources/*.ufo                     the 12 (wght x wdth x SERF) UFO masters (build output)
sources/Multiplex.designspace     the designspace tying the masters together (build output)
third_party/roboto-flex/          vendored Roboto Flex source font + its own OFL.txt
tools/                            the build pipeline (see below)
specimen/                         specimen renders
```

`sources/*.ufo`, `sources/Multiplex.designspace` and
`fonts/variable/Multiplex-VF.ttf` are build output, checked in so the
compiled font is usable without running Python -- regenerate them with
the steps below any time `tools/` or `third_party/roboto-flex/` changes.

### `tools/`

- `params.py` -- the axis model: master grid, and the (registered) axis
  definitions.
- `roboto_source.py` -- maps a Multiplex `(wght, wdth)` onto a point in
  Roboto Flex's axis space, instances the vendored variable font there
  with `fontTools.varLib.instancer`, and extracts glyph outlines,
  advance widths and kerning.
- `qu2cu_exact.py` -- a deterministic (non-adaptive) quadratic-to-cubic
  conversion pen. This matters more than it sounds: fontTools' own
  adaptive `Qu2CuPen` fits cubics to an error tolerance and can pick a
  *different number* of curve segments for two instances of what gvar
  guarantees is the same point topology -- silently breaking
  interpolation compatibility between masters. Degree-elevating each
  quadratic segment 1:1 avoids that.
- `serifs.py` -- detects candidate stem feet once from a reference
  instance, then adds the *same* foot contours (by fractional position)
  to every master, sized by that master's own `SERF` value. Every master
  of a glyph gets identical topology this way -- collapsed to a hairline
  at `SERF=0`, grown to a full slab at `SERF=100` -- which is what makes
  the axis interpolate at all rather than failing to compile.
- `ufo_build.py` -- assembles the 12 master UFOs.
- `designspace_build.py` -- writes the `.designspace` and runs
  `fontmake` to compile the variable TTF.
- `geometry.py`, `preview.py` -- shared primitives and a matplotlib-based
  glyph previewer used during development.

## Building

```
pip install -r requirements.txt
python3 -m tools.designspace_build
```

This regenerates `sources/*.ufo`, `sources/Multiplex.designspace` and
`fonts/variable/Multiplex-VF.ttf`.

## Known limitations

- **Core Latin MVP glyph set.** Uppercase, lowercase, digits and a core
  punctuation set (~88 glyphs) -- not full Latin Extended, and no other
  scripts. `tools/ufo_build.py::CORE_CHARS` is the place to grow it.
- **Three `wght` samples per axis path.** The height/stroke correlation
  is only anchored at wght 100/400/900; a fourth intermediate master
  would let that curve bend more deliberately.
- **`GRAD`, `opsz` and `slnt` are fixed**, not exposed as Multiplex axes,
  though the underlying Roboto Flex source supports all three.

## License

Multiplex is licensed under the [SIL Open Font License, Version 1.1](./OFL.txt),
as a Modified Version of Roboto Flex. Roboto Flex's own license and
authors are in `third_party/roboto-flex/OFL.txt`.
