"""Builds 'c' and 'e' directly from 'o's own outer+inner ring outline,
instead of a separate donor font (Arimo) -- so their bowl/counter
proportions are *literally* 'o's, at every weight, width and serif
setting, rather than an approximation of them.

A prior fix tried to reconcile 'c'/'e' (still Arimo-sourced) with 'o'
by matching only their advance width to Jost's own ch:o ratio -- a
metrics-only patch, not a shape fix -- and went through two rescale
techniques (flat hscale, then a centroid-radial push), both reverted
after each introduced a worse defect (a fattened terminal at Thin, then
a pinched hourglass counter at Black -- see arimo_source.py's own
history and README). This module fixes the actual root cause instead:
'c'/'e' came from a different font with different proportions, so no
amount of width-matching could make their *counter shape* agree with
'o's. Deriving them from 'o's own outline -- the same move already
made for 'a' (`single_story_a.py`, built from 'd's own outline) --
makes the counters agree by construction, no matching required.

Jost's own 'o' is always two contours, each a closed 16-point loop: an
on-curve point at each of 0/90/180/270 degrees from the ring's own
center, joined to the next by three off-curve control points forming
three chained true-quadratic Bezier arcs per quadrant (same topology
guarantee `quirks.py`'s own docstring relies on -- confirmed stable
across the whole wght/wdth/SERF grid, not assumed).

'c' and 'e' are built by walking that loop and "cutting" it open at
exact points along its own curve -- an aperture for both, plus a
crossbar for 'e' -- using ordinary quadratic Bezier subdivision. Given
a target angle (from the ring's own center), `_augment_ring` finds
which of the twelve chained sub-Beziers it falls on (binary search on
angle, safe because each is convex/monotonic) and subdivides exactly
there via De Casteljau's algorithm, which re-expresses a curve as two
shorter ones without changing its shape at all. Every point either
glyph keeps from 'o's own outline is therefore pixel-identical to it;
only the new cut points themselves, and the straight lines connecting
them, are new geometry. 'a' from 'd' set the precedent that a glyph can
be built by transplanting another's *finished* outline rather than
approximating it; this is the same idea applied to a curve that needs
reshaping partway through, not just one segment moved.

's' stays Arimo-sourced (`arimo_source.py`): an S-curve has no ring or
counter to derive from 'o' at all.
"""

from __future__ import annotations

import math

import ufoLib2

from . import jost_source


def _lerp(p0, p1, t):
    return (p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t)


def _quadratic_point(p0, c, p1, t):
    return _lerp(_lerp(p0, c, t), _lerp(c, p1, t), t)


def _split_quadratic(p0, c, p1, t):
    """De Casteljau subdivision of quadratic Bezier (p0, c, p1) at `t`
    into two quadratics tracing the exact same curve: (p0, l, m) then
    (m, r, p1). No approximation."""
    l = _lerp(p0, c, t)
    r = _lerp(c, p1, t)
    m = _lerp(l, r, t)
    return (p0, l, m), (m, r, p1)


def _angle(pt, center):
    return math.degrees(math.atan2(pt[1] - center[1], pt[0] - center[0]))


def _norm_angle(a):
    """Normalizes to (-180, 180]."""
    while a <= -180:
        a += 360
    while a > 180:
        a -= 360
    return a


class _RunPoint:
    """A point plus the TrueType segment-type semantics ufoLib2 expects
    (`type=None` for an off-curve control point, else the kind of
    segment arriving at this point)."""

    __slots__ = ("x", "y", "type")

    def __init__(self, x, y, type_):
        self.x = x
        self.y = y
        self.type = type_


def _ring_runs(points):
    """Splits a 16-point ring contour (4 on-curve cardinal points, each
    followed by 3 off-curve points) into its 4 quadrant runs, each
    [on_idx, off1_idx, off2_idx, off3_idx, on_idx] (index into
    `points`, next run's on0 == this run's on1). Assumes the known,
    verified 16-point structure."""
    on_idx = [i for i, p in enumerate(points) if p.type is not None]
    assert len(on_idx) == 4, f"expected 4 on-curve points, found {len(on_idx)}"
    n = len(points)
    runs = []
    for k in range(4):
        start, end = on_idx[k], on_idx[(k + 1) % 4]
        idxs = [start]
        i = start
        while i != end:
            i = (i + 1) % n
            idxs.append(i)
        runs.append(idxs)
    return runs


