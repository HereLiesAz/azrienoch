# Design

## Where the letterforms come from

Glyph outlines are copied directly from the vendored
[Jost](https://github.com/indestructible-type/Jost) variable font
(`third_party/jost/`, SIL OFL 1.1 -- license copied to
`third_party/jost/OFL.txt`), a real, professionally drawn geometric
sans. Jost's own license explicitly permits exactly this: using,
studying, modifying and redistributing the font. `tools/jost_source.py`
instances the vendored font at a given `wght` via
`fontTools.varLib.instancer` and extracts each glyph's real outline and
advance width; `tools/ufo_build.py` copies that data into Azrienoch's
own UFO masters, then layers Azrienoch's own modifications on top.

An earlier version tried building every letterform from scratch out of
two primitives (a straight polygon, a pair of concentric ovals) instead
of starting from a real drawn typeface. It compiled and interpolated
correctly, but the letterforms it produced (particularly `n`'s arch and
`v`'s diagonal join) didn't hold up -- real type design encodes a lot
of judgment calls (a counter's exact curvature, where a diagonal's
thick/thin sides fall) that a from-scratch geometric formula kept
getting wrong in ways that were each individually fixable but never
added up to a typeface. Starting from Jost's actual outlines and
modifying them from there is the current approach.

Jost only exposes a `wght` axis (100-900); it has no `wdth` axis to
draw from. `wdth` goes through `tools/condense.py`'s per-x, ink-density
weighted compression rather than a flat `x *= wf` scale -- a flat scale
thins a stem by the same factor it narrows a counter, which reads as an
obvious squish rather than a condensed cut at heavy weight (a stem's
X-extent shrinks with the scale, a horizontal stroke's Y-extent
doesn't, so the two drift out of proportion the heavier and more
condensed a master gets). This still isn't a true optically condensed
redraw (no counter is actually reshaped, and it's a single global
compression curve applied the same at every height, so a diagonal
stroke's x position only gets partial credit for the ink it carries) --
see "Not yet done" below.

`s` is the one exception: it's pulled from
[Arimo](https://github.com/googlefonts/arimo) instead (vendored at
`third_party/arimo/`, SIL OFL 1.1) -- an open, metric-compatible
Helvetica/Arial workalike -- because it's meant to specifically read as
Helvetica-derived. Real Helvetica outline data is proprietary
(Linotype/Monotype) and was never traced or extracted here; Arimo is a
freely licensed font used and modified exactly as its license permits,
the same legal basis this project uses Jost on. See
`tools/arimo_source.py`. `c`/`e` used to be sourced from Arimo the same
way, but are now built directly from this project's own `o` instead
(`tools/ring_derived.py` -- see below).

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
  serve one fixed voice. That idea is what `wght`/`wdth` in this
  project are for -- see "Design goal" below.

## Design goal

The brief: a font that makes it *easy* to find creative ways to fit
text together across multiple lines and multiple weights/widths --
lockups, not just paragraphs. One structural fact serves that
directly: **Jost's own vertical metrics are fixed across its entire
`wght` range** (confirmed directly against the vendored font -- `H`'s
bounding box is `(_, 0, _, 700)` and `o`'s top is ~470-471 at `wght`
100, 400 and 900 alike). A Thin line and a Black line already share a
baseline and x-height with no work on Azrienoch's part, which is
exactly what makes mixed-weight lines stack and align without
per-weight compensation. `tools/params.py`'s `CAP_HEIGHT`/`X_HEIGHT`
constants just document that fact for the build; they don't override
anything.

## Axes

See [`axes.md`](./axes.md) for the full table. In short: `wght`
(100-900) and `wdth` (75-100) sample Jost's own outlines (plus
`condense.py`'s compression for `wdth`); `SERF` (0-100) grows a slab
foot from nothing (see "Serif feet" below); `GRAD` (-50 to 50)
approximates a grade axis Jost has no native equivalent for, by
sampling a nearby `wght` for shape while holding the requested
`wght`'s own advance width fixed -- confirmed directly: advance width
is bit-for-bit identical at `GRAD`=-50/0/50 for a given `wght`/`wdth`
while the ink visibly thickens/thins. Not a true optical grade redraw
(it doesn't hold stroke contrast or x-height fixed independently of
`wght`, since it's literally borrowing `wght`'s own interpolation to
fake the effect), but the specific property `GRAD` exists for -- text
reads bolder/lighter without reflowing a layout measured against the
un-graded widths -- holds exactly, by construction.

Every master in the grid (`tools/params.py::MASTER_GRID`, 36 points:
3 `wght` samples x 2 `wdth` x 2 `SERF` x 3 `GRAD`) is also an `fvar`
named instance, with a proper STAT table axis-value label per stop, so
a style picker lists every named style instead of only the implicit
default.

## Status

339 glyphs -- the basic Latin alphabet (`A`-`Z`, `a`-`z`), digits
(`0`-`9`), punctuation, Latin-1 Supplement, Latin Extended-A, and
Cyrillic. All of it is copied from Jost across all 36 masters (except
`c`/`e`, built from this project's own `o`, and `s`, sourced from
Arimo), with Azrienoch-specific modifications (`tools/quirks.py`) on
top for the original 62 ASCII letters/digits, extended to accented
Latin and select Cyrillic letters too (see below). No Greek: Jost
itself has almost none of it (4 codepoints total, confirmed directly
against its own cmap), and sourcing it from a second donor font was
tried and then dropped by direct decision -- a structurally different
donor's outlines don't share Jost's point topology for any of this
project's own per-letter-class refinement to find anything, so Greek
would have carried none of it anyway.

Jost's own accented glyphs that are TrueType composites (a base letter
plus a separately drawn diacritic component, e.g. `Ohungarumlaut`) are
decomposed on extraction (`jost_source.py` uses fontTools'
`DecomposingRecordingPen`, not a plain one) so every downstream
consumer only ever sees plain outline data, never a component
reference.

- **`quirks.py`'s round-counter reshaping and `serifs.py`'s
  per-letter-class foot rules extend to every accented Latin letter**,
  not just the original 62 ASCII letters/digits, via `params.base_letter`
  -- Unicode NFD decomposition strips a letter's own combining accent
  (`ē` -> `e`, `ō` -> `o`, `ń` -> `n`), so an accented glyph gets
  exactly the same classification its plain base letter does: `ō`'s
  counter is reshaped to match `o`'s own, and every accented letter
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
  needed). `r`'s own three accented variants (`ŕ ŗ ř`) need no
  re-splicing -- `r` isn't reshaped by this project, only terminal-cut,
  and Jost draws these the same way (`r`'s own two contours plus one
  more for the mark), so `quirks.py`'s existing terminal-cut indices
  for `r` just needed extending to their own glyph names.

- **`c`/`e` are built directly from this master's own `o`**
  (`tools/ring_derived.py`), not from a separate donor font. `o`'s own
  outer+inner ring is cut open (an aperture for both, plus a straight
  crossbar for `e`) via exact quadratic-Bezier subdivision at a fixed
  angle from the ring's own center -- every point either glyph keeps is
  therefore pixel-identical to `o`'s own, and their bowl/counter
  proportions agree with `o`'s BY CONSTRUCTION, at every weight, width
  and serif setting, with no matching required. This replaces an
  earlier approach (`c`/`e` sourced from Arimo, like `s` still is) that
  spent two rescale attempts trying to match `c`/`e`'s ADVANCE WIDTH to
  Jost's own `ch`-to-`o` ratio and reverted both (a flat scale fattened
  the terminal at Thin; a centroid-radial push fixed that but pinched
  the counter into an hourglass waist at Black -- see git history for
  the full account) without ever fixing the actual root cause: Arimo is
  a different font with different proportions than Jost, so no amount
  of width-matching could make its `c`/`e`'s counter SHAPE agree with
  `o`'s. Deriving them from `o` directly -- the same move already made
  for `a` (built from `d`'s own outline, see below) -- fixes that at
  the source. `e`'s upper bowl is a proper, separately-wound hole (same
  two-contour structure as `o` itself), closed below by the crossbar
  rather than a curve; its lower counter merges into the outer
  silhouette's own single contour, open to the outside through the
  aperture, the same way `c`'s counter is single-contour. Both go
  through `quirks.py::apply_terminal_cuts` too, same as Arimo-sourced
  `s`: Bezier subdivision at an exact target angle doesn't land the two
  straight cuts closing the aperture perfectly flush, so they're
  reoriented to true horizontal the same way Arimo's own terminals are.
  One known residual: at `wght`=100 combined with `wdth`=75 (Thin
  Condensed, the single most extreme corner of the whole design
  space), `e`'s stroke wall gets thin enough at the aperture that its
  terminal folds into a tiny self-intersecting spike -- confirmed
  directly by rendering that specific corner. Not yet fixed: the
  aperture's angle is fixed relative to the ring's own center, but
  `condense.py`'s width compression is non-uniform (X only), so the
  wall thickness at that fixed angle can shrink much faster than the
  letter's overall proportions would suggest at extreme corners.

