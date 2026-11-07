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

Starting from Jost's actual outlines and
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
`tools/arimo_source.py`. `c`/`e` are built directly from this project's own `o`
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
against its own cmap), and no second donor font is used: its outlines
wouldn't share Jost's point topology for this project's per-letter-class
refinement to act on.

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
  letter's own letter-class dictates -- accented `n` (`ń ň ñ ņ`) drops the left stem's foot the same way
  plain `n`, which is `SINGLE_STORY`, does.
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
  (`tools/ring_derived.py`), not from a separate donor font, so their
  bowl/counter proportions agree with `o`'s BY CONSTRUCTION at every
  weight, width and serif setting. Three horizontal levels are
  read off Jost's own `e` at the same axis location: its crossbar's top
  and bottom edges, and the vertical midpoint of its lower-terminal
  cut. `e` is `o`'s ring with an upper bowl closed at the bar top (a
  separately-wound hole), a crossbar that runs straight out to the
  outer edge on the right, and an aperture from there down to a horizontal
  lower terminal. Per the project owner's direction, `c` shares those
  levels: its upper terminal is level with the top of `e`'s crossbar
  (where `e`'s bowl stops curving), its lower terminal level with
  `e`'s own.
  Every terminal and bar edge is exactly horizontal by construction,
  so neither letter goes through `quirks.py::apply_terminal_cuts`
  anymore. Each arc is emitted as a fixed number of tangent-matched
  quadratics sampled on `o`'s actual ring, so point count is identical
  at every master wherever the cuts land. `c` and `e` have no self-intersection at
  any of the 36 masters (checked by flattening every contour).
  Consequence of taking Jost's own `e` levels: at Black, Jost's bar sits
  low and `o`'s counter is small, so `e`'s aperture narrows to a slit.

- **V/W/M/v/w have one uniform stroke thickness**
  (`tools/stroke_balance.py`). Jost draws them Futura-style with
  unequal strokes -- `W`/`w`'s inner diagonals thinner than the outer
  ones, `M`'s diagonals not matching its stems -- and `condense.py`'s
  X-only compression changes each diagonal's perpendicular thickness by
  a different amount depending on slope. Per master, the outer
  silhouette points stay put (so advance width, sidebearings and
  kerning are unchanged), the glyph's first outer stroke sets the
  target thickness, and every inner point is recomputed so every other
  stroke matches it exactly, measured perpendicular to the stroke's
  own parallel sides. Point count and order are untouched. `M` also
  gets the overshoot every other pointed letter here has: Jost's `M`
  is the one whose middle vertex stops above the baseline while
  `V`/`W`/`v`/`w`'s vertices hang below it, so per the project owner's
  direction its middle vertex now drops to the same master's own `V`
  bottom-vertex depth, with each diagonal re-solved between its apex
  and that vertex.

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

- **`six`/`nine` carry a small notch where the bowl meets the
  ascender/descender stroke in Jost's own outlines**, found by a
  self-intersection sweep across the full `wght`x`wdth`x`SERF` grid;
  `quirks.fix_six_nine_notch` moves the offending points to where the
  geometry meets. Two further findings, digit `4`'s technically
  self-intersecting crossbar/stem
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

## Drawn glyphs

`Y` and `y` are drawn by hand, not derived from Jost: one cubic outline
each at Thin (`wght` 100), Regular (400) and Black (900), kept as
Morphont projects in `sources/drawn/` (`Y.morphont.json`,
`y.morphont.json`). The sweep of the diagonal into the stem or the
descender curl is the design. `tools/drawn_glyphs.py` places them at every
master: weight blends linearly between the drawn weights (shifted by `GRAD`
as for every other glyph, with the advance following the requested `wght`),
`wdth` runs through the same `condense.py` compression, and `SERF` feet go
on afterwards as for any glyph. The three drawings have identical points in
identical order, so all 36 masters stay interpolation-compatible.

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

Measuring a stem at a given master uses a 1-unit noise floor, not the
10-unit floor used to DETECT stems on the reference instance: a Thin
Condensed stem is only ~8 units wide, and the detection floor used to
filter it out, silently dropping every Thin Condensed foot onto a
fallback width several times the real stem and off-center.

`n`'s short (~70-unit) run-up into the arch ends flat near the x-height, which could read as a terminal and grow a spurious extra foot. A length threshold
on the adjacent stem segment (must run at least ~150 units to count as
a real stem side) rejects that short run cleanly, the same guard that
already keeps a foot from notching into an arch letter's own counter.

## Kerning

Derived per master from Azrienoch's own outlines (`tools/kern_derive.py`),
for the 62 base letters/digits; accented and Cyrillic glyphs that
`params.base_letter` maps onto a base letter inherit that pair's value
(`kern_derive.inherit`), and every other pair keeps Jost's donor value
(`tools/kerning.py`, 7,774 pairs extracted from Jost's own GPOS table,
scaled by `wdth`; static across `wght`).

Derived method: each pair is scanned every 10 units of height; the
horizontal gap at each height (open space counts as a cap, `GAP_CAP`
280 x `wdth` fraction) is averaged over the pair's band (cap height if
either glyph is a capital or digit, else x-height). That optical gap is
moved toward H-H (capital pairs), n-n (lowercase), or their mean
(mixed) by `STRENGTH` 0.75, clamped to -250..80, raised so the closest
approach never drops under `MIN_CLEAR` 80 (x `wdth` fraction), and
dropped under 5 units. A->Y is an owner override (`PAIR_TIGHTEN`): strength x1.67,
clearance 20, giving -150 at Regular (Y->A, Y->s share it: -47 at Regular -- Y's stem meets A's apex at -150). Pairs touching a diagonal glyph (A K M V W X Y Z k v w x y z) never get a positive kern; J's empty left side above its hook is treated as filled out to the hook's leftmost point. An area measure is used rather than the closest
point because a pair that opens into a wedge (A-Y, T-o) reads looser than
its minimum gap, the effect the proof's O-Y entry records.

Calibration: `GAP_CAP` and `STRENGTH` were fitted to the pair values
approved in the proof's Kerning section (A-W, W-A -100; A-Y -70; T-O
-50; O-Y -100) at wght 400 / wdth 100. Worst residual ~40 units: the
model cannot give A-Y -70 while O-Y is -100, so at Regular it yields
A-W/W-A/A-Y -90, T-O -71, O-Y -77. Values now vary with `wght`, `wdth`
and `SERF`.

## S terminals

Jost's `S` cuts both terminals on the diagonal; `s` (Arimo) is cut
horizontal. `quirks._HORIZONTAL_TERMINALS` now lists `S` (contour 0,
points 0-1 lower-left, 26-27 upper-right) so both letters match.
Verified: every one of the 36 masters has both cuts at identical Y.
The rigid re-spread of a steeply diagonal cut overhung the bowl (x = -12.8
at wght 900, wdth 75), so the letter read as tipping over.
`quirks._TERMINAL_X_LIMITS` slides each cut inward, length kept, until it
sits inside the upper bowl's leftmost / lower bowl's rightmost point.
Verified: min x over all 36 masters is 34.7.
