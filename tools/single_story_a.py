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
"""

from __future__ import annotations

import ufoLib2


def build_from_d(d_glyph, xheight: float):
    """A new glyph named 'a', built from `d_glyph`'s own contours with
    the stem shortened to `xheight`. `d_glyph` itself is left untouched."""
    glyph = ufoLib2.objects.Glyph(name="a")
    glyph.copyDataFromGlyph(d_glyph)  # deep-copies contours/width, not name
    glyph.unicodes = [ord("a")]

    outer = glyph.contours[0]
    top_y = max(p.y for p in outer.points)
    for p in outer.points:
        if p.y == top_y:
            p.y = xheight
    return glyph