- **`s` is sourced from Arimo, not Jost**: it's meant to read as
  Helvetica-derived, and has no ring or counter to derive from `o` the
  way `c`/`e` now are. Arimo's own terminal there is close to
  horizontal but genuinely diagonal by design, so it still goes through
  `quirks.py::apply_terminal_cuts`, just with Arimo's own point indices
  instead of Jost's. Arimo ships only as static instances
  (Regular/Bold, not a variable font); `arimo_source.py`
  interpolates/extrapolates between their point coordinates directly
  for this project's own `wght` samples, confirmed safe to do
  point-for-point since `s` has identical point-command signatures
  between the two vendored weights. `s`'s WEIGHT is calibrated against
  Jost's own original `s`, not Arimo's own Regular/Bold labels --
  `arimo_source.py` measures Jost's own original `s`'s stroke-width
  ratio at the target `wght` and solves for the Arimo interpolation
  parameter that scales Arimo's own `s` stroke width by that same
  ratio, so weight tracks Jost's own curve while shape comes from
  Arimo. `s`'s advance width still doesn't track `o`'s own
  `wght`-relative proportions -- unlike `c`/`e`, `s` couldn't be
  derived from `o` (an S-curve has no ring to cut open), so it's still
  only width-matched by whatever Arimo's own Regular-Bold blend happens
  to produce.

