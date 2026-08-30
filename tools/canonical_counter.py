"""Reshape a glyph's inner counter into a true affine-scaled copy of 'o's
own outer contour, so every closed counter reads as genuinely the same
round shape -- not an approximation of one.

`counter_shape.py::round_off_waists` tried to fix "the counter reads as a
rounded square" by shrinking just the short straight waist segment. Tested
at its most aggressive setting (shrink_to=0.0, waist eliminated entirely)
the counter still read as a squircle, not an oval: the waist was never the
whole problem, the flanking curves themselves are shaped flatter near the
waist and sharper near the corner than a true round shape.

The fix here is structural instead of cosmetic. 'o's outer contour is
already the design's own reference for "genuinely round" (per
`round_contrast.py`'s docstring, its waist is proportionally tiny). Point
inspection at wght=900 shows 'o's outer contour, 'o's own inner contour,
and 'd'/'b'/'p'/'q'/'g's inner counter contour ALL share the identical
14-point structure: 6 on-curve points (4 "corner" nodes at the compass
extremes, and 2 "waist" nodes forming a short straight run) joined by 8
off-curve control points -- the same shape family, cyclically rotated to a
different start point per glyph (a bowl's counter starts at the point
where it meets the stem, not at 'o's own left-waist point). 'a', built
from 'd's own outline (`single_story_a.py`), inherits the same counter
unchanged.

`reshape_counter` finds this correspondence generically: match each
target counter's point-type sequence (line/qcurve/off-curve, in order)
against 'o's outer contour's own type sequence, trying every rotation and
both winding directions, so it works without assuming which glyph's
counter starts where. If (and only if) a match is found, every target
point is replaced by the corresponding template point, affine-scaled
independently in x and y from the template's own bounding box to the
target counter's current bounding box (so the counter's overall size and
position are unchanged -- only its shape becomes a true scaled copy of
the reference oval) and translated to the target's own center. Glyphs
that don't structurally match (e.g. 'e'/'c', whose outer and inner
boundaries share a single open contour) are simply left untouched here --
never forced into a shape that isn't a genuine match.

Only ever moves existing points to new coordinates; never adds, removes,
or reorders a point, so topology is unaffected.

Matching the type sequence alone doesn't determine winding: "line"/
"qcurve"/off-curve labels don't encode geometric direction, so a target
counter's type sequence can satisfy a *forward* rotation match of the
template's own listing even though the counter's actual winding is the
*reverse* of the template's (confirmed for 'd's counter: only a forward
match exists at all, no reversed one, yet 'd's counter genuinely winds
opposite 'o's outer). Trying to predict the correct winding from which
search direction matched is unreliable for exactly that reason -- an
earlier version of this picked between a forward and reversed mapping
based on that assumption and still got it wrong. First caught at Thin
weight: 'o's own counter, reshaped against 'o's own outer as template,
rendered as a solid oval with no hole at all -- confirmed via signed-area
(shoelace) comparison that the mapping used had produced a counter
contour whose sign now matched the outer's instead of its own original,
opposite sign.

The actual fix doesn't try to predict the sign, it checks it: build the
new coordinates from whichever mapping (forward or reversed) was found,
compute their resulting signed area, and if its sign doesn't match the
target contour's own original sign, mirror every new coordinate
left-right about the contour's own center before assigning. A mirrored
ellipse is congruent to the original -- round shapes are reflection-
symmetric -- so this always lands on the correct winding at zero visual
cost.

One glyph/weight combination is a known, deliberate no-op: 'a' at Thin
weight (wght 100). Even after `single_story_a.py`'s own Thin-weight fix
(clamping the stem top above the counter, not blindly to x-height), 'd's
counter (which 'a' inherits) still reaches slightly further left than
'd's own outer bowl edge at that one extreme -- a pre-existing Roboto
Flex artifact in 'd' itself (confirmed present before any of Azrienoch's
edits), of the same kind as the near-zero neck `round_contrast.py`
already documents, not something introduced here. `outer_contour` can't
resolve outer-vs-inner cleanly on a shape that doesn't properly nest, so
`reshape_counter` safely does nothing for that one case rather than guess
and risk reshaping the wrong contour -- `counter_shape.py::round_off_waists`
(run earlier in the pipeline) is still applied there as a fallback.
"""

from __future__ import annotations

from tools.preview import contour_to_mpl
from matplotlib.path import Path


def _type_key(point) -> str:
    return point.type if point.type is not None else "off"