def _run_endpoints(points, run):
    on0, off1, off2, off3, on1 = (points[i] for i in run)
    ctrls = [(off1.x, off1.y), (off2.x, off2.y), (off3.x, off3.y)]
    anchors = [
        (on0.x, on0.y),
        _lerp(ctrls[0], ctrls[1], 0.5),
        _lerp(ctrls[1], ctrls[2], 0.5),
        (on1.x, on1.y),
    ]
    return anchors, ctrls


def _find_cut_in_run(points, run, center, target_angle):
    """Binary-searches this run's 3 chained sub-Beziers for
    `target_angle` (degrees from `center`); returns (sub, t) if found,
    else None. Safe because each sub-Bezier's angle from `center` is
    monotonic (the ring is convex)."""
    anchors, ctrls = _run_endpoints(points, run)
    anchor_angles = [_angle(p, center) for p in anchors]
    for sub in range(3):
        lo, hi = anchor_angles[sub], anchor_angles[sub + 1]
        span = _norm_angle(hi - lo)
        rel = _norm_angle(target_angle - lo)
        if span == 0:
            continue
        in_range = (0 <= rel <= span) if span > 0 else (span <= rel <= 0)
        if not in_range:
            continue
        t_lo, t_hi = 0.0, 1.0
        for _ in range(60):
            t_mid = (t_lo + t_hi) / 2.0
            p_mid = _quadratic_point(anchors[sub], ctrls[sub], anchors[sub + 1], t_mid)
            a_mid = anchor_angles[sub] + _norm_angle(_angle(p_mid, center) - anchor_angles[sub])
            if _norm_angle(a_mid - target_angle) * (1 if span > 0 else -1) < 0:
                t_lo = t_mid
            else:
                t_hi = t_mid
        return sub, (t_lo + t_hi) / 2.0
    return None


def _sub_bezier_segment(p0, c, p1, ta, tb):
    """The exact quadratic (new_p0, new_c, new_p1) tracing (p0, c, p1)
    from t=ta to t=tb, via two De Casteljau splits."""
    if ta <= 0.0 and tb >= 1.0:
        return (p0, c, p1)
    _, right = _split_quadratic(p0, c, p1, max(ta, 0.0))
    if tb >= 1.0:
        return right
    tb2 = (tb - ta) / (1.0 - ta) if ta < 1.0 else 1.0
    left2, _ = _split_quadratic(right[0], right[1], right[2], tb2)
    return left2


def _run_arc_points(points, run, start, end):
    """Interior points (off-curve controls + implied on-curve joins,
    `_RunPoint`s) strictly between `start` and `end` -- each an
    (sub, t) position within this run's own traversal order, per
    `_find_cut_in_run` -- not including whatever sits exactly at
    `start`/`end` themselves. `start` must precede `end` in the run's
    own point order (sub, then t), not necessarily in increasing
    angle -- outer and inner rings traverse their shared angles in
    opposite senses."""
    anchors, ctrls = _run_endpoints(points, run)
    sub_s, t_s = start
    sub_e, t_e = end
    pieces = []
    if sub_s == sub_e:
        pieces.append(_sub_bezier_segment(anchors[sub_s], ctrls[sub_s], anchors[sub_s + 1], t_s, t_e))
    else:
        pieces.append(_sub_bezier_segment(anchors[sub_s], ctrls[sub_s], anchors[sub_s + 1], t_s, 1.0))
        for s in range(sub_s + 1, sub_e):
            pieces.append((anchors[s], ctrls[s], anchors[s + 1]))
        pieces.append(_sub_bezier_segment(anchors[sub_e], ctrls[sub_e], anchors[sub_e + 1], 0.0, t_e))
    out = []
    for i, (p0, c, p1) in enumerate(pieces):
        out.append(_RunPoint(c[0], c[1], None))
        if i < len(pieces) - 1:
            out.append(_RunPoint(p1[0], p1[1], "qcurve"))
    return out


def locate_cuts(points, center, angles):
    """Returns {angle: (quadrant, sub)}: which of the ring's 4 quadrants
    (index into `_ring_runs`) and which of its 3 chained sub-Beziers
    each angle falls on. Meant to be called ONCE, at a single reference
    master, and the result reused via `_augment_ring`'s `locations`
    param at every other master -- searching fresh at each master risks
    a cut landing in a different quadrant/sub-Bezier as the curve's own
    control points shift with weight, changing the glyph's own point
    count between masters, which fontmake requires to be identical to
    compile a variable font at all (confirmed the hard way: 'c' came
    out with 50 points at wght=100 but 46 at wght=400 before this was
    forced to a single reference location)."""
    runs = _ring_runs(points)
    result = {}
    for angle in angles:
        for qi, run in enumerate(runs):
            found = _find_cut_in_run(points, run, center, angle)
            if found is not None:
                result[angle] = (qi, found[0])
                break
        else:
            raise ValueError(f"angle {angle} not found on ring")
    return result


