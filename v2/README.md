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
(`0`-`9`) -- copied from Jost across all 6 masters, with a first pass of
Azrienoch-specific modifications on top (`tools/quirks.py`):

- **Horizontal terminal cuts** on `c`/`e`/`s` (Helvetica-style -- Jost's
  own cut is vertical on `c`, diagonal on `e`/`s`). `g`'s own descender-
  loop terminal was already a horizontal cut in Jost and needed no
  change (confirmed by inspection, not assumed).
- **Vertical terminal cuts** on `r`/`f`, matching each other (Jost draws
  both with the same diagonal cut; both are now reoriented the same way
  instead of one differing from the other).
- **Every round-bowled lowercase letter's inner counter is now a true
  affine-scaled copy of `o`'s own inner counter**: `b`, `d`, `p`, `q`,
  `g`. Confirmed structurally (Jost's own `o`/`b`/`d`/`p`/`q`/`g` all
  share an identical 16-point contour shape for exactly this reason) and
  ported from the repository root's own `tools/canonical_counter.py`
  technique. Not yet extended to `a` (its inner contour also carries the
  points where the counter joins the stem, so it doesn't structurally
  match as a whole contour the way the others do) or `c`/`e` (open
  letterforms with no separate counter contour to replace) -- both are
  the same class of gap the root project's own `canonical_counter.py`
  documents as unfinished for its analogous cases.
- **`a` is single-story** -- confirmed to already be true of Jost's own
  `a` (its bbox top matches `o`'s exactly, `(_, _, _, 470)` at every
  weight tested) rather than something this pass needed to build.

The reorientation itself is a rigid transform (preserves the cut's
length/stroke-thickness and its midpoint, only changes which axis it
spans) applied to point indices identified once against Jost's own
wght=400 instance and stable across every master (fontmake requires
matching topology across masters to compile at all, and Jost's own
`gvar` already interpolates across its native `wght` range, so a given
glyph's point count/order doesn't change with weight).

Compiles to a variable TTF with both axes interpolating cleanly, and
`tools/preview.py`'s rendered sample confirms the modifications hold up
at Thin/Regular/Black and Condensed alike, not just at the reference
weight the point indices were found at.

Not yet done, in order:

- **Serifs.** A variable `SERF` axis (0-100, sans by default) that grows
  a slab foot the same way weight grows stroke thickness -- planned:
  single-story lowercase letters get a foot top and bottom; two-story
  lowercase (ascenders/descenders) and all uppercase get a foot only on
  the end that terminates at a baseline or a descender depth, not at an
  ascender/cap top.
- **Kerning.** None yet -- needs the full glyph set (now in place) to
  tune real pairs against.
- **The round-counter treatment extended to `a`.**
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