def _bbox_center(points):
    xs = [p.x for p in points]
    ys = [p.y for p in points]
    return (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0


def _bbox_area(points) -> float:
    xs = [p.x for p in points]
    ys = [p.y for p in points]
    return (max(xs) - min(xs)) * (max(ys) - min(ys))


def outer_contour(contours):
    """The true outer contour: the one whose interior is not contained in
    any other contour. Neither "touches the glyph's global max Y" (what
    `round_contrast.py`/`counter_shape.py` use) nor "largest bounding-box
    area" is reliable on its own: confirmed at Thin weight that 'p's
    inner counter contour can reach one unit higher than its own outer
    contour's tallest vertex (breaking the max-Y test), and that 'a'
    (built from 'd' with the stem cut down to x-height -- see
    `single_story_a.py`) can end up with a counter whose bbox is larger
    than the shortened outer's (breaking the area test), both genuine
    Roboto Flex/construction artifacts at that extreme, not bugs here.
    Point-in-polygon containment is the actual definition of "outer" and
    isn't fooled by either: test each contour's own bbox center against
    every other contour's own path -- the outer is whichever one's
    center point is contained by nothing else. `contains_point` is called
    directly on the path `contour_to_mpl` builds (proper CURVE3/CURVE4
    codes), never through `Path.interpolated()` first -- that method's
    own docstring says codes other than LINETO/MOVETO/CLOSEPOLY "are not
    handled correctly", and confirmed it silently linearly-interpolates
    the raw control polygon instead of the true curve (a circle's own
    control points round-tripped through it come back an octagon)."""
    paths = [Path(*contour_to_mpl(c)) for c in contours]
    for i, contour in enumerate(contours):
        center = _bbox_center(contour.points)
        if not any(j != i and paths[j].contains_point(center) for j in range(len(contours))):
            return contour
    return max(contours, key=lambda c: _bbox_area(c.points))


def _find_rotation(target_types: list[str], template_types: list[str]) -> list[int] | None:
    """Forward-only: index i of the returned list is which template
    point corresponds to target point i, for some rotation offset, or
    None if no rotation makes every point's type match."""
    n = len(template_types)
    if len(target_types) != n:
        return None
    for offset in range(n):
        if all(target_types[i] == template_types[(i + offset) % n] for i in range(n)):
            return [(i + offset) % n for i in range(n)]
    return None


def _find_reversed_rotation(target_types: list[str], template_types: list[str]) -> list[int] | None:
    """Same as `_find_rotation` but matching the template read backwards
    -- needed because a hole conventionally winds opposite its outer
    contour, so its type sequence, read forward, matches the template's
    reversed."""
    n = len(template_types)
    if len(target_types) != n:
        return None
    reversed_template = template_types[::-1]
    for offset in range(n):
        if all(target_types[i] == reversed_template[(i + offset) % n] for i in range(n)):
            return [(n - 1 - ((i + offset) % n)) % n for i in range(n)]
    return None


def _signed_area(points) -> float:
    n = len(points)
    total = 0.0
    for i in range(n):
        x1, y1 = points[i].x, points[i].y
        x2, y2 = points[(i + 1) % n].x, points[(i + 1) % n].y
        total += x1 * y2 - x2 * y1
    return total / 2.0


def reshape_counter(glyph, template_contour) -> bool:
    """Reshape every inner contour of `glyph` that structurally matches
    `template_contour` (typically the same master's 'o' outer contour)
    into an affine-scaled copy of it. Returns True if at least one
    contour was reshaped."""
    contours = glyph.contours
    if len(contours) < 2 or template_contour is None:
        return False
    outer = outer_contour(contours)
    template_pts = template_contour.points
    template_types = [_type_key(p) for p in template_pts]
    tx0 = min(p.x for p in template_pts)
    tx1 = max(p.x for p in template_pts)
    ty0 = min(p.y for p in template_pts)
    ty1 = max(p.y for p in template_pts)
    if tx1 <= tx0 or ty1 <= ty0:
        return False
    tcx, tcy = (tx0 + tx1) / 2.0, (ty0 + ty1) / 2.0

    reshaped_any = False
    for contour in contours:
        if contour is outer:
            continue
        pts = contour.points
        target_types = [_type_key(p) for p in pts]
        mapping = _find_rotation(target_types, template_types)
        if mapping is None:
            mapping = _find_reversed_rotation(target_types, template_types)
        if mapping is None:
            continue
        ox0 = min(p.x for p in pts)
        ox1 = max(p.x for p in pts)
        oy0 = min(p.y for p in pts)
        oy1 = max(p.y for p in pts)
        if ox1 <= ox0 or oy1 <= oy0:
            continue
        ocx, ocy = (ox0 + ox1) / 2.0, (oy0 + oy1) / 2.0
        scale_x = (ox1 - ox0) / (tx1 - tx0)
        scale_y = (oy1 - oy0) / (ty1 - ty0)
        new_coords = [
            (ocx + (template_pts[mapping[i]].x - tcx) * scale_x, ocy + (template_pts[mapping[i]].y - tcy) * scale_y)
            for i in range(len(pts))
        ]

        # Whether the found mapping was a forward or reversed reading of
        # the template turns out not to reliably predict the resulting
        # winding sign (the type-label sequence -- line/qcurve/off-curve
        # -- doesn't encode geometric direction, so matching it can find
        # a "forward" correspondence even when the target's actual
        # winding was the reverse of the template's -- confirmed for
        # 'd's own counter, which only had a forward-type match yet
        # winds opposite 'o's outer). The robust fix doesn't try to
        # predict the sign at all: build the new coordinates, check
        # whether they came out with the wrong sign, and if so mirror
        # them left-right about the contour's own center. A mirrored
        # ellipse is congruent to the original (round shapes are
        # reflection-symmetric), so this costs nothing visually while
        # always landing on the correct winding.
        original_sign = _signed_area(pts) >= 0
        n = len(new_coords)
        proposed_area = sum(
            new_coords[i][0] * new_coords[(i + 1) % n][1] - new_coords[(i + 1) % n][0] * new_coords[i][1]
            for i in range(n)
        )
        proposed_sign = proposed_area >= 0
        if proposed_sign != original_sign:
            new_coords = [(2 * ocx - x, y) for x, y in new_coords]

        for p, (x, y) in zip(pts, new_coords):
            p.x, p.y = x, y
        reshaped_any = True
    return reshaped_any
