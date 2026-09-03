"""Azrienoch-specific modifications layered on top of Jost's own outlines.

Every function here mutates a `ufoLib2.Glyph` already built from Jost's
raw extraction (`jost_source.py`), the same way the repository root's
own `tools/quirks.py` modifies Roboto Flex's raw extraction -- nothing
here is a fresh redraw.

Point INDICES used below (which on-curve point is which terminal, which
contour is the round bowl, etc.) were found once by inspecting Jost's
own wght=400 instance directly and are stable across every (wght, wdth)
master: fontmake requires identical point topology across all masters
to compile a variable font at all, and Jost's own gvar already
interpolates across its native wght range, so a given glyph's point
count and ordering don't change with weight -- confirmed by inspecting
the same indices at wght 100/400/900 directly, not assumed.
"""

from __future__ import annotations

import math


# ---------------------------------------------------------------------------
# Horizontal / vertical terminal cuts
# ---------------------------------------------------------------------------

def _centroid(points):
    on_curve = [p for p in points if p.type is not None]
    xs = [p.x for p in on_curve]
    ys = [p.y for p in on_curve]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def _reorient_cut(points, i1: int, i2: int, orientation: str) -> None:
    """Reorients the straight cut between points[i1] and points[i2] to be
    perfectly horizontal or vertical, preserving the cut's length (the
    stroke thickness there) and its midpoint (the cut's location) --
    a rigid re-spread of the same two points along a different axis,
    not a curve redraw. The point that currently sits farther from the
    contour's own centroid (the outer boundary's terminal) is kept on
    the outward-facing side of the new cut, so the reorientation can't
    flip the shape inside-out.
    """
    p1, p2 = points[i1], points[i2]
    cx, cy = _centroid(points)
    mx, my = (p1.x + p2.x) / 2.0, (p1.y + p2.y) / 2.0
    length = math.hypot(p2.x - p1.x, p2.y - p1.y)
    half = length / 2.0

    d1 = math.hypot(p1.x - cx, p1.y - cy)
    d2 = math.hypot(p2.x - cx, p2.y - cy)
    outer, inner = (p1, p2) if d1 > d2 else (p2, p1)

    if orientation == "horizontal":
        sign = 1.0 if mx >= cx else -1.0
        outer.x, outer.y = mx + sign * half, my
        inner.x, inner.y = mx - sign * half, my
    elif orientation == "vertical":
        sign = 1.0 if my >= cy else -1.0
        outer.x, outer.y = mx, my + sign * half
        inner.x, inner.y = mx, my - sign * half
    else:
        raise ValueError(orientation)


# glyph name -> (contour index, point index 1, point index 2), horizontal cut
_HORIZONTAL_TERMINALS = {
    "c": [(0, 8, 9), (0, 23, 24)],
    "e": [(0, 3, 4)],
    "s": [(0, 0, 1), (0, 22, 23)],
    # 'g': Jost's own descender-loop terminal is already a horizontal cut
    # (both endpoints already share a Y) -- confirmed by inspection, not
    # assumed, and left alone rather than risk flipping an already-correct
    # shape by applying the general reorientation to it anyway.
}

# glyph name -> (contour index, point index 1, point index 2), vertical cut
_VERTICAL_TERMINALS = {
    "r": [(1, 0, 1)],
    "f": [(1, 0, 1)],
}


def apply_terminal_cuts(glyph) -> None:
    """s/c/e get Helvetica-style horizontal terminal cuts; r/f get a
    vertical cut (matching each other, per the project owner's direction)
    instead of Jost's own diagonal one. g is left alone (see above)."""
    for contour_idx, i1, i2 in _HORIZONTAL_TERMINALS.get(glyph.name, []):
        _reorient_cut(glyph.contours[contour_idx].points, i1, i2, "horizontal")
    for contour_idx, i1, i2 in _VERTICAL_TERMINALS.get(glyph.name, []):
        _reorient_cut(glyph.contours[contour_idx].points, i1, i2, "vertical")


# ---------------------------------------------------------------------------
# Canonical round counter: every round lowercase letter's inner hole
# becomes an affine-scaled copy of 'o's own inner counter.
# ---------------------------------------------------------------------------

def _type_key(point) -> str:
    return point.type if point.type is not None else "off"


