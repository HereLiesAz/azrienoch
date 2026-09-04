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

408 glyphs -- the basic Latin alphabet (`A`-`Z`, `a`-`z`), digits
(`0`-`9`), punctuation, Latin-1 Supplement, Latin Extended-A, Greek,
and Cyrillic -- the same character set the repository root's own v1
pipeline covers, in full. Latin/Cyrillic/punctuation/digits are copied
from Jost across all 36 masters (except `c`/`e`, built from this
project's own `o`, and `s`, sourced from Arimo -- see below), with a
first pass of Azrienoch-specific modifications on top (`tools/quirks.py`)
for the original 62 ASCII letters/digits, now extended to accented
Latin and select Cyrillic letters too (see below).

**Greek is sourced from the repository root's own vendored Roboto
Flex**, not Jost -- Jost itself has almost no Greek coverage (4
codepoints total, confirmed directly against its own cmap), so it
needs a separate donor; rather than vendoring a second new font and
re-solving "how do you get a sane per-weight stroke/height progression
out of an independent-parametric-axes variable font" from scratch,
`roboto_flex_source.py` reuses v1's own already-tuned
`tools/roboto_source.py::roboto_location` wholesale via a read-only
import (no v1 file touched) -- v2's own `wdth` (75-100) and `GRAD`
(-50 to 50) ranges are numerically identical to v1's own, so both pass
straight through with no rescaling; only `wght` is floor-clamped to
180 (v1's own floor -- everything below it was confirmed, repeatedly,
to self-intersect somewhere in Roboto Flex's own gvar deltas at this
axis combination, a font-data limitation predating this project).
Greek necessarily looks like Roboto Flex's own grotesque design, not
Jost's geometric one -- a real, visible style seam against the
Latin/Cyrillic alphabet, the same class of tradeoff already made for
's' (Arimo/Helvetica-derived). No Azrienoch-specific quirks/serifs
refinement is applied to Greek, and it has no kerning of its own (see
"Kerning" below) -- it compiles and renders correctly (confirmed:
full 36-master grid compiles with identical point topology, and Greek
was rendered and checked at several master combinations, including
Black+Condensed+Slab, with no defects) but carries none of the
per-letter-class treatment Latin/Cyrillic now get.

Jost's own accented glyphs that are TrueType composites (a base letter
plus a separately drawn diacritic component, e.g. `Ohungarumlaut`) are
decomposed on extraction (`jost_source.py` uses fontTools'
`DecomposingRecordingPen`, not a plain one) so every downstream
consumer only ever sees plain outline data, never a component
reference; `roboto_flex_source.py` does the same for Roboto Flex's own
composites.

- **`quirks.py`'s round-counter reshaping and `serifs.py`'s
  per-letter-class foot rules now extend to every accented Latin
  letter**, not just the original 62 ASCII letters/digits, via
  `params.base_letter` -- Unicode NFD decomposition strips a letter's
  own combining accent (`ē` -> `e`, `ō` -> `o`, `ń` -> `n`), so an
  accented glyph gets exactly the same classification its plain base
  letter does: `ō`'s counter is reshaped to match `o`'s own (the same
  structural point-topology match `reshape_counter_to_o` already used,
  just now offered more glyphs to check), and every accented letter
  grows serif feet at the guide lines and flare directions its base
  letter's own letter-class dictates -- including a real, previously
  wrong case this surfaced directly: accented `n` (`ń ň ñ ņ`) used to
  fall through to the generic uppercase/digit "baseline-only, no flare
  restriction" bucket (its literal, non-ASCII character not matching
  any of `serifs.py`'s ASCII-keyed class sets), keeping a foot on BOTH
  of its stems -- `n` itself is declared `SINGLE_STORY` (documented as
  "gets exactly two feet"), so its accented variants now correctly
  drop the left stem's foot the same way plain `n` always has.
  `quirks.py`'s terminal-cut treatment covers the 18 c/e/s-based
  accented letters (via mark-splicing, below) plus 3 r-based ones
  directly, described next.

