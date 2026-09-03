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

`c`/`e`/`s` are the one exception: they're pulled from
[Arimo](https://github.com/googlefonts/arimo) instead (vendored at
`third_party/arimo/`, SIL OFL 1.1) -- an open, metric-compatible
Helvetica/Arial workalike -- per the project owner's direction that
these three specifically read as Helvetica-derived. Real Helvetica
outline data is proprietary (Linotype/Monotype) and was never traced or
extracted here; Arimo is a freely licensed font used and modified
exactly as its license permits, the same legal basis this project uses
Jost on. See `tools/arimo_source.py`.

## Design references

- **Jost** (OFL) -- the actual source of every outline in this build
  (see above), not just an influence.
- **Helvetica** -- proprietary (Linotype/Monotype); its rational,
  flat/square-cut terminals and directness (no ball terminals, no
  bracketed serifs, tighter apertures than Jost's own) are the intended
  target for `c`/`e`/`s` specifically -- nothing from Helvetica itself
  is traced or extracted, per its license. Those three letters are
  instead pulled from **Arimo** (OFL), an open, metric-compatible
  Helvetica/Arial workalike -- see "Where the letterforms come from."
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
| Serif | `SERF` | 0-100 | 0 (sans) |

Masters: the full `wght` x `wdth` x `SERF` grid
(`tools/params.py::MASTER_GRID`), 3 weight samples (100/400/900, so
`wght` gets a bend rather than one straight interpolation) x 2 width
samples x 2 serif samples = 12 masters. The default
location (400, 100, 0) is itself one of the twelve, as a designspace
requires.

## Status

62 glyphs -- the basic Latin alphabet (`A`-`Z`, `a`-`z`) and digits
(`0`-`9`) -- copied from Jost across all 12 masters (except `c`/`e`/`s`,
see below), with a first pass of Azrienoch-specific modifications on top
(`tools/quirks.py`):

- **`c`/`e`/`s` are sourced from Arimo, not Jost** (`tools/arimo_source.py`
  -- see "Where the letterforms come from" and "Design references"
  above): these three are meant to read as Helvetica-derived. Arimo's own
  terminals there are close to horizontal but genuinely diagonal by
  design (a rise of 12-31 units across the cut, confirmed by dumping
  Arimo's own raw points directly, not assumed from how they looked at a
  glance), so they still go through `quirks.py::apply_terminal_cuts`,
  just with Arimo's own point indices instead of Jost's -- this is a
  real fix, not a workaround, for a problem this project hit twice
  trying to reorient Jost's own terminals on `c`/`s` into that shape
  (see the similarity-transform note below): the reoriented cut kept
  producing a self-intersection at heavy weight that traced back to the
  curve geometry right at that terminal, not just the reorientation
  math. Arimo ships only as static instances (Regular/Bold, not a
  variable font); `arimo_source.py` linearly interpolates (or, past
  Bold's own 700, extrapolates) between their point coordinates directly
  for this project's own `wght` samples, confirmed safe to do
  point-for-point since `c`/`e`/`s` have identical point-command
  signatures between the two vendored weights.
- **Every terminal reorientation** (`quirks.py::_reorient_cut`, used for
  `c`/`e`/`s`'s horizontal cut and `r`/`f`'s vertical one) transforms
  not just the two
  terminal points but the whole run of off-curve control points leading
  into each one, via a similarity transform (rotate + scale, pivoting on
  that curve's own anchor point) rather than a plain translation: a
  translation was tried first and left the control point the same
  distance from its anchor regardless of how far the terminal itself had
  to move, which overshot into a self-intersecting notch at heavy weight
  (confirmed directly, rendering `c`/`s` at wght 900 before this fix,
  back when they were still Jost-derived) even though it looked fine at
  Thin.
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
  match as a whole contour the way the others do) -- the same class of
  gap the root project's own `canonical_counter.py` documents as
  unfinished for its analogous case. `c`/`e` are no longer Jost-derived
  at all (see above) so this doesn't apply to them.
- **`a` is single-story, built directly from `d`** (`tools/single_story_a.py`,
  ported from the repository root's own module of the same name): a
  fresh copy of `d`'s own three contours (Jost draws `d` as an
  independent stem rectangle, bowl outer, and inner counter, rather than
  Roboto Flex's fused stem+bowl outer, which made this simpler than
  root's own version -- the stem is just contour 0 outright) with the
  stem's top edge moved down from ascender height to x-height (or just
  clear of the counter's own top, if that's taller at extreme weights,
  same `COUNTER_CLEARANCE` guard root's version uses). Not "confirmed
  Jost's own `a` happens to already be single-story" any more, as this
  project's first pass here found -- replaced with an `a` that's
  literally `d` with a shortened stem, matching root's own convention,
  per the project owner's direction.

The reorientation itself is a rigid transform (preserves the cut's
length/stroke-thickness and its midpoint, only changes which axis it
spans) applied to point indices identified once against Jost's own
wght=400 instance and stable across every master (fontmake requires
matching topology across masters to compile at all, and Jost's own
`gvar` already interpolates across its native `wght` range, so a given
glyph's point count/order doesn't change with weight).

Compiles to a variable TTF with all three axes interpolating cleanly,
and `tools/preview.py`'s rendered sample confirms the modifications
hold up at Thin/Regular/Black and Condensed alike, not just at the
reference weight the point indices were found at.

**A variable `SERF` axis** (0-100, sans by default, `tools/serifs.py`)
grows a slab foot the same way `wght` grows stroke thickness -- ported
from the repository root's own `tools/serifs.py` (which does this for
Roboto Flex) rather than redesigned from scratch: detect a flat stem
terminal once on a reference instance (`wght`=400, `wdth`=100), and at
every master append a same-wound rectangle contour there (collapsed to
a hairline at `SERF`=0, a full slab at `SERF`=100), rather than
relocating the stem's own points -- appending same-wound ink can only
ever add, never accidentally flip a fill relationship the way an
earlier, since-discarded point-insertion version of this did on `n`.
Which terminal(s) get a foot, and which direction each one flares,
follows the project owner's own handwriting-inspired rule -- rewritten
once already after the first pass got it wrong in two ways (every
single-story letter got a foot per stem instead of exactly two, and
multi-stem letters like `H`/`R` flared symmetrically outward AND inward,
notching straight into their own counters):

- A single-story letter (`SINGLE_STORY`) gets exactly TWO feet total:
  the x-height top of its leftmost stem, flaring only left, and the
  baseline of its rightmost stem, flaring only right -- not a foot on
  every flat terminal.
- An ascender letter (`b`/`d`/`f`/`h`/`k`/`l`/`t`) gets a foot only at
  the baseline, never the ascender top.
- `g`/`p`/`q` get a foot only at the x-height top instead -- the
  opposite end from the rest of `DESCENDER_TOP`'s siblings -- `g`'s own
  descender is a curved hook rather than a straight stem in this
  construction anyway, so it never had a foot there to move.
- `y` gets a foot at both the x-height top and its own descender depth.
- Uppercase and digits get a foot only at the baseline, never the top.
- Every letter EXCEPT single-story ones keeps a foot per qualifying
  stem, but each one flares only away from the letter's OTHER stems: the
  leftmost stem at a guide flares left only, the rightmost flares right
  only, a lone stem at that guide flares both ways, and anything
  strictly between two others doesn't flare at all. This is what fixes
  `H`/`R`: both used to flare both ways whenever geometrically safe,
  which included flaring each stem toward the other, into the counter.

One real bug caught by rendering before this landed: a first version
grew a spurious extra foot on `n` where its left stem's short (~70-unit)
run-up into the arch happens to end flat and close enough to the
x-height ballpark to look like a genuine terminal. The root project's
own length threshold on the adjacent stem segment (must run at least
~150 units to count as a real stem side) rejects that short run
cleanly, the same guard that already keeps a foot from notching into an
arch letter's own counter.

Not yet done, in order:

- **Kerning.** None yet -- needs the full glyph set (now in place) to
  tune real pairs against.
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
v2/tools/quirks.py             terminal-cut reorientation, canonical round counters
v2/tools/serifs.py             the SERF axis: detects stem terminals, grows slab feet
v2/tools/params.py             axis model, master grid, vertical metrics
v2/tools/ufo_build.py          builds one UFO per master from jost_source.py + quirks.py + serifs.py
v2/tools/designspace_build.py  writes the designspace, runs fontmake
v2/tools/preview.py            dev-only visual QA render
v2/tools/arimo_source.py       extracts c/e/s from vendored Arimo (Helvetica-derived)
v2/third_party/jost/           vendored Jost source font + its own OFL.txt
v2/third_party/arimo/          vendored Arimo Regular/Bold + its own OFL.txt
v2/sources/                    build output (UFOs + designspace)
v2/fonts/variable/             build output (compiled variable TTF)
```

## License

Everything in this directory that touches Jost's outline data is a
Modified Version of Jost under the SIL Open Font License, Version 1.1
(`v2/third_party/jost/OFL.txt`; project authors credited there).
Likewise, `c`/`e`/`s` are a Modified Version of Arimo under the same
license (`v2/third_party/arimo/OFL.txt`). The root repository's
`OFL.txt` covers the project as a whole.

## Next steps

1. Kerning: derive pair classes from the full glyph set and tune by eye
   against rendered specimens.
2. The round-counter treatment extended to `a`, and further Helvetica-
   inspired proportion adjustments beyond terminals/counters/serifs.
3. A real condensed cut for `wdth`, replacing the uniform-scale
   placeholder, now that the letterform modification passes it would
   otherwise have to redo (terminals, counters, serifs) are in place.
4. Revisit whether a fourth axis belongs here for the Heliuum-style
   "mix and match" goal specifically, once the modified letterforms are
   settled enough to know if `wght`/`wdth`/`SERF` alone already deliver
   on it.
