"""Fix a stroke's outer/inner edge trading places between masters, at a
flat corner where they should never cross -- the mechanism behind v/w's
"turns inside out" self-intersection at low `wght`.

Roboto Flex draws the end of a diagonal stroke (where v/w's outer and
inner edges meet the top of the letter, and similar flat corners
elsewhere) as two separate on-curve points joined by a short straight
"line" run, not a single vertex -- the same "two points, not one"
pattern `quirks.py::_sharpen_baseline_notches` already found and fixed
at the *bottom* of v/w's point. At the top corners, though, collapsing
the run isn't the fix (these are genuine, visible corners of the outer
silhouette, not a spurious flat spot to sharpen away) -- what actually
needs fixing is which of the two points has the larger x.

Confirmed directly on 'v': at Thin weight, the run's first point sits
very slightly LEFT of its second point; at Regular weight, the same two
points (same indices -- topology is identical across masters) sit with
the second point substantially to the RIGHT of the first. Both
individually valid (a 5-unit separation at Thin isn't visibly backwards,
it's just an almost-hairline-thin corner), but gvar interpolates the
two points' x-coordinates independently and linearly: if their relative
order isn't the same at both ends, the straight-line path between them
necessarily crosses through a state where the two points coincide (the
corner pinches to a point) and then swap sides -- a real, if brief,
self-intersection of the outer contour. This is the same root failure
mode `rotation_align.py` fixes for whole-contour point correspondence,
just at the scale of a single two-point corner instead of a whole
contour's start-point rotation.

`align_taper_signs` finds every such flat corner generically (a 'line'
segment between two on-curve points, in the upper portion of the glyph,
not at the outer silhouette's very topmost point which is a real corner
in its own right) and checks whether its two points' relative order
matches a reference master's for the *same two point indices* -- if it
doesn't, mirrors the second point around the first (preserving the
corner's own width exactly, just flipping which side is which), which
is what removes the crossing without changing the corner's appearance
at any master where it wasn't already backwards.
"""

from __future__ import annotations

MIN_Y_FRACTION = 0.6  # only look in the upper part of the glyph
Y_TOLERANCE = 2.0  # units; how close in Y two points must be to call them a flat run


def _flat_line_pairs(points) -> list[tuple[int, int]]:
    n = len(points)
    if n < 3:
        return []
    max_y = max(p.y for p in points)
    if max_y <= 0:
        return []
    pairs = []
    for i in range(n):
        a, b = points[i], points[(i + 1) % n]
        if a.type != "line" or b.type != "line":
            continue
        if abs(a.y - b.y) > Y_TOLERANCE:
            continue
        if a.y < max_y * MIN_Y_FRACTION:
            continue
        if a.x == b.x:
            continue
        pairs.append((i, (i + 1) % n))
    return pairs


def align_taper_signs(glyph, reference_contours) -> None:
    """For every flat upper corner in `glyph`'s own contours, mirror its
    second point around its first whenever the pair's left/right order
    doesn't match the same pair (by point index) in `reference_contours`
    (a `rotation_align.snapshot()` of this same glyph at the reference
    master). No-op wherever the order already agrees, which is the
    common case."""
    contours = glyph.contours
    if len(contours) != len(reference_contours):
        return
    for contour, ref_points in zip(contours, reference_contours):
        points = contour.points
        if len(points) != len(ref_points):
            continue
        for i, j in _flat_line_pairs(points):
            ref_diff = ref_points[j].x - ref_points[i].x
            if ref_diff == 0:
                continue
            cur_diff = points[j].x - points[i].x
            if cur_diff == 0:
                continue
            if (cur_diff > 0) != (ref_diff > 0):
                points[j].x = 2 * points[i].x - points[j].x
