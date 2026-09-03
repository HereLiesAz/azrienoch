# Design

Azrienoch's letterforms, spacing and kerning come from
[Roboto Flex](https://github.com/googlefonts/roboto-flex) (SIL OFL 1.1),
not from a from-scratch drawing. Roboto Flex is real, professionally
hinted and kerned type-design engineering, with nine independent
"parametric" axes controlling stroke weight and vertical proportions
separately from its registered `wght`/`wdth` axes. Azrienoch's own work
is in what it does with that space.

This repository previously held
[Graduate](https://github.com/etunni/Graduate-Variable-Font), a
12-axis variable font by Eduardo Tunni that served as this project's
model for how far a single variable font's axis system can go.
Azrienoch replaces it: same ambition for axis versatility, a different
letterform foundation and a narrower, more deliberate set of axes (see
[`axes.md`](./axes.md)).

## Height as a matter of weight

Roboto Flex deliberately keeps weight and height independent -- that's
the whole point of exposing eight parametric axes (`XOPQ`/`YOPQ` stroke
weight, `XTRA` counter width, `YTUC`/`YTLC`/`YTAS`/`YTDE`/`YTFI`
cap/x/ascender/descender/figure height) separately from `wght`/`wdth`.
Azrienoch deliberately does the opposite: its `wght` axis is mapped
onto a correlated path through that same eight-axis space (see
`tools/roboto_source.py::_HEIGHT_AXES_AT_WGHT`), so cap-height,
x-height and stroke weight all grow together. A heavier Azrienoch
instance is a genuinely *taller* one, independent of the type size or
line height the reader chooses.

## A variable serif axis (`SERF`, 0-100)

Roboto Flex has no serifs. `tools/serifs.py` scans one reference
instance for short, already-flat horizontal stem terminals (round
strokes never present one, so bowls and curves are naturally skipped)
and grows a slab foot on each, driven by the `SERF` axis. Azrienoch is
sans by default.

Each foot only grows on the side(s) that border a real stem rather than
the letter's own counter (checked via the adjacent contour segment's
length), which is what keeps it from notching into arch letters like
'n'/'m'/'p'/'r'/'h'.

## A grade axis (`GRAD`, -50-50) for optical compensation, not redesign

Unlike `wght`, Roboto Flex's `GRAD` changes stroke weight without
touching advance widths or glyph metrics at all -- it's designed to be
nudged live (dark text on a light ground can read thinner than light
text on a dark ground at the same nominal weight) without reflowing a
single line of text. Azrienoch passes it straight through to Roboto
Flex's own `GRAD` (see `roboto_source.roboto_location`), narrowed to a
safer slice of Roboto's full -200..150 range.

## Automatic, weight/width-aware spacing and kerning

Advance widths and kerning are extracted straight out of Roboto Flex's
own `hmtx` and (per-master, since it's decompiled from a fully
instanced, therefore static, `GPOS`) `kern` feature at each of
Azrienoch's master locations -- see
`tools/roboto_source.py::extract_kerning`. That inherits Roboto Flex's
own tuning: pairs tighten at heavier weights and stay legible when
condensed, without Azrienoch reimplementing an optical-kerning
algorithm of its own.

## A horizontal-terminal design principle

Roboto Flex's own grotesque terminals are meant to be cut flat
(horizontal or vertical), not on the stroke's own angle -- Azrienoch's
slab serifs follow the same rule (they're rectangles, by construction).
'c' already cuts both its openings flat, which is what exposed 'e'/'g'
as exceptions: 'e's lower-right opening and 'g's descender-tail hook
both turned out to end in a genuine diagonal cut instead, growing
sharply with weight. `tools/quirks.py` fixes both by moving one
existing point's Y to match its neighbor's -- no new points, so
topology stays exactly what gvar needs across every master.

## Counters pushed wide at every weight

Roboto Flex's `XTRA` axis controls counter width independently of
stroke weight; Azrienoch's `wght` mapping deliberately keeps `XTRA`
generous even at Black (`tools/roboto_source.py::_HEIGHT_AXES_AT_WGHT`),
refusing the usual trade where the heaviest weight lets its ink crowd
the void out. The counter is a considered shape, not leftover space.

## A couple of barely-noticeable Akzidenz-Grotesk quirks

`tools/quirks.py` makes two small, targeted edits on top of the
imported outline: 'G' gets a proper hanging spur (Roboto Flex's own
crossbar, extended), and 'R' gets a subtly flared, kicked-out leg,
instead of a plain conservative one. Both are computed relative to the
glyph's own local geometry (a multiple of its own bar thickness or leg
width) so they scale with weight and width instead of needing tuning
per master, and both only ever move existing points -- never add or
remove one -- so they don't touch the topology gvar interpolation
depends on.

## A genuinely sharp bottom point on 'v'/'w', at every weight

Roboto Flex doesn't draw the point where 'v'/'w's two diagonals meet as
a single vertex -- it's a short flat baseline segment between two
separate on-curve points, and that segment widens aggressively with
weight (imperceptible at Thin, hundreds of units wide by Black),
reading as a blunt, flattened bottom rather than the sharp
Akzidenz-reminiscent point this design wants to keep. `tools/quirks.py`'s
`_sharpen_baseline_notches` collapses both endpoints of that segment
onto their own shared midpoint at every master -- both already sit
exactly on the baseline, so only X moves, and the two points become
coincident: a true zero-width vertex, still with the same point count.

Because `apply_quirks` runs before `tools/serifs.py`'s foot detection,
this also fixes a second bug as a side effect: with the segment
flattened to zero width, it no longer meets `serifs.py`'s minimum-run
threshold, so 'v'/'w's point no longer picks up a spurious slab foot at
`SERF` > 0 the way a real stem terminal would.

## Dots that read as a mark, not a fleck -- and don't fuse into the stroke beside them

Two separate fixes here, both in `tools/dots.py`.

First, Roboto Flex's period/colon/semicolon/tittle/exclam/question dots
barely grow with `wght` the way stems do, so they read as an
afterthought next to Azrienoch's already-wide counters -- every dot
Azrienoch imports gets scaled up around its own centroid, by an amount
that tapers from a real lift at Thin down to none at all by Bold/Black,
where Roboto Flex's own dots are already a reasonable size and boosting
further would crowd a colon's two dots into each other.

Second, and unrelated: Roboto Flex's own 'i'/'j' tittle sits low of
where letters like h/d/b/k/l actually top out, and at Bold and
especially Black weight sits close enough to the stem beneath it that
the two read as one fused shape rather than a stem with a dot above it.
Moving the tittle straight up so its top lands exactly on that true
ascender height (measured off 'h' itself, not the font's own much
taller `hhea.ascender` line-spacing metric) fixes both at once.

## A single-story 'a', built from 'd'

Roboto Flex, like most grotesques, draws 'a' as a double-story
letterform -- a small bowl low, capped by a separate ear/hook above --
the printed-book convention, not how most people actually write the
letter by hand. `tools/single_story_a.py` builds Azrienoch's 'a' the
way a single-story 'a' is actually constructed: as the exact same
bowl-and-stem shape as 'd', just with the stem shortened from ascender
height down to x-height (since, unlike 'd', 'a' has no ascender). It's
not drawn separately -- it's literally 'd's own outline with its
topmost points moved down, so it inherits 'd's proportions exactly and
flows through the rest of the pipeline (SERF feet included) the same
way any other imported glyph does. Its kerning is 'd's too, not the
pairs Roboto Flex tuned for the old double-story shape: `ufo_build.py`
overwrites every kerning pair keyed to 'd' with an equivalent one keyed
to 'a' before the master's kerning is filtered down and saved.

## 'o'/'c'/'e' thinned at top and bottom, to match a bowl's own neck

Roboto Flex draws a full circle's curve and a bowl letter's curve at
two different thicknesses even though they're the same family of
shape: 'o'/'c'/'e' read visibly heavier at their vertical extremes than
the wall of 'd'/'b'/'p'/'q's bowl does right where it meets the flat
stem. `tools/round_contrast.py` compares both contours' own Y-extremes
directly (both are already on-curve points there, so no curve
flattening is needed for this particular measurement) and moves only
'o'/'c'/'e's own inner top/bottom points toward the outer edge, in the
same proportion the neck is thinner at the one weight (Regular) where
measuring the neck itself is reliable -- at Thin, Roboto Flex's own
neck pinches to nearly nothing, a genuine corner of its design space
rather than something to match exactly.

## Symmetric arch counters ('n'/'h'/'m'/'u')

Roboto Flex springs the curve of an arch letter from its two stems at
two different heights -- 'n's left stem meets its arch 84 units higher
than the right stem does -- which reads as a lopsided negative space
even though the letter's outer silhouette is close to symmetric.
`tools/arch_symmetry.py` finds each such spring pair generically (a
real stem meeting a curve, sanity-checked against unrelated springs
like 'h's ascender) and moves each to the pair's average height,
translating the one adjacent off-curve control point along with it so
the curve's local shape stays smooth rather than kinking.

## The same true oval, everywhere a counter is round

Even after the neck-thinning above, 'o's counter (and 'd'/'b'/'p'/'q'/
'g'/'a's, all built the same way) still read as a rounded square rather
than a genuine oval: Roboto Flex draws these as four quadrant curves
bridged by a short flat "waist," proportionally tiny on the outer
contour but a much bigger fraction of the smaller counter inside it.
`tools/canonical_counter.py` fixes this structurally instead of
shrinking the waist: 'o's own outer contour is already the design's
reference for "genuinely round," and every one of these counters turns
out to share its exact 14-point structure, just cyclically rotated to
a different start point. Every matching counter is rebuilt as a true
affine-scaled copy of 'o's own outer contour -- same size and position,
only the shape changes -- with the winding direction verified (and
corrected by mirroring, which costs nothing on a round shape) so the
result still renders as a hole rather than solid fill. 'e'/'c' aren't
included yet: their outer and inner boundaries share a single open
contour, which needs a different approach than this one.

## Arch letters' counters ('n'/'h'/'m'/'u') round to match

These don't have a separate counter contour to reshape the way a bowl
does -- the counter is bounded by a curve embedded in the letter's own
single outer contour, spanning between the two spring points
`arch_symmetry.py` finds. `tools/arch_shape.py` extends the same "copy
'o's own shape" idea to this open case: that span turns out to share
'o's own 7-point half-oval structure exactly, at every weight, for all
four letters. Since the spring points are shared with the stems and
can't move, this solves the similarity transform (rotation + uniform
scale, exactly determined by the two fixed spring points) that maps
the template's matching span onto them, then applies it to the points
between -- verified to bulge to the correct side of its own chord (not
assumed from how it looked for one letter: an early version relied on
a plain rotation, which happened to look right for 'n'/'h' but visibly
flattened 'u').

## A `matplotlib` bug found while checking the dot/counter match

`Path.interpolated()` -- used in a couple of places to "flatten" a
curve for measurement -- doesn't evaluate curve segments at all (its
own docstring says so): it linearly interpolates the raw vertex array,
so a circle's own control polygon comes back an octagon. Visual
rendering was never affected (matplotlib's renderer evaluates curves
correctly when drawing), only code calling `.interpolated()` to get
points back out for measurement or point-in-polygon tests was.
`preview.py::flatten_path` is a real bezier sampler; `canonical_counter.
py`'s outer/inner detection no longer needs to flatten at all
(`Path.contains_point` is already curve-aware called directly).

## Overall character

The letterform character overall aims for an analytical neo-grotesque:
Roboto Flex's own modern, systematic proportions, read with some of
Helvetica's rational flat-terminal directness.