- **A stability audit's self-intersection sweep across the full
  `wght`x`wdth`x`SERF` grid** caught genuine defects inherited
  byte-for-byte from the vendored Jost outlines (none introduced by
  this project's own extraction or modification code): `y` had a
  visible hole at its crotch (its two diagonal strokes' inner edges
  terminated a few units past their actual crossing point instead of
  meeting it exactly); `six`/`nine` each had a small notch where the
  bowl meets the ascender/descender stroke. Both fixed in `quirks.py`
  (`fix_y_crotch`/`fix_six_nine_notch`) by moving the offending points
  to where the geometry actually intends them to meet. Two further
  findings, digit `4`'s technically self-intersecting crossbar/stem
  junction and capital `B`'s technically self-intersecting waist (two
  overlapping, collinear spine segments in its single-contour
  "keyhole" construction), were both confirmed by direct rendering --
  not just the geometric self-intersection test that first flagged
  them -- to draw with no visible artifact at every weight/width
  combination checked (a harmless retrace/T-junction under
  nonzero-winding fill). Needed no fix.

- **Every terminal reorientation** (`quirks.py::_reorient_cut`, used
  for `c`/`e`/`s`'s horizontal cut and `r`/`f`'s vertical one)
  transforms not just the two terminal points but the whole run of
  off-curve control points leading into each one, via a similarity
  transform (rotate + scale, pivoting on that curve's own anchor point)
  rather than a plain translation: a translation left the control point
  the same distance from its anchor regardless of how far the terminal
  itself had to move, which overshot into a self-intersecting notch at
  heavy weight.

- **Every round-bowled lowercase letter's inner counter is a true
  affine-scaled copy of `o`'s own inner counter**: `b`, `d`, `p`, `q`,
  `g` (Jost's own `o`/`b`/`d`/`p`/`q`/`g` all share an identical
  16-point contour shape for exactly this reason). Not extended to `a`
  (its inner contour also carries the points where the counter joins
  the stem, so it doesn't structurally match as a whole contour the
  way the others do). `c`/`e` are no longer Jost-derived at all (see
  above) so this doesn't apply to them.

- **`a` is single-story, built directly from `d`** (`tools/single_story_a.py`):
  a fresh copy of `d`'s own three contours (Jost draws `d` as an
  independent stem rectangle, bowl outer, and inner counter) with the
  stem's top edge moved down from ascender height to x-height (or just
  clear of the counter's own top, if that's taller at extreme weights).

## Not yet done

In order:

- **A true optically condensed `wdth` cut.** `condense.py`'s ink-density
  weighted compression keeps stems close to their full width at
  heavy/condensed combinations instead of uniformly squishing them, but
  it's still a global per-x warp with no counter actually reshaped -- a
  real condensed cut redraws counters and adjusts spacing by hand,
  which this project doesn't do.
- **`s`'s advance width doesn't track `o`'s own `wght`-relative
  proportions** (see "Status" above). `c`/`e` no longer have this
  problem (both now derive their whole shape, width included, from
  `o` directly); `s` still can't, since an S-curve has no ring to cut
  open the way `c`/`e` do.
- **`e`'s aperture terminal self-intersects at the single most extreme
  corner of the design space** (`wght`=100 combined with `wdth`=75 --
  see "Status" above for why).
