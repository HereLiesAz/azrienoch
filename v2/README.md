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
from. `wdth` here goes through `condense.py`'s per-x, ink-density
weighted compression (see that module's docstring) rather than a flat
`x *= wf` scale -- the flat scale used to thin a stem by the same
factor it narrowed a counter, which read as an obvious squish rather
than a condensed cut at heavy weight (a stem's X-extent shrinks with
the scale, a horizontal stroke's Y-extent doesn't, so the two drift out
of proportion the heavier and more condensed a master gets -- caught by
rendering the full alphabet at `wght`=900/`wdth`=75 and comparing stroke
weights directly). The new version still isn't a true optically
condensed redraw (no counter is actually reshaped, and it's a single
global compression curve applied the same at every height, so a
diagonal stroke's x position only gets partial credit for the ink it
carries) -- worth revisiting once the modification pass below is
underway -- but stems now measure close to their `wdth`=100 width
instead of uniformly thinned by the same 25% as every counter (`n`'s
stem: 0.98x instead of 0.75x; `H`'s: 0.90x instead of 0.75x, both at
`wght`=900 -- `o`'s ring, which has no distinct stem/counter columns to
tell apart, still compresses close to uniformly, which is expected).

`s` is the one exception: it's pulled from
[Arimo](https://github.com/googlefonts/arimo) instead (vendored at
`third_party/arimo/`, SIL OFL 1.1) -- an open, metric-compatible
Helvetica/Arial workalike -- per the project owner's direction that it
specifically reads as Helvetica-derived. Real Helvetica outline data is
proprietary (Linotype/Monotype) and was never traced or extracted here;
Arimo is a freely licensed font used and modified exactly as its
license permits, the same legal basis this project uses Jost on. See
`tools/arimo_source.py`. `c`/`e` used to be sourced from Arimo the same
way, but are now built directly from this project's own `o` instead
(`tools/ring_derived.py` -- see "Status" below).

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

Every one of those 12 masters is also an `fvar` named instance --
`designspace_build.py` gives each an `InstanceDescriptor` (Thin/
Regular/Black x Normal/Condensed x Sans/Slab, e.g. "Black Condensed
Slab") and a STAT table with a proper axis-value label per stop, so a
style picker lists all 12 named styles instead of just interpolating
silently along raw axis sliders. This was missing entirely through the
font's first several revisions -- the compiled variable TTF always had
the full range internally (any `wght`/`wdth`/`SERF` coordinate
interpolates correctly), but with no named instances defined, apps that
list a font's available styles rather than exposing its axes directly
had only the implicit default ("Regular") to show, regardless of how
many masters actually existed. Getting the naming right took two
passes: STAT's own elision rule (`AxisLabelDescriptor.elidable`) turned
out to override each instance's explicit `styleName`, not just decorate
it -- marking `wght`'s default ("Regular") elidable the same way
`wdth`/`SERF`'s defaults are (correctly dropping "Normal"/"Sans" when
they don't apply) made "Regular" vanish from every instance that shared
that weight, not just the one truly-default instance ("Condensed"
instead of the intended "Condensed Regular"). Fixed by never eliding
`wght`'s own labels. Separately, each master UFO's `font.info.styleName`
had been set to the same technical identifier used for its own on-disk
folder name (`Wght900_Wdth75_Serf100`) -- harmless for the 11 masters
that only feed `gvar`, but the DEFAULT master's `font.info` is copied
into the compiled font's actual name table (nameID 1/2/16/17) via its
source's `copyInfo=True`, so that technical string leaked into the
font's real family/style name until `font.info.styleName` was changed
to the same human name (`params.instance_style_name`) the fvar instance
uses.

## Status

338 glyphs -- the basic Latin alphabet (`A`-`Z`, `a`-`z`), digits
(`0`-`9`), punctuation, Latin-1 Supplement, Latin Extended-A, and
Cyrillic -- copied from Jost across all 12 masters (except `c`/`e`,
built from this project's own `o`, and `s`, sourced from Arimo -- see
below), with a first pass of Azrienoch-specific modifications on top
(`tools/quirks.py`) for the original 62 ASCII letters/digits.

**Character set is not yet Greek** -- Jost itself barely has any Greek
glyphs (4 codepoints total), so it needs a separate donor font this
project doesn't vendor yet; the repository root's own v1 pipeline
covers Greek via Roboto Flex. `quirks.py`'s terminal-cut/round-counter
treatments and `serifs.py`'s per-letter-class foot rules are also still
scoped to the original 62 -- accented Latin and Cyrillic glyphs get
Jost's own raw shape (correctly weighted/condensed/serifed at the
whole-letter level, since those axes apply generically) but not yet
the same per-glyph refinements as their base letters (e.g. `ā`'s
counter isn't forced to match `o`'s the way `a`'s is). `kerning.py` is
similarly still scoped to the original 62 -- every other glyph compiles
and renders but is unkerned against everything, including itself.
Jost's own accented glyphs that are TrueType composites (a base letter
plus a separately drawn diacritic component, e.g. `Ohungarumlaut`) are
decomposed on extraction (`jost_source.py` uses fontTools'
`DecomposingRecordingPen`, not a plain one) so every downstream
consumer only ever sees plain outline data, never a component
reference. One genuinely new axis this expansion doesn't add: v1 also
has a `GRAD` (grade) axis, passed straight through to Roboto Flex's own
native `GRAD`; Jost has no such axis to pass through, so v2 would need
its own from-scratch implementation (stroke-weight offsetting that
doesn't change advance width) -- not attempted yet.

- **`c`/`e` are built directly from this master's own `o`**
  (`tools/ring_derived.py`), not from a separate donor font. `o`'s own
  outer+inner ring is cut open (an aperture for both, plus a straight
  crossbar for `e`) via exact quadratic-Bezier subdivision at a fixed
  angle from the ring's own center -- every point either glyph keeps is
  therefore pixel-identical to `o`'s own, and their bowl/counter
  proportions agree with `o`'s BY CONSTRUCTION, at every weight, width
  and serif setting, with no matching required. This replaces an
  earlier approach (`c`/`e` sourced from Arimo, like `s` still is --
  see below) that spent two rescale attempts trying to match `c`/`e`'s
  ADVANCE WIDTH to Jost's own `ch`-to-`o` ratio and reverted both (a
  flat scale fattened the terminal at Thin; a centroid-radial push
  fixed that but pinched the counter into an hourglass waist at Black
  -- see git history for the full account) without ever fixing the
  actual root cause: Arimo is a different font with different
  proportions than Jost, so no amount of width-matching could make its
  `c`/`e`'s counter SHAPE agree with `o`'s. Deriving them from `o`
  directly -- the same move already made for `a` (built from `d`'s own
  outline, see below) -- fixes that at the source. `e`'s upper bowl is
  a proper, separately-wound hole (same two-contour structure as `o`
  itself), closed below by the crossbar rather than a curve; its lower
  counter merges into the outer silhouette's own single contour, open
  to the outside through the aperture, the same way `c`'s counter is
  single-contour. Both go through `quirks.py::apply_terminal_cuts` too,
  same as Arimo-sourced `s`: Bezier subdivision at an exact target
  angle doesn't land the two straight cuts closing the aperture
  perfectly flush, so they're reoriented to true horizontal the same
  way Arimo's own terminals are. One known residual: at `wght`=100
  combined with `wdth`=75 (Thin Condensed, the single most extreme
  corner of the whole design space), `e`'s stroke wall gets thin enough
  at the aperture that its terminal folds into a tiny self-intersecting
  spike -- confirmed directly, not just suspected, by rendering that
  specific corner and finding one real crossing. Not yet fixed: the
  aperture's angle is fixed relative to the ring's own center, but
  `condense.py`'s width compression is non-uniform (X only), so the
  wall thickness at that fixed angle can shrink much faster than the
  letter's overall proportions would suggest at extreme corners --
  fixing it needs the aperture geometry to adapt to the compressed
  ring's own local wall thickness, not just its angle.
- **`s` is sourced from Arimo, not Jost** (`tools/arimo_source.py` --
  see "Where the letterforms come from" and "Design references"
  above): it's meant to read as Helvetica-derived, and has no ring or
  counter to derive from `o` the way `c`/`e` now are. Arimo's own
  terminal there is close to horizontal but genuinely diagonal by
  design, so it still goes through `quirks.py::apply_terminal_cuts`,
  just with Arimo's own point indices instead of Jost's -- this is a
  real fix, not a workaround, for a problem this project hit trying to
  reorient Jost's own terminal on `s` into that shape (see the
  similarity-transform note below): the reoriented cut kept producing
  a self-intersection at heavy weight that traced back to the curve
  geometry right at that terminal, not just the reorientation math.
  Arimo ships only as static instances (Regular/Bold, not a variable
  font); `arimo_source.py` interpolates/extrapolates between their
  point coordinates directly for this project's own `wght` samples,
  confirmed safe to do point-for-point since `s` has identical
  point-command signatures between the two vendored weights.
