"""Azrienoch-specific modifications layered on top of Jost's own outlines.

Every function here mutates a `ufoLib2.Glyph` already built from Jost's
raw extraction (`jost_source.py`) -- nothing here is a fresh redraw.

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


def _reorient_cut(points, i1: int, i2: int, orientation: str,
                  x_bounds: tuple[float, float] | None = None) -> None:
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

    if x_bounds is not None:
        # Slide the whole cut (length kept) back inside `x_bounds`, so a
        # rigid re-spread of a steeply diagonal cut can't overhang the
        # glyph's own body.
        lo, hi = x_bounds
        xs = (new_outer[0], new_inner[0])
        dx = lo - min(xs) if min(xs) < lo else (hi - max(xs) if max(xs) > hi else 0.0)
        new_outer = (new_outer[0] + dx, new_outer[1])
        new_inner = (new_inner[0] + dx, new_inner[1])

    outer.x, outer.y = new_outer
    inner.x, inner.y = new_inner

    for pt, i, old, new in ((outer, i_outer, old_outer, new_outer), (inner, i_inner, old_inner, new_inner)):
        for step in (1, -1):
            neighbor_i = (i + step) % n
            if neighbor_i in (i1, i2):
                continue  # the other terminal point, not this leg
            _rotate_scale_run(points, neighbor_i, step, (i1, i2), old, new)


# glyph name -> (contour index, point index 1, point index 2), horizontal cut
_HORIZONTAL_TERMINALS = {
    # 'c'/'e' are absent on purpose: `ring_derived.py` builds their
    # terminals exactly horizontal by construction, and their rebuilt
    # contours no longer carry the old hardcoded cut indices.
    # Arimo's own 's' terminals are close to horizontal but genuinely
    # diagonal by design (~12-14 units of rise across the cut, confirmed
    # by dumping Arimo's own raw points directly, not assumed from how
    # they looked) -- these indices are Arimo's point layout (via
    # arimo_source.py), found once against its own topology, which
    # `arimo_source.extract`'s point-for-point interpolation between
    # Regular and Bold keeps identical at every wght sample.
    "s": [(0, 6, 7), (0, 29, 30)],
    # Jost's 'S': one 51-point contour, identical at every master
    # (checked at wght 100/900, wdth 75/100). Points 0-1 are the lower-
    # left terminal's cut, 26-27 the upper-right one's. Jost cuts both
    # on the diagonal; cut horizontal to match 's' (Arimo, above).
    "S": [(0, 0, 1), (0, 26, 27)],
}

# glyph name -> (contour index, index of the on-curve point whose x is
# the cut's left limit, index of the one whose x is its right limit):
# horizontal cuts of that glyph are kept inside [left x, right x]. 'S':
# 35 is the upper bowl's leftmost point, 10 the lower bowl's rightmost
# (Jost's own contour order, identical at every master). Without it the
# lower-left terminal overhangs the bowl (x = -12.8 at wght 900,
# wdth 75) and the letter reads as tipping over.
_TERMINAL_X_LIMITS = {"S": (0, 35, 10)}

# glyph name -> (contour index, point index 1, point index 2), vertical cut
_VERTICAL_TERMINALS = {
    "r": [(1, 0, 1)],
    "f": [(1, 0, 1)],
    # 'r' with a diacritic (Jost's own glyph names for r-acute/r-cedilla/
    # r-caron): Jost draws these as 'r's own two contours plus one more
    # for the mark (confirmed directly: 3 contours vs 'r's own 2, at
    # every one of these three), so 'r's own contour-1/point-0,1
    # terminal indices still point at the same stem terminal here too.
    "racute": [(1, 0, 1)],
    "uni0157": [(1, 0, 1)],
    "rcaron": [(1, 0, 1)],
}


def apply_terminal_cuts(glyph) -> None:
    """'s' (sourced from Arimo, see `arimo_source.py`) and 'S' (Jost's
    own diagonal terminals, cut to match 's') get a true
    horizontal terminal cut ('c'/'e' are built horizontal by
    `ring_derived.py` and aren't listed) -- Arimo's own terminals are close to
    horizontal but genuinely diagonal by design (a rise of 12-31 units
    across the cut, confirmed by dumping Arimo's own raw points
    directly, not assumed from how they looked at a glance). r/f get a
    vertical terminal cut, matching each other, instead of Jost's own
    diagonal one. 'g' is left alone: Jost's own descender-loop terminal
    is already a horizontal cut (both endpoints already share a Y) --
    confirmed by inspection, not assumed."""
    limits = _TERMINAL_X_LIMITS.get(glyph.name)
    for contour_idx, i1, i2 in _HORIZONTAL_TERMINALS.get(glyph.name, []):
        pts = glyph.contours[contour_idx].points
        bounds = (pts[limits[1]].x, pts[limits[2]].x) if limits else None
        _reorient_cut(pts, i1, i2, "horizontal", bounds)
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
    into an affine-scaled copy of it, for Jost's own point structure
    (confirmed directly: 'o's own two contours and 'b'/'d'/'p'/'q's
    inner counter and 'g's upper-bowl inner counter all share the
    identical 16-point structure -- 4 qcurve/off/off/off runs -- just
    cyclically rotated to a different start point per glyph).

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
    untouched -- a known, documented limitation, not a bug.
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
        # contour's own absolute winding sign is not, confirmed
        # directly on Jost's own masters).
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


# ---------------------------------------------------------------------------
# Micro-notch fixes: a handful of Jost's own glyphs place two on-curve
# points a few units apart where the drawing clearly intends a single
# point (two strokes meeting, or a curve terminating flush against a
# straight run) -- a genuine defect in the vendored source, not
# something Azrienoch's own extraction or terminal-cut logic introduced
# (confirmed directly: these exact coordinates appear byte-for-byte in
# Jost[wght].ttf's own raw outlines, caught by a Glee stability audit's
# self-intersection sweep across the full wght x wdth x SERF grid).
# Left uncorrected, the tiny stray segment between the two near-
# duplicate points folds the fill, showing as a visible hole ('y'), or
# a thin notch carved into the stroke ('six'/'nine').
# ---------------------------------------------------------------------------

def _line_intersect(a, b, c, d):
    """The intersection of infinite lines through (a, b) and (c, d)."""
    x1, y1 = a.x, a.y
    x2, y2 = b.x, b.y
    x3, y3 = c.x, c.y
    x4, y4 = d.x, d.y
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    return x1 + t * (x2 - x1), y1 + t * (y2 - y1)


def fix_y_crotch(glyph) -> None:
    """'y's two diagonal strokes' inner edges are meant to meet at a
    single crotch point where they cross, but Jost's own points 2 and 3
    (contour 0) sit a few units apart on either side of the true
    crossing -- confirmed by computing where the lines through their own
    neighbors (1->2 and 3->4) actually intersect: at wght=400 that point
    is (223.6, 143.0), well clear of both original points (208, 104) and
    (241, 100), meaning the drawn edges already cross before reaching
    them and fold back, leaving a visible triangular hole at the join.
    Moves both points to the real intersection -- unlike the six/nine
    notches below, a plain midpoint merge would leave the fold in place
    here, since the true crossing is genuinely elsewhere.
    """
    pts = glyph.contours[0].points
    x, y = _line_intersect(pts[1], pts[2], pts[3], pts[4])
    pts[2].x, pts[2].y = x, y
    pts[3].x, pts[3].y = x, y


def _merge_near_duplicate(points, i1: int, i2: int) -> None:
    """Collapses points[i1]/points[i2] -- a few units apart where the
    drawing intends one point -- to their shared midpoint, eliminating
    the stray micro-segment between them without changing point count."""
    mx = (points[i1].x + points[i2].x) / 2.0
    my = (points[i1].y + points[i2].y) / 2.0
    points[i1].x, points[i1].y = mx, my
    points[i2].x, points[i2].y = mx, my


def fix_six_nine_notch(glyph) -> None:
    """'six'/'nine' each place two on-curve points ~8 units apart right
    where the bowl's curve meets the ascender/descender's straight edge
    (contour 1, indices 20/21 in both) -- confirmed present in Jost's
    own raw outline at every sampled weight from 150 to 900 (a Glee
    stability audit's finding). Close enough together, unlike 'y's
    crotch, that a plain midpoint merge (not a full line intersection)
    cleanly removes the notch."""
    _merge_near_duplicate(glyph.contours[1].points, 20, 21)


# ---------------------------------------------------------------------------
# Letter redraws derived from other letters' own outlines: S rotation, the
# q/J curls, and y built from u + g's descender.
# ---------------------------------------------------------------------------

def _copy_points(points):
    from ufoLib2.objects import Point
    return [Point(p.x, p.y, p.type, p.smooth) for p in points]


def _mirror_reversed(points, axis_sum: float):
    """Mirrors `points` across the vertical line x = axis_sum / 2
    (x' = axis_sum - x) and reverses the contour direction so winding is
    preserved (a mirror flips it). In a UFO point list an on-curve
    point's type names the segment that ENDS at it, so after reversing,
    each on-curve point takes the type of the on-curve point that
    followed it in the original order; off-curve points stay untyped."""
    from ufoLib2.objects import Point
    n = len(points)
    on_idx = [i for i, p in enumerate(points) if p.type is not None]
    next_type = {}
    for pos, i in enumerate(on_idx):
        next_type[i] = points[on_idx[(pos + 1) % len(on_idx)]].type
    out = []
    for i in reversed(range(n)):
        p = points[i]
        out.append(Point(axis_sum - p.x, p.y, next_type[i] if p.type is not None else None, p.smooth))
    return out


def _set_contour_points(glyph, index: int, points) -> None:
    from ufoLib2.objects import Contour
    glyph.contours[index] = Contour(points=points)


def rotate_180(glyph) -> None:
    """Rotates the whole glyph 180 degrees about its own bounding-box
    centre. A rotation keeps contour winding, so nothing else needs
    reordering; advance width is untouched."""
    pts = [p for c in glyph.contours for p in c.points]
    cx = (min(p.x for p in pts) + max(p.x for p in pts)) / 2.0
    cy = (min(p.y for p in pts) + max(p.y for p in pts)) / 2.0
    for p in pts:
        p.x = 2 * cx - p.x
        p.y = 2 * cy - p.y


def build_J_from_g(J_glyph, g_glyph) -> None:
    """'J' takes g's full descender curl (stem, loop, horizontal
    terminal) verbatim, with the stem's top raised from x-height to J's
    own cap-height. Advance width becomes g's, since the curl needs g's
    horizontal room. g contour 0 is the stem+tail outline; points 9 and
    10 are its top-right and top-left stem corners."""
    top_y = J_glyph.contours[0].points[11].y  # J's own stem-top corner (cap height)
    pts = _copy_points(g_glyph.contours[0].points)
    pts[9].y = top_y
    pts[10].y = top_y
    _set_contour_points(J_glyph, 0, pts)
    J_glyph.width = g_glyph.width


def curl_q_from_j(q_glyph, j_glyph) -> None:
    """'q' swaps its plain rectangular stem (contour 0) for j's stem and
    curl mirrored left-to-right, so the tail hooks right where j's hooks
    left. j contour 1 is the stem+tail (contour 0 is the dot); points 10
    and 11 are its stem-top right/left corners. The mirror axis maps j's
    stem onto q's stem (q contour 0, points 0/1 = stem bottom-left/
    bottom-right). Advance width is unchanged: like j's own curl, the
    hook overhangs the sidebearing."""
    j_pts = j_glyph.contours[1].points
    q_stem = q_glyph.contours[0].points
    axis_sum = q_stem[0].x + j_pts[10].x  # j stem right edge -> q stem left edge
    _set_contour_points(q_glyph, 0, _mirror_reversed(_copy_points(j_pts), axis_sum))


def build_y_from_u_and_g(y_glyph, u_glyph, g_glyph) -> None:
    """'y' becomes 'u' with its right stem run down into g's descender
    curl: u points 0-9 (left stem, bowl, up to where the bowl meets the
    right stem), then g's stem-left edge, curl and terminal (g points
    11-19 then 0-8, shifted so g's stem sits on u's right stem), then
    u points 12-20 (right stem up and back round). Replaces u points
    10-11, the flat foot. Advance width is u's."""
    u_pts = u_glyph.contours[0].points
    g_pts = g_glyph.contours[0].points
    dx = u_pts[12].x - g_pts[9].x  # g stem right edge -> u stem right edge
    tail = _copy_points(g_pts[11:20] + g_pts[0:9])
    for p in tail:
        p.x += dx
    pts = _copy_points(u_pts[0:10]) + tail + _copy_points(u_pts[12:21])
    _set_contour_points(y_glyph, 0, pts)
    y_glyph.width = u_glyph.width