- **Nine lowercase Cyrillic letters get the same treatment too**, via a
  small hand-checked `_CYRILLIC_ANALOG` table in `params.py` (NFD
  decomposition doesn't relate Cyrillic to Latin at all, so this part
  isn't automatic): `а`/`е`/`э`/`о`/`с`/`м`/`р`/`у`/`х` were each
  rendered and confirmed by direct inspection to share a plain Latin
  letter's structural class -- `о`/`с` are pure round bowls (`o`/`c`),
  `е`/`э` share `e`'s aperture-cut shape (mirrored, for `э`), `м` is a
  three-legged bridge identical to `m`, `р` is a bowl-plus-descender
  identical to `p` (so its bowl's counter now reshapes to match `o`'s
  too, the same as `p`'s own), `у` is a v-bowl-plus-descender-tail
  identical to `y`, and `х` is pure diagonal crossing strokes like `x`
  (grows no feet regardless, same as `x`). Every other Cyrillic
  lowercase letter (`б в г д ж з и й к л н п т ф ц ч ш щ ъ ы ь ю я`) was
  rendered and checked too but has no clean single-Latin-letter
  structural analog -- bridge/ladder shapes like `н`/`п` (which
  resemble a lowercase Latin "H", not "n") already get the right
  generic two-stem-outward-flare treatment from the unclassified
  default, so forcing a wrong analog onto them would make things worse,
  not better, and they're deliberately left alone. Cyrillic uppercase
  needs no equivalent work: it already gets the same baseline-only
  treatment Latin uppercase does, correctly, from the same
  unclassified default.

- **`c`/`e`/`s`'s own accented variants need more than the base-letter
  resolution above** (their base letters aren't built from Jost's raw
  shape at all -- `c`/`e` are ring-derived, `s` is Arimo-sourced -- so
  there's no Jost outline for those accented glyphs to inherit
  correctly-shaped serif feet or counters from in the first place):
  every accented Latin letter whose base is `c`/`e`/`s` (`ç è é ê ë ć ĉ
  ċ č ē ĕ ė ę ě ś ŝ ş š`, 18 letters) gets its diacritic mark re-spliced
  onto THIS project's own finished `c`/`e`/`s` instead of carrying
  Jost's own native shape for that base letter (`tools/accent_marks.py`)
  -- without this, e.g. `ć` would read as Jost's own geometric-sans `c`
  with an accent, sitting oddly next to this project's own
  Helvetica-derived one right beside it in any real word. Jost's own
  accented glyphs aren't a base contour byte-identical to the plain
  letter plus an appended mark contour (confirmed directly: `ę`'s own
  first contour has a different point count than plain `e`, evidently
  redrawn slightly to fit the mark) -- but `c`/`e`/`s` are always
  single-contour in Jost, so contour 0 of any of these accented glyphs
  is reliably "this letter's own version of the base," and every
  contour after it is the mark, regardless of whether the base
  contour matches point-for-point. The mark is repositioned
  horizontally to this project's own base's center (both letters share
  the same baseline/cap-height/x-height, so no vertical adjustment is
  needed -- confirmed by comparing bounding boxes directly). `r`'s own
  three accented variants (`ŕ ŗ ř`) need no re-splicing -- `r` isn't
  reshaped by this project, only terminal-cut, and Jost draws these the
  same way (`r`'s own two contours plus one more for the mark), so
  `quirks.py`'s existing terminal-cut indices for `r` just needed
  extending to their own glyph names.

- **A fourth axis, `GRAD` (Grade, -50 to 50)**, now exists too --
  v1 gets a real one for free, passed straight through to Roboto
  Flex's own native `GRAD` (drawn by that font's own designers); Jost
  has no such axis to draw from at all. `jost_source.extract` (and
  `arimo_source.extract`, for `s`) approximates it instead: sample
  Jost's own outline at a NEARBY `wght` (a fixed ratio of `grad` units
  to `wght` units, clamped to Jost's own 100-900 range) for SHAPE,
  while keeping the ADVANCE WIDTH from the requested `wght` itself --
  reusing gvar interpolation Jost's own designers already drew
  correctly, rather than a from-scratch outline-offset (stroke-
  emboldening) algorithm, which risks the same class of self-
  intersection failure this project has hit repeatedly with hand-
  rolled geometric transforms elsewhere. Confirmed directly: advance
  width is bit-for-bit identical at `GRAD`=-50/0/50 for a given
  `wght`/`wdth` while the ink visibly thickens/thins, and point
  topology stays identical across the whole grid (Jost's own gvar
  already guarantees this for any `wght` it samples). Not a true
  optical grade redraw the way a real one is (it doesn't hold stroke
  CONTRAST or x-height fixed independently of `wght`, since it's
  literally borrowing `wght`'s own interpolation to fake the effect),
  but the specific property `GRAD` exists for -- text reads
  bolder/lighter without reflowing a layout measured against the
  un-graded widths -- holds exactly, by construction. Triples the
  master grid from 12 to 36 (crossed with `GRAD_SAMPLES` the same way
  `wdth`/`SERF` already are).

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

**Foot sizing is measured off each master's own actual stem width, not
the reference instance's.** A real, visible defect the project owner
caught directly: at any weight thinner than the `wght`=400 reference
(most obviously Thin), feet sat wider than the stem itself and poked
out to both sides -- visible even at `SERF`=0, where a foot is meant to
be an invisible hairline. Root cause: a stem's own stroke thickness
shrinks with `wght` far faster than the glyph's overall advance width
does (a Thin letter is only modestly narrower end-to-end, even though
its stems are dramatically thinner), but `apply_feet` sized every
foot's base width off `detect_feet`'s reference-instance fraction
rescaled by THIS master's overall advance width -- treating "fraction
of total glyph width" as a stand-in for "fraction of stem width," which
only holds at the reference weight itself. Fixed by measuring the
actual flat-run width directly off each master's own already-built
glyph (`serifs.py::_actual_stem_width`) before appending any foot, so
the base rectangle sits flush with the real stem at every weight, not
just 400. Foot HEIGHT is now also hard-capped at that same real stem
width (`foot_h = min(foot_h, run_w)`) per the project owner's own
explicit requirement: a serif's stroke-perpendicular extension must
never equal or exceed the stroke it grows from, at any weight, not
just Black -- the old formula derived height from the same
wrongly-overshot width, so at Thin it could produce a foot taller than
the actual (thin) stroke itself, not merely wider. Confirmed by
rendering Thin, Regular, Black, and Thin+Condensed side by side with
`SERF`=100: feet now stay proportional to each master's own stem at
every point across the range, instead of only looking right at 400.

**The outward flare itself was halved** (`apply_feet`'s `extra`
coefficient, 0.9 -> 0.45) after a second round of direct inspection:
`A`'s two feet are geometrically mirror-symmetric (confirmed by
measuring the compiled font's own points, and by pixel-measuring a
real browser render -- both sides land on the exact same width), but
one side was getting clipped by the proof artifact's own display
container, making the unclipped side look twice as long by comparison.
Since the correctly-displayed (unclipped) length was itself judged too
prominent once seen in full, every foot's flare -- upper- and
lowercase alike, every letter -- was cut to half its previous length,
a single global scalar rather than a per-letter fix, so the whole
alphabet's feet move together and stay consistent with each other.

**Two more rounds after that, per further direct comparison**: the
flare was cut again, to 2/3 of THAT already-halved length (`extra`'s
coefficient 0.45 -> 0.3, i.e. 1/3 of the original 0.9), and the foot
HEIGHT formula was independently tightened specifically because it
still read as too tall at the thinnest weights even after the earlier
"cap it at the stem's own width" fix -- capping at the full stem width
still let a thin stem's foot reach roughly half that stem's own
thickness, visually chunky against a delicate stroke. Foot height's
own coefficient dropped 0.42 -> 0.28 and its cap tightened from the
full measured stem width to 40% of it (`run_w * 0.4`), so a foot reads
as a small nub relative to the stroke it grows from at every weight,
thin ones included, not a block half as tall as the stroke is wide.

**That height pass overcorrected.** The very next comparison called it
too short -- the flare length itself (`extra`, left at 0.3) was fine;
only the height needed to come back up. Foot height's coefficient
moved to 0.35 (was 0.42, then 0.28) and its cap to 60% of the measured
stem width (was 100%, then 40%), landing between the original,
too-tall setting and the too-short one that immediately followed it.

One real bug caught by rendering before this landed: a first version
grew a spurious extra foot on `n` where its left stem's short (~70-unit)
run-up into the arch happens to end flat and close enough to the
x-height ballpark to look like a genuine terminal. The root project's
own length threshold on the adjacent stem segment (must run at least
~150 units to count as a real stem side) rejects that short run
cleanly, the same guard that already keeps a foot from notching into an
arch letter's own counter.

Not yet done, in order:

- **Greek's own per-letter-class refinement and kerning**, and the
  remaining ~23 Cyrillic lowercase letters with no clean
  single-Latin-letter structural analog (`б в г д ж з и й к л н п т ф
  ц ч ш щ ъ ы ь ю я` -- see "Status" above). Greek itself is no longer
  missing (see "Status" above -- it's sourced from Roboto Flex now),
  but it carries none of `serifs.py`'s foot rules, `quirks.py`'s
  round-counter reshaping, or `kerning.py`'s pairs the way Latin and
  select Cyrillic do -- Roboto Flex's own outlines are a structurally
  different donor font (different point topology entirely) from Jost's,
  so `params.base_letter`'s NFD-decomposition/analog-table approach
  (which works by finding a shared STRUCTURE with an already-refined
  Jost/Arimo-derived Latin letter) has nothing to offer it, and its
  kerning would need extracting and merging a second donor's own GPOS
  table, not attempted here. `serifs.py`'s foot rules and
  `quirks.py`'s round-counter reshaping do extend to every accented
  Latin letter via `params.base_letter` (NFD decomposition), plus nine
  lowercase Cyrillic letters confirmed to share a Latin letter's
  structure (`_CYRILLIC_ANALOG`, same function), and terminal-cut
  treatment already covers the 18 accented `c`/`e`/`s`-based letters
  and 3 accented `r`-based ones (re-spliced/terminal-cut directly,
  since their base letters aren't Jost's raw shape to begin with). The
  rest of Cyrillic has no clean analog to map to -- forcing one onto a
  genuinely different letterform (a bridge/ladder shape like `н`/`п`,
  which looks like a lowercase Latin "H", not "n") would be worse than
  the generic unclassified default it already gets, which happens to
  be correct for those shapes. `GRAD` (see "Status") is done, if only
  an approximation of a true optical grade.
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

7,774 letter-pair corrections (`tools/kerning.py`), extracted from
vendored Jost's own GPOS pair-positioning table rather than hand-tuned
-- the same donor-kerning approach the repository root's own v1
pipeline uses on Roboto Flex, for the same reason: several thousand
pairs tuned by eye is its own multi-week type-design task, and Jost
already did that work. Covers every script this project's own
character set does EXCEPT Greek (Latin, Latin-1, Latin Extended-A,
Cyrillic -- Jost's own kerning table already has pairs for all of
them, the exact same donor-kerning logic the original 62-glyph ASCII
set already rested on, needing no new extraction work when the
character set grew -- see "Status" above), not just the original 62
ASCII letters/digits (533 pairs there alone). Greek is sourced from
Roboto Flex instead (see "Status" above), which Jost's own GPOS table
naturally has no glyphs for at all, so Greek pairs get excluded from
this extraction outright rather than merely unmatched -- a real fix
means extracting and merging a second donor's own kerning table,
not attempted here. Jost's own kerning is entirely static across
its `wght` axis (confirmed by diffing the full extracted table at
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
v2/tools/roboto_flex_source.py extracts Greek from the repo root's own vendored Roboto Flex
v2/tools/accent_marks.py       re-splices Jost's own diacritic marks onto this project's c/e/s
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
license (`v2/third_party/arimo/OFL.txt`). Greek is a Modified Version
of Roboto Flex, also under the SIL Open Font License, Version 1.1,
sourced from the repository root's own already-vendored
`third_party/roboto-flex/` (see that directory's own `OFL.txt`) rather
than vendoring a second copy under `v2/`. The root repository's
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