- **`s`'s WEIGHT is calibrated against Jost's own original `s`, not
  Arimo's own Regular/Bold labels.** A first version mapped this
  project's `wght` value straight onto an interpolation fraction between
  Arimo Regular (treated as 400) and Bold (700) -- but Arimo's own
  weight range is far narrower than Jost's, so that naive mapping
  rendered `s` several times heavier than the surrounding Jost letters
  at `wght`=100 -- caught by a Glee design-coherence audit rendering
  "acorns"/"assess" at Thin, confirmed with a direct stroke-width
  measurement rather than left as a visual impression. `arimo_source.py`
  now measures Jost's own ORIGINAL `s`'s stroke-width ratio at the
  target `wght` (via a real instancer sample, not extrapolated) and
  solves for the Arimo interpolation parameter that scales Arimo's own
  `s` stroke width by that same ratio -- correct WEIGHT from the letter
  this project used before switching to Arimo, correct SHAPE from
  Arimo, per the project owner's own framing of the fix. This pushes
  the extrapolation well past Arimo's own [0, 1] Regular-Bold range in
  both directions, which surfaced (and this same audit round fixed) a
  genuine near-duplicate-point defect in Arimo's own raw `e` (back when
  `e` was still Arimo-sourced) that only became a visible spike once
  stretched that far -- see the `y`/`six`/`nine` fixes below for the
  same class of bug inherited from Jost.