def _bbox(points):
    xs = [p.x for p in points]
    ys = [p.y for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def _find_rotation(target_types: list[str], template_types: list[str]) -> list[int] | None:
    n = len(template_types)
    if len(target_types) != n:
        return None
    for offset in range(n):
        if all(target_types[i] == template_types[(i + offset) % n] for i in range(n)):
            return [(i + offset) % n for i in range(n)]
    return None


def _find_reversed_rotation(target_types: list[str], template_types: list[str]) -> list[int] | None:
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


def reshape_counter_to_o(glyph, o_inner_points) -> bool:
    """Reshapes every INNER (hole) contour of `glyph` whose point-type
    sequence matches `o_inner_points` (a rotation, forward or reversed)
    into an affine-scaled copy of it -- same technique as the repository
    root's `tools/canonical_counter.py::reshape_counter`, ported here
    for Jost's own point structure (confirmed directly: 'o's own two
    contours and 'b'/'d'/'p'/'q's inner counter and 'g's upper-bowl
    inner counter all share the identical 16-point structure -- 4
    qcurve/off/off/off runs -- just cyclically rotated to a different
    start point per glyph, the same relationship the root project found
    in Roboto Flex).

    Jost's own bowl outline (b/d/p/q's outer contour, g's upper-bowl
    outer contour) happens to share this same 16-point structure with
    the counter it encloses, so it structurally matches the template
    too -- reshaping it as well is NOT what was asked for (only the
    hole) and actively breaks 'g' specifically: 'g' is built from two
    independent overlapping parts (a closed bowl ring, plus a separate
    descender loop/link that passes through it), and resizing the
    bowl's own outer contour disturbs its winding relationship with the
    link, visibly notching a gap into the bowl where they used to
    overlap cleanly (confirmed by first reshaping every matching
    contour indiscriminately, seeing exactly that gap appear, and
    tracing it to this).

    Excluding "the glyph's outer contour" isn't as simple as "not
    contained in any other contour", either: b/d/p/q's straight stem
    rectangle is ALSO not contained in anything (it doesn't overlap the
    bowl), so that test alone can just as easily pick the stem as "the"
    outer and leave the real bowl-outer unexcluded -- confirmed the
    hard way: doing exactly that made every reshaped counter wind the
    SAME direction as its own bowl instead of opposite, erasing the
    hole entirely (nonzero fill draws no hole when a contour and what
    encloses it wind the same way). The fix used here sidesteps the
    ambiguity instead of resolving it generally: only compare bounding-
    box size WITHIN the set of contours that already structurally
    matched the template (the bowl-outer and its own counter, and nothing
    else -- a stem never matches this point-type sequence), where "larger
    bbox = the outer of this specific nested pair" is unambiguous.

    Only moves existing points; never adds, removes, or reorders one, so
    topology is unaffected. Contours that don't structurally match
    (any glyph whose counter doesn't share this exact 16-point shape --
    'a', whose inner contour also carries the stem-join points, and
    'c'/'e', which have no separate counter contour at all) are left
    untouched, same as the root project's own documented limitation for
    its analogous cases.
    """
    template_types = [_type_key(p) for p in o_inner_points]
    tx0, ty0, tx1, ty1 = _bbox(o_inner_points)
    if tx1 <= tx0 or ty1 <= ty0:
        return False
    tcx, tcy = (tx0 + tx1) / 2.0, (ty0 + ty1) / 2.0

    matches = []
    for contour in glyph.contours:
        target_types = [_type_key(p) for p in contour.points]
        mapping = _find_rotation(target_types, template_types)
        if mapping is None:
            mapping = _find_reversed_rotation(target_types, template_types)
        if mapping is not None:
            matches.append((contour, mapping))
    if len(matches) < 2:
        return False
    def _area(c):
        x0, y0, x1, y1 = _bbox(c.points)
        return (x1 - x0) * (y1 - y0)
    outer, _ = max(matches, key=lambda pair: _area(pair[0]))
    outer_sign = _signed_area(outer.points) >= 0
    desired_sign = not outer_sign

    reshaped_any = False
    for contour, mapping in matches:
        if contour is outer:
            continue
        pts = contour.points
        ox0, oy0, ox1, oy1 = _bbox(pts)
        if ox1 <= ox0 or oy1 <= oy0:
            continue
        ocx, ocy = (ox0 + ox1) / 2.0, (oy0 + oy1) / 2.0
        scale_x = (ox1 - ox0) / (tx1 - tx0)
        scale_y = (oy1 - oy0) / (ty1 - ty0)
        new_coords = [
            (ocx + (o_inner_points[mapping[i]].x - tcx) * scale_x, ocy + (o_inner_points[mapping[i]].y - tcy) * scale_y)
            for i in range(len(pts))
        ]

        # A hole must wind opposite whatever contour encloses it; that
        # relationship is the only thing stable across masters (each
        # contour's own absolute winding sign is not -- see the root
        # project's own canonical_counter.py docstring for the full
        # reasoning, confirmed there directly on Roboto Flex and not
        # re-derived here).
        n = len(new_coords)
        proposed_area = sum(
            new_coords[i][0] * new_coords[(i + 1) % n][1] - new_coords[(i + 1) % n][0] * new_coords[i][1]
            for i in range(n)
        )
        proposed_sign = proposed_area >= 0
        if proposed_sign != desired_sign:
            new_coords = [(2 * ocx - x, y) for x, y in new_coords]

        for p, (x, y) in zip(pts, new_coords):
            p.x, p.y = x, y
        reshaped_any = True
    return reshaped_any


# Glyphs whose inner counter is expected to structurally match 'o's own
# 16-point inner contour. 'o' itself is included (reshaping it against
# itself is a no-op) so the whole family goes through one code path.
ROUND_COUNTER_GLYPHS = {"o", "b", "d", "p", "q", "g"}
