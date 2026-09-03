# Azrienoch v2

A second, independent build of Azrienoch, living entirely in this
directory. It shares no code with the repository root's existing
pipeline (`tools/`, `sources/`, `fonts/`). Nothing at the root was
touched or deleted to make room for this.

## Where the letterforms come from

Glyph outlines are copied directly from the vendored
[Jost](https://github.com/indestructible-type/Jost) variable font
(`third_party/jost/`, SIL OFL 1.1 -- license copied to
`third_party/jost/OFL.txt`) -- the same approach the repository root's
own pipeline uses with Roboto Flex, and Jost's own license explicitly
permits exactly this: using, studying, modifying and redistributing the
font. `tools/jost_source.py` instances the vendored font at a given
`wght` via `fontTools.varLib.instancer` and extracts each glyph's real
outline and advance width; `tools/ufo_build.py` copies that data into
Azrienoch's own UFO masters unmodified.

This module's first version (now gone) tried building every letterform
from scratch out of two primitives (a straight polygon, a pair of
concentric ovals) instead of starting from a real drawn typeface. It
compiled and interpolated correctly, but the letterforms it produced
(particularly `n`'s arch and `v`'s diagonal join) didn't hold up --
real type design encodes a lot of judgment calls (a counter's exact
curvature, where a diagonal's thick/thin sides fall) that a from-scratch
geometric formula kept getting wrong in ways that were each individually
fixable but never added up to a typeface. Starting from Jost's actual,
professionally drawn outlines and modifying them from there -- per the
project owner's direction -- is the current approach.

Jost only exposes a `wght` axis (100-900); it has no `wdth` axis to draw
from. `wdth` here is currently a uniform horizontal scale of the
extracted outline and advance width (see `jost_source.py`) -- a
placeholder, not a true optically condensed redraw (a real condensed
cut needs redrawn counters and adjusted spacing, not squashed stems).
Worth revisiting once the modification pass below is underway.

## Design references

- **Jost** (OFL) -- the actual source of every outline in this build
  (see above), not just an influence.
- **Helvetica** -- proprietary (Linotype/Monotype); its rational,
  flat/square-cut terminals and directness (no ball terminals, no
  bracketed serifs, tighter apertures than Jost's own) are the intended
  target of the modification pass on top of Jost's outlines -- nothing
  from Helvetica is traced or extracted, per its license.
- **Heliuum VAR** (205TF, Damien Gautier; commercial/trial license) --
  referenced for its underlying idea, not its shapes: a single font
  built as "a typographic system for mixing and matching," meant to
  spark creative multi-line, multi-weight compositions rather than
  serve one fixed voice. That idea is what `wght`/`wdth` in this module
  are for -- see "Design goal" below.

## Design goal

The brief: a font that makes it *easy* to find creative ways to fit text
together across multiple lines and multiple weights/widths -- lockups,
not just paragraphs. One structural fact serves that directly: **Jost's
own vertical metrics are fixed across its entire `wght` range**
(confirmed directly against the vendored font -- `H`'s bounding box is
`(_, 0, _, 700)` and `o`'s top is ~470-471 at `wght` 100, 400 and 900
alike). A Thin line and a Black line already share a baseline and
x-height with no work on Azrienoch's part, which is exactly what makes
mixed-weight lines stack and align without per-weight compensation.
`tools/params.py`'s `CAP_HEIGHT`/`X_HEIGHT` constants just document
that fact for the build; they don't override anything.

## Axes (current)

| Axis | Tag | Range | Default |
|---|---|---|---|
| Weight | `wght` | 100-900 | 400 |
| Width | `wdth` | 75-100 | 100 |

Masters: the full `wght` x `wdth` grid (`tools/params.py::MASTER_GRID`),
3 weight samples (100/400/900, so `wght` gets a bend rather than one
straight interpolation) x 2 width samples = 6 masters. The default
location (400, 100) is itself one of the six, as a designspace requires.

## Status

62 glyphs -- the basic Latin alphabet (`A`-`Z`, `a`-`z`) and digits
(`0`-`9`) -- copied straight from Jost, unmodified, across all 6
masters. Compiles to a variable TTF with both axes interpolating
cleanly (verified: `fontmake` requires matching point topology across
every master to compile at all, and it does; `tools/preview.py` renders
a sample including `n`/`v`/`a`/`e`/`g`/`s`/`R`/`M` at four axis-space
corners from the compiled font's own `glyf`/`gvar` data).

Not yet done, in order:

- **The Helvetica-inspired modification pass.** Right now this is
  Jost, full stop -- no terminal, aperture, or proportion changes yet.
- **Kerning.** None yet -- needs the full glyph set (now in place) to
  tune real pairs against, which is next now that letterform
  modifications are the remaining open question, not glyph coverage.
- **The `wdth` axis's uniform-scale placeholder** (see above).

## Building

From the repository root:

```
pip install fontTools ufoLib2 fontmake
python3 -m v2.tools.designspace_build
```

Output: `v2/sources/*.ufo`, `v2/sources/AzrienochV2.designspace`,
`v2/fonts/variable/AzrienochV2-VF.ttf`.

Visual QA (renders a sample of glyphs at four axis locations to a PNG,
from the compiled font's own outlines): `python3 -m v2.tools.preview
out.png` (needs `matplotlib`, dev-only, not part of the build).

## Layout

```
v2/tools/jost_source.py        extracts glyph outlines from vendored Jost
v2/tools/params.py             axis model, master grid, vertical metrics
v2/tools/ufo_build.py          builds one UFO per master from jost_source.py
v2/tools/designspace_build.py  writes the designspace, runs fontmake
v2/tools/preview.py            dev-only visual QA render
v2/third_party/jost/           vendored Jost source font + its own OFL.txt
v2/sources/                    build output (UFOs + designspace)
v2/fonts/variable/             build output (compiled variable TTF)
```

## License

Everything in this directory that touches Jost's outline data is a
Modified Version of Jost under the SIL Open Font License, Version 1.1
(`v2/third_party/jost/OFL.txt`; project authors credited there). The
root repository's `OFL.txt` covers the project as a whole.

## Next steps

1. The Helvetica-inspired modification pass: tighter apertures, flatter
   terminals, proportion adjustments -- applied on top of Jost's real
   outlines the way the repository root's `tools/quirks.py` and
   friends modify Roboto Flex's, not as a from-scratch redraw.
2. Kerning: derive pair classes from the full glyph set and tune by eye
   against rendered specimens.
3. A real condensed cut for `wdth`, replacing the uniform-scale
   placeholder, once the modification pass has settled the letterforms
   it would otherwise have to redo.
4. Revisit whether a third axis belongs here for the Heliuum-style
   "mix and match" goal specifically, once the modified letterforms are
   settled enough to know if `wght`/`wdth` alone already deliver on it.