def match_Q_tail_to_R(Q_glyph, R_glyph) -> None:
    """Re-angles 'Q's diagonal tail (contour 2, a four-point
    parallelogram: 0 top-left, 1 bottom-left, 2 bottom-right, 3
    top-right) to the same slope as 'R's leg (contour 0, same point
    order). The tail's bottom points and height stay put; each top
    point's x moves so its edge runs at R's own run-per-rise ratio
    (measured on this master's own R, so it holds at every weight and
    width). The tail's bottom edge is also set to R's leg's own bottom-
    edge length (centred on the tail's own midpoint), so the stroke is
    the same width as R's, not just the same angle."""
    r = R_glyph.contours[0].points
    ratio_left = (r[1].x - r[0].x) / (r[0].y - r[1].y)
    ratio_right = (r[2].x - r[3].x) / (r[3].y - r[2].y)
    q = Q_glyph.contours[2].points
    # Same stroke width as R's leg: R's bottom edge length, kept centred on
    # the tail's own bottom-edge midpoint. Same slope + same bottom width
    # = same perpendicular thickness.
    width = r[2].x - r[1].x
    mid = (q[1].x + q[2].x) / 2.0
    q[1].x, q[2].x = mid - width / 2.0, mid + width / 2.0
    q[0].x = q[1].x - ratio_left * (q[0].y - q[1].y)
    q[3].x = q[2].x - ratio_right * (q[3].y - q[2].y)



