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


def _rotate_scale_run(points, start_i: int, step: int, stop_at: tuple[int, ...],
                       old_terminal, new_terminal) -> None:
    """Walks points[] from `start_i` in direction `step` (+1 or -1),
    collecting the run of OFF-CURVE points that lead from the terminal
    back to its real anchor (the nearest ON-CURVE point that isn't the
    other terminal, i.e. where this curve segment actually starts), then
    applies the similarity transform (rotate + uniform scale, pivoting on
    that anchor) which maps `old_terminal` onto `new_terminal` to every
    point in that run.

    A plain translation (moving each control point by the same delta the
    terminal moved) was tried first and is NOT enough: it leaves the
    control point's distance from its own anchor unchanged, so at Black
    weight -- where the terminal cut's own reorientation moves the
    terminal much farther than at Thin -- the control point ends up
    proportionally far too close to the anchor for how far the terminal
    now sits, and the curve overshoots into a self-intersecting notch
    right at the join (confirmed directly: rendering 'c'/'s' at wght 900
    after the translation-only fix still showed a visible spike there,
    at 400 it did not, plotted side by side). A similarity transform
    pivoting on the anchor scales the whole curve segment consistently
    with how far its own terminal actually moved, instead of just
    dragging one point along for the ride.
    """
    n = len(points)
    run_indices = []
    i = start_i
    while True:
        if i in stop_at:
            anchor_i = i
            break
        pt = points[i]
        if pt.type is not None:
            anchor_i = i
            break
        run_indices.append(i)
        i = (i + step) % n
        if len(run_indices) > n:  # pathological contour; bail out safely
            return

    if not run_indices:
        return

    anchor = points[anchor_i]
    ax, ay = anchor.x, anchor.y
    ox, oy = old_terminal[0] - ax, old_terminal[1] - ay
    nx, ny = new_terminal[0] - ax, new_terminal[1] - ay
    old_len = math.hypot(ox, oy)
    new_len = math.hypot(nx, ny)
    if old_len < 1e-9:
        return
    scale = new_len / old_len
    old_angle = math.atan2(oy, ox)
    new_angle = math.atan2(ny, nx)
    dtheta = new_angle - old_angle
    cos_t, sin_t = math.cos(dtheta) * scale, math.sin(dtheta) * scale

    for idx in run_indices:
        pt = points[idx]
        rx, ry = pt.x - ax, pt.y - ay
        pt.x = ax + rx * cos_t - ry * sin_t
        pt.y = ay + rx * sin_t + ry * cos_t


def _reorient_cut(points, i1: int, i2: int, orientation: str) -> None:
    """Reorients the straight cut between points[i1] and points[i2] to be
    perfectly horizontal or vertical, preserving the cut's length (the
    stroke thickness there) and its midpoint (the cut's location) --
    a rigid re-spread of the same two points along a different axis,
    not a curve redraw. The point that currently sits farther from the
    contour's own centroid (the outer boundary's terminal) is kept on
    the outward-facing side of the new cut, so the reorientation can't
    flip the shape inside-out.

    Each terminal's own leg of off-curve control points (the run between
    it and its real anchor point, see `_rotate_scale_run`) is transformed
    along with it, not left where it was -- see that function's docstring
    for why a plain translation isn't enough at heavy weight.
    """
    n = len(points)
    p1, p2 = points[i1], points[i2]
    cx, cy = _centroid(points)
    mx, my = (p1.x + p2.x) / 2.0, (p1.y + p2.y) / 2.0
    length = math.hypot(p2.x - p1.x, p2.y - p1.y)
    half = length / 2.0

    d1 = math.hypot(p1.x - cx, p1.y - cy)
    d2 = math.hypot(p2.x - cx, p2.y - cy)
    outer, inner, i_outer, i_inner = (p1, p2, i1, i2) if d1 > d2 else (p2, p1, i2, i1)
    old_outer, old_inner = (outer.x, outer.y), (inner.x, inner.y)

    if orientation == "horizontal":
        sign = 1.0 if mx >= cx else -1.0
        new_outer = (mx + sign * half, my)
        new_inner = (mx - sign * half, my)
    elif orientation == "vertical":
        sign = 1.0 if my >= cy else -1.0
        new_outer = (mx, my + sign * half)
        new_inner = (mx, my - sign * half)
    else:
        raise ValueError(orientation)

    outer.x, outer.y = new_outer
    inner.x, inner.y = new_inner

    for pt, i, old, new in ((outer, i_outer, old_outer, new_outer), (inner, i_inner, old_inner, new_inner)):
        for step in (1, -1):
            neighbor_i = (i + step) % n
            if neighbor_i in (i1, i2):
                continue  # the other terminal point, not this leg
            _rotate_scale_run(points, neighbor_i, step, (i1, i2), old, new)


# glyph name -> (contour index, point index 1, point index 2), vertical cut
_VERTICAL_TERMINALS = {
    "r": [(1, 0, 1)],
    "f": [(1, 0, 1)],
}


def apply_terminal_cuts(glyph) -> None:
    """r/f get a vertical terminal cut, matching each other, instead of
    Jost's own diagonal one. 'c'/'e'/'s' are no longer sourced from Jost
    at all (see `arimo_source.py`) -- Arimo's own Helvetica-style flat
    terminals need no reorientation. 'g' is left alone: Jost's own
    descender-loop terminal is already a horizontal cut (both endpoints
    already share a Y) -- confirmed by inspection, not assumed."""
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


