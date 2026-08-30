# Azrienoch

A variable font that multiplexes several axes of control into one
typeface: weight, width, and a sans/serif toggle, with cap-height and
x-height themselves tied to the weight axis rather than to point size or
line height.

This repository previously held [Graduate](https://github.com/etunni/Graduate-Variable-Font),
a 12-axis variable font by Eduardo Tunni that served as this project's
model for how far a single variable font's axis system can go. Azrienoch
replaces it: same ambition for axis versatility, a different letterform
foundation and a narrower, more deliberate set of axes.

## Design

Azrienoch's letterforms, spacing and kerning come from
[Roboto Flex](https://github.com/googlefonts/roboto-flex) (SIL OFL 1.1),
not from a from-scratch drawing. Roboto Flex is real, professionally
hinted and kerned type-design engineering, with nine independent
"parametric" axes controlling stroke weight and vertical proportions
separately from its registered `wght`/`wdth` axes. Azrienoch's own work
is in what it does with that space:

- **Height as a matter of weight.** Roboto Flex deliberately keeps
  weight and height independent -- that's the whole point of exposing
  `YTUC`/`YTLC`/`YTAS`/`YTDE`/`XOPQ`/`YOPQ` as separate axes. Azrienoch
  deliberately does the opposite: its `wght` axis is mapped onto a
  correlated path through that same space (see
  `tools/roboto_source.py::_HEIGHT_AXES_AT_WGHT`), so cap-height,
  x-height and stroke weight all grow together. A heavier Azrienoch
  instance is a genuinely *taller* one, independent of the type size or
  line height the reader chooses.
- **A variable serif axis (`SERF`, 0-100).** Roboto Flex has no serifs.
  `tools/serifs.py` scans one reference instance for short, already-flat
  horizontal stem terminals (round strokes never present one, so bowls
  and curves are naturally skipped) and grows a slab foot on each,
  driven by the `SERF` axis. Azrienoch is sans by default.
- **Automatic, weight/width-aware spacing and kerning.** Advance widths
  and kerning are extracted straight out of Roboto Flex's own `hmtx`
  and (per-master, since it's decompiled from a fully instanced,
  therefore static, `GPOS`) `kern` feature at each of Azrienoch's master
  locations -- see `tools/roboto_source.py::extract_kerning`. That
  inherits Roboto Flex's own tuning: pairs tighten at heavier weights
  and stay legible when condensed, without Azrienoch reimplementing an
  optical-kerning algorithm of its own.
- **A horizontal-terminal design principle.** Roboto Flex's own grotesque
  terminals are already cut flat (horizontal or vertical), not on the
  stroke's own angle -- Azrienoch's slab serifs follow the same rule
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
fonts/variable/Azrienoch-VF.ttf   compiled variable font (build output)
sources/*.ufo                     the 12 (wght x wdth x SERF) UFO masters (build output)
sources/Azrienoch.designspace     the designspace tying the masters together (build output)
third_party/roboto-flex/          vendored Roboto Flex source font + its own OFL.txt
tools/                            the build pipeline (see below)
specimen/                         specimen renders
```

`sources/*.ufo`, `sources/Azrienoch.designspace` and
`fonts/variable/Azrienoch-VF.ttf` are build output, checked in so the
compiled font is usable without running Python -- regenerate them with
the steps below any time `tools/` or `third_party/roboto-flex/` changes.

### `tools/`

- `params.py` -- the axis model: master grid, and the (registered) axis
  definitions.
- `roboto_source.py` -- maps an Azrienoch `(wght, wdth)` onto a point in
  Roboto Flex's axis space, instances the vendored variable font there
  with `fontTools.varLib.instancer`, and extracts glyph outlines,
  advance widths and kerning.
- `serifs.py` -- detects candidate stem feet once from a reference
  instance, then adds the *same* foot contours (by fractional position)
  to every master, sized by that master's own `SERF` value. Every master
  of a glyph gets identical topology this way -- collapsed to a hairline
  at `SERF=0`, grown to a full slab at `SERF=100` -- which is what makes
  the axis interpolate at all rather than failing to compile.
- `ufo_build.py` -- assembles the 12 master UFOs, copying each glyph's
  quadratic outline through unmodified (no curve conversion -- gvar
  already guarantees the same point topology across masters, so nothing
  needs re-fitting; only `serifs.py`'s added rectangles are new points).
- `designspace_build.py` -- writes the `.designspace` and runs
  `fontmake` to compile the variable TTF.
- `geometry.py` -- the rectangle-contour primitive `serifs.py` builds feet
  from.
- `preview.py` -- a matplotlib-based text renderer (from the compiled
  variable font, at any axis location) used for visual QA during
  development; also runnable directly, `python3 -m tools.preview "text" wght wdth SERF out.png`.

## Building

```
pip install -r requirements.txt
python3 -m tools.designspace_build
```

This regenerates `sources/*.ufo`, `sources/Azrienoch.designspace` and
`fonts/variable/Azrienoch-VF.ttf`.

## Known limitations

This is a Core Latin MVP (~88 glyphs: uppercase, lowercase, digits, core
punctuation) -- not full Latin Extended, no other scripts, no named
`fvar` instances, and no `GSUB` features (ligatures, figure styles,
case-sensitive forms) beyond the kerning that is carried over. See
[TODO.md](./TODO.md) for the full, itemized list of what's next.

## License

Azrienoch is licensed under the [SIL Open Font License, Version 1.1](./OFL.txt),
as a Modified Version of Roboto Flex. Roboto Flex's own license and
authors are in `third_party/roboto-flex/OFL.txt`.