- **`s`'s advance width still doesn't track `o`'s own `wght`-relative
  proportions.** Unlike `c`/`e`, `s` couldn't be derived from `o` (an
  S-curve has no ring to cut open), so it's still only width-matched by
  whatever Arimo's own Regular-Bold blend happens to produce, which has
  nothing to do with how wide `o` (Jost-sourced, a completely
  independent width curve) happens to be at the same master. A known,
  narrower version of the problem `c`/`e` used to have.
- **A Glee stability audit's self-intersection sweep across the full
  `wght`x`wdth`x`SERF` grid** caught three genuine defects inherited
  byte-for-byte from the vendored Jost outlines (none introduced by this
  project's own extraction or modification code, which itself checked
  out clean everywhere the audit tested it): `y` had a visible hole at
  its crotch (its two diagonal strokes' inner edges terminated a few
  units past their actual crossing point instead of meeting it exactly);
  `six`/`nine` each had a small notch where the bowl meets the
  ascender/descender stroke (two on-curve points a few units apart where
  the drawing intends one). Both fixed in `quirks.py`
  (`fix_y_crotch`/`fix_six_nine_notch`) by moving the offending points to
  where the geometry actually intends them to meet, not by adding or
  removing a point. Two further findings, digit `4`'s technically
  self-intersecting crossbar/stem junction and capital `B`'s
  technically self-intersecting waist (two overlapping, collinear
  spine segments in its single-contour "keyhole" construction, where
  the corridor connecting the outer silhouette to each counter
  retraces part of the same stem edge), were both confirmed by direct
  rendering -- not just the geometric self-intersection test that
  first flagged them -- to draw with no visible artifact at every
  weight/width combination checked (a harmless retrace/T-junction under
  nonzero-winding fill, the overlapping segments contributing no net
  area). Needed no fix, same conclusion for both, though `B`'s was
  initially assumed to need one and left deferred before actually being
  rendered and checked.
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
- `o`/`c`/`e`/`s` -- fully round letters, all four declared
  `SINGLE_STORY` -- get NO foot at any `SERF` value, on every one of
  them alike: a round bowl has no flat stem run anywhere on it, the same
  structural limitation already documented above for `g`'s curved
  descender hook, not specific to any one of these letters' own source
  (`c`/`e` built from `o`, `s` from Arimo -- all four behave
  identically).

