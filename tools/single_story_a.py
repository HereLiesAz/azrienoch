"""Azrienoch's 'a': single-story, built directly from 'd's own outline.

Most grotesques (Roboto Flex included) draw 'a' as a double-story
letterform -- a small bowl low, capped by a separate ear/hook above.
That's the printed-book convention, not how most people actually write
the letter by hand: a single bowl with a stem, the same construction as
'd'/'b'/'p'/'q'. Azrienoch's 'a' follows that instead, built by
literally reusing 'd's own outline -- same bowl, same stem width and
position, same baseline -- with only the stem's top edge moved down
from ascender height to x-height (since, unlike 'd', 'a' has no
ascender). Nothing else about the shape changes: the only edit is
moving 'd's own existing top-of-stem points, never adding or removing
one, so this is exactly as topology-safe across every master as
`quirks.py`'s point-nudges are.

Built this way -- rather than drawn separately -- 'a' automatically
inherits everything 'd' already gets right, and flows through the rest
of the pipeline (SERF feet, dot detection) exactly like any other
imported glyph: by the time those run, it's just another glyph with a
flat-topped stem, no special-casing needed.

At Thin weight specifically (wght 100), cutting straight to `xheight`
would put the stem top BELOW the bowl counter's own natural top: 'd's
counter (contour 1) reaches y=874 at Thin while x-height itself is only
821 there -- the counter's own top is comfortably below x-height at
every other tested weight (a growing margin from wght 200 up), so this
is a Thin-only extreme, the same kind of corner `roboto_source.py`'s
XOPQ=27 fix and `round_contrast.py`'s neck-pinch already work around.
Left uncorrected, the counter would poke out through the top of the
shortened stem -- a self-intersecting outline, not just a visual defect.
`COUNTER_CLEARANCE` keeps the stem top at least this far above the
counter's own top when that's taller than `xheight`, so the outline
stays valid at every weight; everywhere else the counter is already
well clear and this has no effect.
"""

from __future__ import annotations

import ufoLib2

COUNTER_CLEARANCE = 20.0  # units of headroom kept above the counter's own top


def build_from_d(d_glyph, xheight: float):
    """A new glyph named 'a', built from `d_glyph`'s own contours with
    the stem shortened to `xheight` (or just clear of the counter's own
    top, if that's taller -- see module docstring). `d_glyph` itself is
    left untouched."""
    glyph = ufoLib2.objects.Glyph(name="a")
    glyph.copyDataFromGlyph(d_glyph)  # deep-copies contours/width, not name
    glyph.unicodes = [ord("a")]

    outer = glyph.contours[0]
    top_y = max(p.y for p in outer.points)
    target_y = xheight
    if len(glyph.contours) > 1:
        counter_top = max(p.y for p in glyph.contours[1].points)
        target_y = max(target_y, counter_top + COUNTER_CLEARANCE)
    for p in outer.points:
        if p.y == top_y:
            p.y = target_y
    return glyph
