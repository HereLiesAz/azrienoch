"""Round off counters that read as a "rounded square" instead of a
curve matching the glyph's own outer roundness.

Roboto Flex draws a circle (and any bowl counter built the same way) as
four quadrant curves joined by a short straight "waist" segment at each
of the four compass points -- e.g. 'o's outer contour has a ~32-unit
flat run on its left and right sides, bridging the top and bottom
quadrant curves. That's proportionally tiny on the outer contour (about
2.8% of its width) but Roboto Flex draws the *same absolute* ~32-unit
waist on the smaller counter inside it -- about 4% of the counter's
width, and enough to read as a flattened, squared-off side next to the
outer contour's genuinely round one.

``round_off_waists`` finds these short straight runs generically (a
'line' segment, short, with a curve on both sides -- not a long straight
run, which is a real edge like a bowl's wall facing its own stem, not an
artifact) and shrinks them toward their own midpoint, closing most but
not all of the flat gap. It only ever moves the two points that already
form the run, so it doesn't touch topology.

Applied to every contour except the outer one, on any glyph with more
than one contour -- the counter/hole contours, never the outer
silhouette, which is the shape this is trying to match in the first
place. "Except the outer one" is not the same as "except contour 0":
Roboto Flex's own contour order isn't reliably outer-first (confirmed at
Thin, wght 100, where 'o' has its smaller-bbox contour first), so the
outer contour is found the same way `round_contrast.py` finds it -- the
one that reaches the glyph's global max Y, which a strictly-enclosed
inner contour never can. Glyphs where the outer and inner boundaries
share a single contour (e.g. 'c', 'e') aren't touched here, since
there'd be no safe, generic way to tell which of that contour's short
runs are the outer silhouette's and which are the counter's without
risking the wrong one.
"""

from __future__ import annotations

import math

MAX_WAIST_LEN = 60.0  # units; longer than this is a real edge, not a waist artifact
SHRINK_TO = 0.15  # fraction of the original waist length kept, not eliminated


def round_off_waists(glyph, shrink_to: float = SHRINK_TO) -> None:
    contours = glyph.contours
    if len(contours) < 2:
        return
    global_top = max(p.y for c in contours for p in c.points)
    outer = next(c for c in contours if any(p.y == global_top for p in c.points))
    for contour in contours:
        if contour is outer:
            continue
        pts = contour.points
        n = len(pts)
        for i in range(n):
            a, b = pts[i], pts[(i + 1) % n]
            if b.type != "line":
                continue
            length = math.hypot(a.x - b.x, a.y - b.y)
            if length <= 1.0 or length > MAX_WAIST_LEN:
                continue
            before = pts[(i - 1) % n]
            after = pts[(i + 2) % n]
            if before.type is not None or after.type is not None:
                continue  # not sandwiched between curves on both sides
            mx, my = (a.x + b.x) / 2.0, (a.y + b.y) / 2.0
            a.x, a.y = mx + (a.x - mx) * shrink_to, my + (a.y - my) * shrink_to
            b.x, b.y = mx + (b.x - mx) * shrink_to, my + (b.y - my) * shrink_to