One real bug caught by rendering before this landed: a first version
grew a spurious extra foot on `n` where its left stem's short (~70-unit)
run-up into the arch happens to end flat and close enough to the
x-height ballpark to look like a genuine terminal. The root project's
own length threshold on the adjacent stem segment (must run at least
~150 units to count as a real stem side) rejects that short run
cleanly, the same guard that already keeps a foot from notching into an
arch letter's own counter.

Not yet done, in order:

- **Greek**, a `GRAD` axis, and extending `quirks.py`/`serifs.py`/
  `kerning.py`'s per-glyph refinements past the original 62 ASCII
  letters/digits to the newly added punctuation/Latin-1/Latin
  Extended-A/Cyrillic set (see "Status" above for the full account of
  what's covered and what isn't).
- **A true optically condensed `wdth` cut.** `condense.py`'s ink-density
  weighted compression (see above) keeps stems close to their full
  width at heavy/condensed combinations instead of uniformly squishing
  them, but it's still a global per-x warp with no counter actually
  reshaped -- a real condensed cut redraws counters and adjusts
  spacing by hand, which this project doesn't do.
- **`s`'s advance width doesn't track `o`'s own `wght`-relative
  proportions** (see "Status" above). `c`/`e` no longer have this
  problem (both now derive their whole shape, width included, from
  `o` directly); `s` still can't, since an S-curve has no ring to cut
  open the way `c`/`e` do.
- **`e`'s aperture terminal self-intersects at the single most extreme
  corner of the design space** (`wght`=100 combined with `wdth`=75 --
  see "Status" above for why: the aperture's angle is fixed relative to
  `o`'s own center, but `wdth`'s non-uniform compression can thin the
  ring wall at that exact angle faster than the rest of the letter).
  Confirmed narrow (one real self-intersection, only at that one
  corner) rather than assumed fixed by the rest of the ring-derivation
  work.
- **`s` at Thin (`wght`=100, any `wdth`) has its own near-zero ring-wall
  pinch** (~0.002 units, pre-existing -- present on the plain Cartesian-
  interpolated shape itself, confirmed directly, independent of anything
  else in this section). `s` can't take the same fix `c`/`e` got (an
  S-curve has no ring to derive from `o`), so its own extreme
  `wght`=100 alpha still moves points along each one's own
  Regular-to-Bold straight line. Not reported by name and not fixed
  this pass; a real, if narrow and currently invisible, residual.

## Kerning

533 letter-pair corrections (`tools/kerning.py`), extracted from
vendored Jost's own GPOS pair-positioning table rather than hand-tuned
-- the same donor-kerning approach the repository root's own v1
pipeline uses on Roboto Flex, for the same reason: several thousand
pairs tuned by eye is its own multi-week type-design task, and Jost
already did that work. Jost's own kerning is entirely static across its
`wght` axis (confirmed by diffing the full extracted table at
`wght`=100/400/900: zero pairs differ), so one extraction is reused at
every master, scaled only by that master's own `wdth` fraction (kerning
has no direct `SERF` dependence either). `c`/`e`/`s` (no longer all
Jost's own outlines -- `c`/`e` are built from `o`, `s` from Arimo, see
"Status" above) keep Jost's own kerning values for pairs involving
them regardless, a stand-in on the same donor-kerning logic the rest
of the module rests on. `a` (built from
`d`'s own contours, not Jost's separately-drawn `a`) gets `d`'s kerning,
not Jost's native `a`'s -- Jost's own `d` happens to carry no
class-kerning pairs at all, so `a` ends up unkerned too, the more
consistent outcome given it now shares `d`'s exact shape.

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
v2/tools/arimo_source.py       extracts s from vendored Arimo (Helvetica-derived)
v2/tools/ring_derived.py       builds c/e from this project's own o (cut-open ring + crossbar)
v2/tools/condense.py           the wdth axis: ink-density weighted horizontal compression
v2/tools/kerning.py            letter-pair kerning, extracted from vendored Jost's own GPOS
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
