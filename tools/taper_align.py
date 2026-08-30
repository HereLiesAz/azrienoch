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

That fixes the TOP corner's own two points trading places, but it isn't
the whole story: confirmed directly (a real edge-edge crossing sweep,
not just the two-point-order check above) that v/w's OUTER curve -- the
run leading from each tip down into the sharp bottom vertex ('v'), or
into each of 'w's own internal valleys -- can still cross the counter's
own dead-straight inner diagonal at a wide band of intermediate `wght`
values, independent of whether the top corner's own two points are
correctly ordered. This isn't an in-between interpolation artifact
either: the RAW, unprocessed Roboto Flex extraction at these weights
already self-intersects, before any of Azrienoch's own code touches it
-- Roboto Flex's own gvar deltas, at the specific combination of
Azrienoch's custom stroke-weight parametric axes (`roboto_source.py`'s
own height-as-weight curve) and these particular intermediate `wght`
values, simply don't keep positive stroke width there at every point
along the curve.

`stabilize_diagonal_strokes` fixes this the same way
`canonical_counter.py` already fixes an analogous raw-extraction defect
for 'o' and its own family: only when the glyph's own contour is
confirmed to actually self-intersect (checked directly, not assumed --
most masters need nothing done at all, including most of the heaviest
weights, where Roboto Flex's own native curve is perfectly fine and
worth keeping untouched), replace the WHOLE contour with an
affine-scaled copy of this SAME glyph's own shape at the reference
master (always non-self-intersecting there, confirmed), fit to this
master's own current bounding box via
`canonical_counter._reshape_contour_to_reference` -- the same
bbox-relative, independent-X/Y-scale primitive 'o'/'O'/'0'/'6'/'9'/'D'
already use to stabilize themselves. A per-span reshape (moving only
the curve nearest each crossing, anchored on the outer silhouette's own
"safe" tip/notch corners) was tried first and worked for 'v'/'V'/'w',
but not reliably for 'W' -- confirmed those "safe" anchors aren't
always safe (they sit on a crossing themselves at 'W's own most
extreme weights) and, more importantly, that even where it did clear
the crossing it visibly looked wrong: a chord-relative scale moves each
point's own local angle independently of its neighbors, so the
counter's own vertex ends up pointing a different direction than the
outer silhouette's own lowest point right next to it. A whole-contour
bbox-relative copy doesn't have that problem -- every point moves
together, preserving the whole shape's own internal angles exactly as
Roboto Flex drew them at the reference master, just rescaled.
"""

from __future__ import annotations

from tools import canonical_counter as CC

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


def _ccw(a, b, c) -> bool:
    return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])


def _segments_cross(a, b, c, d) -> bool:
    if a in (c, d) or b in (c, d):
        return False
    return _ccw(a, c, d) != _ccw(b, c, d) and _ccw(a, b, c) != _ccw(a, b, d)


def contour_self_intersects(points) -> bool:
    """Whether `points` (a contour's own on/off-curve points, taken as a
    polygon of straight edges between consecutive points -- close enough
    to the true curve for detecting the gross, wght-scale self-crossings
    this module fixes, without needing a full bezier flattening) has any
    two non-adjacent edges that cross."""
    n = len(points)
    if n < 4:
        return False
    coords = [(p.x, p.y) for p in points]
    edges = [(coords[i], coords[(i + 1) % n]) for i in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            if abs(i - j) <= 1 or (i == 0 and j == n - 1):
                continue
            if _segments_cross(edges[i][0], edges[i][1], edges[j][0], edges[j][1]):
                return True
    return False


def stabilize_diagonal_strokes(glyph, reference_contours) -> bool:
    """If `glyph`'s own first contour actually self-intersects, replace
    it wholesale with an affine-scaled copy of this same glyph's own
    reference-master shape (`canonical_counter._reshape_contour_to_reference`
    -- the same bbox-relative, independent-X/Y-scale primitive that
    fixes 'o' and its own family), fit to this master's own current
    bounding box. Returns whether the contour is (now) clean.

    A no-op, by design, on the large majority of masters where Roboto
    Flex's own native curve is already fine (most of the weight range,
    including most of the heaviest weights) -- this only ever touches a
    master actually confirmed to need it, never blindly re-derives a
    shape that was already correct.

    An earlier version of this reshaped only the specific span(s) of the
    curve nearest each crossing, anchored on the outer silhouette's own
    tip/notch corners left untouched -- confirmed to work for 'v'/'V'/
    'w' but not reliably for 'W', where those same "safe" anchor points
    turned out to sit on a crossing themselves at the most extreme
    weights, and confirmed to look visibly wrong even where it did
    remove the crossing (a chord-relative scale doesn't move each
    point's local angle in step with its neighbors, so the counter's own
    vertex ends up pointing a visibly different direction than the
    outer silhouette's own lowest point -- exactly the asymmetry a
    bbox-relative whole-contour copy doesn't have, since it moves every
    point together, preserving the whole shape's own internal angles)."""
    if not glyph.contours:
        return True
    contour = glyph.contours[0]
    points = contour.points
    if not contour_self_intersects(points):
        return True
    ref_points = reference_contours[0]
    if len(ref_points) != len(points):
        return True
    CC._reshape_contour_to_reference(contour, ref_points)
    return not contour_self_intersects(points)
