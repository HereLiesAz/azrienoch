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
| Serif | `SERF` | 0-100 | 0 (sans) |

Masters: the full `wght` x `wdth` x `SERF` grid
(`tools/params.py::MASTER_GRID`), 3 weight samples (100/400/900, so
`wght` gets a bend rather than one straight interpolation) x 2 width
samples x 2 serif samples = 12 masters. The default
location (400, 100, 0) is itself one of the twelve, as a designspace
requires.

## Status

62 glyphs -- the basic Latin alphabet (`A`-`Z`, `a`-`z`) and digits
(`0`-`9`) -- copied from Jost across all 12 masters (except `s`, see
below), with a first pass of Azrienoch-specific modifications on top
(`tools/quirks.py`):

- **`c`/`e` are cut directly from `o`, not from Jost's own (very
  slightly different) circle for those two letters**: every on/off-curve
  point on their round silhouette is projected onto `o`'s own exact
  outer or inner circle at the same angle from center
  (`quirks.py::snap_round_points_to_o`), before the terminal cut below
  carves the opening. Only runs on points that aren't part of a straight
  ('line'-type) segment -- `e`'s crossbar and both letters' flat cut
  connectors were never on the circle to begin with, so they're left as
  Jost drew them.
- **Horizontal terminal cuts** on `c`/`e` (Helvetica-style -- Jost's own
  cut is vertical on `c`, diagonal on `e`). `g`'s own descender-loop
  terminal was already a horizontal cut in Jost and needed no change
  (confirmed by inspection, not assumed).
- **`s` is sourced from the repository root's own Azrienoch pipeline
  (Roboto Flex) instead of Jost** (`tools/roboto_s_source.py`): Jost's
  own `s`, once reoriented to a horizontal terminal, kept producing a
  self-intersection at heavy weight that traced back to the curve
  geometry right at that terminal, not just the reorientation math.
  Root's own `s` has a real stepped ink-trap notch at heavy weight
  instead (confirmed directly against Roboto Flex's own raw, untouched
  points -- a deliberate optical correction, not a bug), extracted
  before root's own serif feet are applied (v2 applies its own SERF axis
  afterward) and rescaled from Roboto Flex's metrics to this project's
  own via the x-height ratio (`s` sits entirely within the x-height box
  in both). Root's `wght` axis floors at 180, not v2's 100 -- v2's
  `wght`=100 sample clamps to root's 180, the closest real value rather
  than an extrapolation.
- **Vertical terminal cuts** on `r`/`f`, matching each other (Jost draws
  both with the same diagonal cut; both are now reoriented the same way
  instead of one differing from the other).
- Each terminal reorientation (`quirks.py::_reorient_cut`) transforms not
  just the two terminal points but the whole run of off-curve control
  points leading into each one, via a similarity transform (rotate +
  scale, pivoting on that curve's own anchor point) rather than a plain
  translation: a translation was tried first and left the control point
  the same distance from its anchor regardless of how far the terminal
  itself had to move, which overshot into a self-intersecting notch at
  heavy weight (confirmed directly, rendering `c`/`s` at wght 900 before
  this fix) even though it looked fine at Thin. The similarity transform
  scales the whole curve segment consistently with its own terminal's
  actual displacement.
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
Which terminal(s) get a foot follows the project owner's own rule:

- A letter confined to the x-height box (no ascender/descender) gets a
  foot at both the baseline and the x-height top, wherever a flat run
  genuinely exists there -- `n`'s stems, for instance, only have one at
  the baseline, since their tops curve straight into the arch with no
  flat run to grow a foot from at all.
- A letter with an ascender/descender gets a foot only at the end that
  terminates at a baseline or a descender depth (`b`/`d`/`h`/`k`/`l`/
  `f`/`t`'s baseline; `q`'s own descender), never at an ascender/cap
  top -- `g`'s own descender is a curved hook rather than a straight
  stem in this construction, so it gets no foot at all, a real
  limitation of "slab feet on flat stems only," not a bug.
- Uppercase and digits get a foot only at the baseline.

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
- **The SERF axis's classification/geometry rules**, per the project
  owner's more detailed direction than the first pass implemented:
  single-story lowercase letters should get exactly two diagonal feet
  (top-left of the first stem flaring only left/backward, bottom-right
  of the last stem flaring only right/forward -- not a foot on every
  flat terminal), two-story ascenders one symmetric-outward foot at the
  bottom only, `g`/`p`/`q` one at the top instead, `y` both, and
  uppercase never a top foot with bottom feet flaring strictly outward
  (the current `H`/`R` feet flare inward, which needs fixing).

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