- **~23 Cyrillic lowercase letters have no clean single-Latin-letter
  structural analog** (`б в г д ж з и й к л н п т ф ц ч ш щ ъ ы ь ю я`
  -- see "Status" above) and are deliberately left on the generic
  unclassified default rather than forced into a wrong analog.
- **`s` at Thin (`wght`=100, any `wdth`) has its own near-zero ring-wall
  pinch** (~0.002 units, pre-existing on the plain Cartesian-
  interpolated shape itself). `s` can't take the same fix `c`/`e` got
  (an S-curve has no ring to derive from `o`), so its own extreme
  `wght`=100 alpha still moves points along each one's own
  Regular-to-Bold straight line. Not fixed; a real, if narrow and
  currently invisible, residual.

## Serif feet

**A variable `SERF` axis** (0-100, sans by default, `tools/serifs.py`)
grows a slab foot the same way `wght` grows stroke thickness: detect a
flat stem terminal once on a reference instance (`wght`=400,
`wdth`=100), and at every master append a same-wound rectangle contour
there (collapsed to a hairline at `SERF`=0, a full slab at `SERF`=100),
rather than relocating the stem's own points -- appending same-wound
ink can only ever add, never accidentally flip a fill relationship.
Which terminal(s) get a foot, and which direction each one flares,
follows a handwriting-inspired rule:

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
  stem, but each one flares only away from the letter's OTHER stems:
  the leftmost stem at a guide flares left only, the rightmost flares
  right only, a lone stem at that guide flares both ways, and anything
  strictly between two others doesn't flare at all -- this is what
  keeps `H`/`R` from flaring each stem toward the other, into the
  counter.
- `o`/`c`/`e`/`s` -- fully round letters, all four declared
  `SINGLE_STORY` -- get NO foot at any `SERF` value: a round bowl has
  no flat stem run anywhere on it, the same structural limitation as
  `g`'s curved descender hook.

Foot sizing is measured off each master's own actual stem width, not a
reference instance's fraction of the glyph's overall advance width --
a stem's own stroke thickness shrinks with `wght` far faster than the
glyph's overall advance width does, so a size derived from the wrong
quantity sat wider than the actual stem at Thin, visible even at
`SERF`=0 where a foot is meant to be an invisible hairline. Foot HEIGHT
is capped at that same real stem width -- a serif's stroke-
perpendicular extension never equals or exceeds the stroke it grows
from, at any weight -- and its own formula interpolates from the
hairline (`SERF`=0) straight to a fully-proportional target
(`SERF`=100, an exact fraction of the real stem width) rather than
adding a flat bonus on top of that fraction, which would otherwise
matter disproportionately more on a thin stem than a thick one. The
outward flare itself is a modest fraction of the stem's own width, the
same scalar applied to every letter -- upper- and lowercase alike --
so the whole alphabet's feet move together and stay consistent with
each other.

One real bug caught by rendering before this landed: a first version
grew a spurious extra foot on `n` where its left stem's short (~70-unit)
run-up into the arch happens to end flat and close enough to the
x-height ballpark to look like a genuine terminal. A length threshold
on the adjacent stem segment (must run at least ~150 units to count as
a real stem side) rejects that short run cleanly, the same guard that
already keeps a foot from notching into an arch letter's own counter.

## Kerning

7,774 letter-pair corrections (`tools/kerning.py`), extracted from
vendored Jost's own GPOS pair-positioning table rather than hand-tuned:
several thousand pairs tuned by eye is its own multi-week type-design
task, and Jost already did that work. Covers the full character set
this project uses (Latin, Latin-1, Latin Extended-A, Cyrillic -- Jost's
own kerning table already has pairs for all of them), not just the
original 62 ASCII letters/digits (533 pairs there alone). Jost's own
kerning is entirely static across its `wght` axis (confirmed by
diffing the full extracted table at `wght`=100/400/900: zero pairs
differ), so one extraction is reused at every master, scaled only by
that master's own `wdth` fraction (kerning has no direct `SERF`
dependence either). `c`/`e`/`s` (no longer all Jost's own outlines --
`c`/`e` are built from `o`, `s` from Arimo) keep Jost's own kerning
values for pairs involving them regardless, a stand-in on the same
donor-kerning logic the rest of the module rests on. `a` (built from
`d`'s own contours, not Jost's separately-drawn `a`) gets `d`'s
kerning, not Jost's native `a`'s -- Jost's own `d` happens to carry no
class-kerning pairs at all, so `a` ends up unkerned too, the more
consistent outcome given it now shares `d`'s exact shape.