# ---------------------------------------------------------------------------
# Y and y hung from the right terminal of their V (narrowed), not from its
# crotch. The stem (Y) or g's descender curl (y) drops from the V's right
# outer edge.
# ---------------------------------------------------------------------------

V_NARROW = 0.9   # y's V half-width scale about its centre line; arm horizontal width kept
Y_V_NARROW = 1.0  # Y's V: full original width
Y_TIP_DEPTH = 0.70  # Y's V tip height as a fraction of Jost's own junction height (taller V)
Y_ATTACH = 0.8   # Y stem attaches this fraction of the way up the V's right side


def _signed_area_xy(pts) -> float:
    n = len(pts)
    return sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n)) / 2.0


def _narrow_v(outer_l: float, outer_r: float, arm_w: float, top: float, cx: float, tip_y: float, narrow: float = V_NARROW, stem_w: float | None = None):
    """Pointed V polygon (outer-left, inner-left, crotch, inner-right,
    outer-right, tip) narrowed about x = cx by V_NARROW with the arms'
    horizontal width kept. Returns (points, slope) where slope is the
    right edge's dx/dy."""
    lo = cx - narrow * (cx - outer_l)
    ro = cx + narrow * (outer_r - cx)
    slope = (cx - lo) / (top - tip_y)
    if stem_w is not None:
        # arms as thick (perpendicular) as the stem/tail they carry
        arm_w = stem_w * math.sqrt(1.0 + slope * slope)
    crotch_y = top - (cx - (lo + arm_w)) / slope
    return [(lo, top), (lo + arm_w, top), (cx, crotch_y), (ro - arm_w, top), (ro, top), (cx, tip_y)], slope