def _bisect_t(anchors, ctrls, sub, center, target_angle):
    a0 = _angle(anchors[sub], center)
    a1 = _angle(anchors[sub + 1], center)
    span = _norm_angle(a1 - a0)
    t_lo, t_hi = 0.0, 1.0
    for _ in range(60):
        t_mid = (t_lo + t_hi) / 2.0
        p_mid = _quadratic_point(anchors[sub], ctrls[sub], anchors[sub + 1], t_mid)
        a_mid = a0 + _norm_angle(_angle(p_mid, center) - a0)
        if _norm_angle(a_mid - target_angle) * (1 if span >= 0 else -1) < 0:
            t_lo = t_mid
        else:
            t_hi = t_mid
    return (t_lo + t_hi) / 2.0


def _augment_ring(points, center, angles, locations):
    """Returns (new_points, index_for_angle): a copy of the 16-point
    ring `points` with one new on-curve point inserted, via exact
    Bezier subdivision, at each angle in `angles` -- at the (quadrant,
    sub) position `locations[angle]` gives (see `locate_cuts`), not
    searched fresh. Multiple cuts landing in the same quadrant run are
    handled in their own correct order. `index_for_angle` maps each
    requested angle to its point's index in `new_points`."""
    runs = _ring_runs(points)
    located = [(runs[locations[angle][0]], locations[angle][1], angle) for angle in angles]

    new_points = []
    index_for_angle = {}
    for run in runs:
        on0 = points[run[0]]
        new_points.append(_RunPoint(on0.x, on0.y, on0.type))
        anchors, ctrls = _run_endpoints(points, run)
        cuts_here = sorted(
            ((sub, _bisect_t(anchors, ctrls, sub, center, angle), angle) for (r, sub, angle) in located if r is run),
            key=lambda c: (c[0], c[1]),
        )
        prev = (0, 0.0)
        for (sub, t, angle) in cuts_here:
            new_points.extend(_run_arc_points(points, run, prev, (sub, t)))
            cut_xy = _quadratic_point(anchors[sub], ctrls[sub], anchors[sub + 1], t)
            new_points.append(_RunPoint(cut_xy[0], cut_xy[1], "qcurve"))
            index_for_angle[angle] = len(new_points) - 1
            prev = (sub, t)
        new_points.extend(_run_arc_points(points, run, prev, (2, 1.0)))
    return new_points, index_for_angle


def _forward(points, i, j):
    """Points from index `i` to `j` inclusive, walking forward
    (increasing, wrapping at len(points))."""
    n = len(points)
    out = []
    k = i
    while True:
        out.append(points[k])
        if k == j:
            return out
        k = (k + 1) % n


def _kept_arc(points, i, j):
    """The LONGER of the two forward arcs between indices `i` and `j`
    -- i.e. the arc that excludes whatever small aperture/gap the two
    cuts bound."""
    n = len(points)
    fwd_i_to_j = (j - i) % n
    if fwd_i_to_j >= n - fwd_i_to_j:
        return _forward(points, i, j)
    return _forward(points, j, i)


