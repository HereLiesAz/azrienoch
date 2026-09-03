"""Azrienoch v2's 'a': single-story, built directly from 'd's own outline
-- ported from the repository root's own `tools/single_story_a.py`
(same rationale: most grotesques draw 'a' as a double-story letterform,
a printed-book convention rather than how people actually write it by
hand; a single bowl-and-stem, same construction as 'd'/'b'/'p'/'q', is
what this project uses instead).

Jost's own 'd' is three independent contours -- a plain stem rectangle,
the bowl's outer silhouette, and its inner counter (already reshaped to
'o's own by `quirks.py::reshape_counter_to_o` by the time this runs) --
unlike Roboto Flex's fused stem+bowl outer contour, which is what root's
own version of this function has to search for the stem's top points
within. Jost's own separation makes this simpler: the stem is contour 0
outright, a 4-point rectangle, so shortening it is just moving its two
top points down, no search needed.
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
    glyph.copyDataFromGlyph(d_glyph)
    glyph.unicodes = [ord("a")]

    stem = glyph.contours[0]
    top_y = max(p.y for p in stem.points)
    target_y = xheight
    if len(glyph.contours) > 2:
        counter_top = max(p.y for p in glyph.contours[2].points)
        target_y = max(target_y, counter_top + COUNTER_CLEARANCE)
    for p in stem.points:
        if p.y == top_y:
            p.y = target_y
    return glyph