def _set_xy_contour(glyph, index: int, pts_xy, template_points, ccw_like) -> None:
    from ufoLib2.objects import Contour, Point
    if (_signed_area_xy(pts_xy) > 0) != ccw_like:
        pts_xy = pts_xy[::-1]
    pts = [Point(x, y, "line", False) for x, y in pts_xy]
    c = Contour(points=pts)
    if index < len(glyph.contours):
        glyph.contours[index] = c
    else:
        glyph.contours.append(c)


def hang_Y_from_V(Y_glyph) -> None:
    """Y = pointed V (tip kept at the original junction height) plus a
    rectangular stem hanging from the V's right outer edge Y_ATTACH of
    the way up. Reads Jost's own 9-point Y: 0 inner-right top, 1 crotch,
    2 inner-left top, 3 outer-left top, 4/7 stem-top corners at the
    junction, 5/6 stem foot, 8 outer-right top."""
    P = [(p.x, p.y) for p in Y_glyph.contours[0].points]
    if len(P) != 9:
        raise ValueError(f"Y: expected 9 points, got {len(P)}")
    ccw = _signed_area_xy(P) > 0
    stem_w = P[6][0] - P[5][0]
    top = P[0][1]
    cx = (P[4][0] + P[7][0]) / 2.0
    tip_y = (P[4][1] + P[7][1]) / 2.0 * Y_TIP_DEPTH
    v, slope = _narrow_v(P[3][0], P[8][0], P[2][0] - P[3][0], top, cx, tip_y, Y_V_NARROW, stem_w)
    ym = tip_y + Y_ATTACH * (top - tip_y)
    xm = cx + (ym - tip_y) * slope
    # A Y stem is a rectangle from the baseline to the attach height, with
    # its right edge on the V's right outer edge.
    stem = [(xm - stem_w, P[5][1]), (xm, P[5][1]), (xm, ym), (xm - stem_w, ym)]
    _set_xy_contour(Y_glyph, 0, v, None, ccw)
    _set_xy_contour(Y_glyph, 1, stem, None, ccw)