def _center_of(points):
    xs = [p.x for p in points]
    ys = [p.y for p in points]
    return ((min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0)


def _outer_inner(o_glyph):
    def area(c):
        xs = [p.x for p in c.points]
        ys = [p.y for p in c.points]
        return (max(xs) - min(xs)) * (max(ys) - min(ys))
    contours = sorted(o_glyph.contours, key=area, reverse=True)
    return contours[0], contours[1]


def _make_glyph(name, width, points):
    glyph = ufoLib2.objects.Glyph(name=name)
    glyph.unicodes = [ord(name)]
    glyph.width = width
    contour = ufoLib2.objects.Contour()
    for p in points:
        contour.points.append(ufoLib2.objects.Point(p.x, p.y, type=p.type))
    glyph.contours.append(contour)
    return glyph


_reference_rings_cache: tuple | None = None


def _reference_rings():
    """'o's own outer/inner ring points at wght=400/wdth=100 -- the same
    single reference instance `quirks.py`'s own point-index tables are
    verified against -- used ONLY to pin down which (quadrant, sub) each
    aperture/crossbar cut angle falls on (see `locate_cuts`), so that
    assignment doesn't depend on which master happens to get built
    first."""
    global _reference_rings_cache
    if _reference_rings_cache is None:
        jost_name = jost_source.glyph_names_for_chars("o")["o"]
        pen_value, _ = jost_source.extract(jost_name, 400, 100)
        glyph = ufoLib2.objects.Glyph(name="o")
        jost_source.replay(glyph.getPen(), pen_value)
        outer, inner = _outer_inner(glyph)
        _reference_rings_cache = (outer.points, inner.points)
    return _reference_rings_cache


_cut_location_cache: dict = {}


def _cached_locations(key, angles, which):
    """`locate_cuts`, computed once per distinct `key` against the fixed
    reference 'o' (`_reference_rings`) and reused for every later call
    regardless of which master's ring is actually being cut -- see
    `locate_cuts`'s own docstring for why the (quadrant, sub) assignment
    must stay fixed across masters. `which` is "outer" or "inner"."""
    if key not in _cut_location_cache:
        outer_pts, inner_pts = _reference_rings()
        points = outer_pts if which == "outer" else inner_pts
        center = _center_of(points)
        _cut_location_cache[key] = locate_cuts(points, center, angles)
    return _cut_location_cache[key]


def build_c_from_o(o_glyph, aperture_half_angle: float = 31.0):
    """A new glyph named 'c': 'o's own ring, cut open at
    `aperture_half_angle` degrees on either side of due east (the
    ring's own rightmost point) -- the side Latin 'c' opens toward.
    Both cut points sit exactly on 'o's own curve; the two straight
    terminals closing the aperture are left for the caller to reorient
    to horizontal (`quirks.py::_reorient_cut`, reused as-is -- a
    straight 2-point cut is exactly what that function expects).
    Returns (glyph, [(i1, i2), (i1, i2)]) -- the point-index pairs of
    the aperture's two terminal cuts (bottom, then top/wraparound).
    """
    outer, inner = _outer_inner(o_glyph)
    outer_c, inner_c = _center_of(outer.points), _center_of(inner.points)

    hi, lo = aperture_half_angle, -aperture_half_angle
    outer_loc = _cached_locations(("c", "outer", aperture_half_angle), [hi, lo], "outer")
    inner_loc = _cached_locations(("c", "inner", aperture_half_angle), [hi, lo], "inner")
    outer_pts, outer_idx = _augment_ring(outer.points, outer_c, [hi, lo], outer_loc)
    inner_pts, inner_idx = _augment_ring(inner.points, inner_c, [hi, lo], inner_loc)

    outer_kept = _kept_arc(outer_pts, outer_idx[hi], outer_idx[lo])
    inner_kept = _kept_arc(inner_pts, inner_idx[lo], inner_idx[hi])

    points = (
        [_RunPoint(outer_kept[0].x, outer_kept[0].y, "line")]
        + outer_kept[1:]
        + [_RunPoint(inner_kept[0].x, inner_kept[0].y, "line")]
        + inner_kept[1:]
    )
    glyph = _make_glyph("c", o_glyph.width, points)
    n = len(points)
    cuts = [(len(outer_kept) - 1, len(outer_kept)), (n - 1, 0)]
    return glyph, cuts


def _signed_area(points):
    n = len(points)
    total = 0.0
    for i in range(n):
        x1, y1 = points[i].x, points[i].y
        x2, y2 = points[(i + 1) % n].x, points[(i + 1) % n].y
        total += x1 * y2 - x2 * y1
    return total / 2.0


def build_e_from_o(o_glyph, aperture_half_angle: float = 15.0, aperture_center_angle: float = -46.0):
    """A new glyph named 'e': 'o's own ring, with a horizontal crossbar
    at the ring's own vertical center (its inner contour's existing
    due-east/due-west on-curve points, connected directly -- no new
    geometry needed there) closing off an upper bowl as a proper,
    separately-wound hole -- same as 'o's own two-contour structure,
    just with the hole's own lower edge now a straight line instead of
    a curve -- plus a small aperture on the lower-right
    (`aperture_center_angle` below due east, `aperture_half_angle`
    wide) where Latin 'e' opens, merging the lower counter into the
    outer silhouette's own single contour (there is no separate lower
    "hole": it's open to the outside through the aperture).

    Two contours, not one -- an earlier version tried a single contour
    that threaded the aperture, the crossbar, AND the upper bowl into
    one path, reasoning by analogy with 'c' (whose counter genuinely is
    single-contour, since its aperture opens the *entire* ring). That
    doesn't hold for 'e': the upper bowl never touches the aperture or
    the outer edge, so it's a properly enclosed region -- a single
    contour can't represent a hole that isn't reachable along its own
    boundary. Confirmed the hard way: that version rendered with the
    upper bowl solid and the lower region open, exactly backwards, at
    every weight and width tried.

    Returns (glyph, [(i1, i2), (i1, i2)]) -- the point-index pairs of
    the aperture's two terminal cuts (bottom, then top/wraparound),
    both on the glyph's own contour 0 (the outer contour).
    """
    outer, inner = _outer_inner(o_glyph)
    outer_c, inner_c = _center_of(outer.points), _center_of(inner.points)

    hi = aperture_center_angle + aperture_half_angle
    lo = aperture_center_angle - aperture_half_angle
    cache_key = (aperture_half_angle, aperture_center_angle)
    outer_loc = _cached_locations(("e", "outer", cache_key), [hi, lo], "outer")
    inner_loc = _cached_locations(("e", "inner", cache_key), [hi, lo], "inner")
    outer_pts, outer_idx = _augment_ring(outer.points, outer_c, [hi, lo], outer_loc)
    inner_pts, inner_idx = _augment_ring(inner.points, inner_c, [hi, lo], inner_loc)

    outer_kept = _kept_arc(outer_pts, outer_idx[hi], outer_idx[lo])

    # Due-east/due-west on `inner_pts` -- NOT requested as `_augment_ring`
    # cuts (that degenerates: those angles coincide exactly with existing
    # on-curve points, producing a zero-length "cut" and a duplicate
    # point on top of the real one -- confirmed directly). They're
    # unmodified copies of 'o's own on-curve points, so an exact
    # coordinate match finds them.
    original_center_pts = [(p.x, p.y) for p in inner.points if p.type is not None]
    east_xy = min(original_center_pts, key=lambda p: abs(_norm_angle(_angle(p, inner_c) - 0.0)))
    west_xy = min(original_center_pts, key=lambda p: abs(_norm_angle(_angle(p, inner_c) - 180.0)))
    east_new_idx = next(i for i, p in enumerate(inner_pts) if (p.x, p.y) == east_xy)
    west_new_idx = next(i for i, p in enumerate(inner_pts) if (p.x, p.y) == west_xy)

    # Outer contour: outer silhouette (long way, hi to lo) -> cut inward
    # -> lower-counter arc (lo, through south, to west) -- kept, not
    # skipped in favor of solid ink, which would wrongly fill the entire
    # lower counter at light weights -- -> crossbar -> a short arc back
    # to the aperture's other edge -> cut back to the outer silhouette.
    lower_inner = _forward(inner_pts, inner_idx[lo], west_new_idx)
    upper_inner_edge = _forward(inner_pts, east_new_idx, inner_idx[hi])

    outer_contour_points = (
        [_RunPoint(outer_kept[0].x, outer_kept[0].y, "line")]
        + outer_kept[1:]
        + [_RunPoint(lower_inner[0].x, lower_inner[0].y, "line")]
        + lower_inner[1:]
        + [_RunPoint(upper_inner_edge[0].x, upper_inner_edge[0].y, "line")]
        + upper_inner_edge[1:]
    )

    # Upper bowl: a proper hole, same as 'o's own inner contour but with
    # a straight crossbar instead of the lower quarter-arcs. Must wind
    # opposite the outer contour -- checked and flipped if needed, same
    # as `quirks.py::reshape_counter_to_o`'s own reasoning (a contour's
    # own absolute winding isn't stable across masters, only its
    # relationship to what encloses it is).
    hole_arc = _forward(inner_pts, west_new_idx, east_new_idx)
    hole_points = [_RunPoint(hole_arc[0].x, hole_arc[0].y, "line")] + hole_arc[1:]
    hole_points[-1] = _RunPoint(hole_points[-1].x, hole_points[-1].y, hole_points[-1].type or "line")

    outer_sign = _signed_area(outer_contour_points) >= 0
    hole_sign = _signed_area(hole_points) >= 0
    if hole_sign == outer_sign:
        hole_points = [hole_points[0]] + list(reversed(hole_points[1:]))

    glyph = ufoLib2.objects.Glyph(name="e")
    glyph.unicodes = [ord("e")]
    glyph.width = o_glyph.width
    outer_c_obj = ufoLib2.objects.Contour()
    for p in outer_contour_points:
        outer_c_obj.points.append(ufoLib2.objects.Point(p.x, p.y, type=p.type))
    glyph.contours.append(outer_c_obj)
    hole_c_obj = ufoLib2.objects.Contour()
    for p in hole_points:
        hole_c_obj.points.append(ufoLib2.objects.Point(p.x, p.y, type=p.type))
    glyph.contours.append(hole_c_obj)
    n = len(outer_contour_points)
    cuts = [(len(outer_kept) - 1, len(outer_kept)), (n - 1, 0)]
    return glyph, cuts