def hang_y_from_v(y_glyph, v_glyph) -> None:
    """y = v narrowed (same V as Y) plus the descender curl built by
    build_y_from_u_and_g, re-hung so its stem's right edge sits on the
    V's right terminal at x-height. Run after build_y_from_u_and_g: y
    contour 0 points 10-29 are then the stem-and-curl outline, with
    points 28/29 the stem-top right/left corners."""
    Q = [(p.x, p.y) for p in v_glyph.contours[0].points]
    if len(Q) != 6:
        raise ValueError(f"v: expected 6 points, got {len(Q)}")
    top = Q[0][1]
    cx, tip_y = Q[1]
    ccw = _signed_area_xy(Q) > 0
    pts = y_glyph.contours[0].points
    v, _ = _narrow_v(Q[0][0], Q[2][0], Q[5][0] - Q[0][0], top, cx, tip_y, V_NARROW, pts[28].x - pts[29].x)
    dx = v[4][0] - pts[28].x
    tail = _copy_points([pts[10]] + pts[11:30])
    for p in tail:
        p.x += dx
        if p.y == pts[28].y:
            p.y = top
    _set_xy_contour(y_glyph, 0, v, None, ccw)
    from ufoLib2.objects import Contour
    y_glyph.contours.append(Contour(points=tail))
