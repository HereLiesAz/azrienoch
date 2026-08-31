"""Small, deliberately barely-noticeable Akzidenz-Grotesk-style idiosyncrasies.

Roboto Flex's letterforms are rational and even-tempered almost to a fault
-- exactly the "modern sensibilities" this project wants, but on their own
they read as neutral rather than *analytical* in the Helvetica/Akzidenz
sense. This module makes a handful of small, targeted edits to specific
glyphs, on top of the imported outline, to give the design a little more
character without redrawing anything: a proper spur on 'G', a slightly
kicked leg on 'R', and a genuinely flat terminal on 'e'/'g' where Roboto
Flex actually cuts on a diagonal despite the project's own horizontal-
terminal principle (see README's "A horizontal-terminal design
principle" -- 'c' already cuts flat there, which is what exposed 'e'/'g'
as the exceptions).

Each edit moves a small number of *existing* points by index, computed
relative to the glyph's own local geometry (a fraction of its own stem
width or bar thickness) rather than by an absolute constant -- so it
scales sensibly across weights and widths instead of needing separate
tuning per master. Critically, it never adds or removes a point: point
count and order stay exactly what Roboto Flex's own gvar already
guarantees is identical across every master, so this doesn't touch the
topology invariant the SERF axis (and gvar interpolation generally)
depends on.

Applied identically to every master (not axis-conditional), so it needs
no such invariant of its own beyond "don't change the point count."
"""

from __future__ import annotations

import math


def apply_quirks(char: str, glyph) -> None:
    """Mutate glyph's points in place for the handful of characters that
    get a quirk. No-op for everything else."""
    fn = _QUIRKS.get(char)
    if fn is not None:
        fn(glyph)


def _spur_G(glyph) -> None:
    """Extend Roboto Flex's short flat crossbar into a proper hanging
    spur -- the classic Akzidenz-Grotesk 'G' signature. Roboto Flex's own
    'G' already has a thin bar at the counter-facing end of the crossbar
    (points 24-27 in its own contour: a top-left curve anchor, two flat
    'line' corners forming the bar's bottom edge, and a top-right corner);
    this just extends that bar's bottom edge further down, by a multiple
    of its own existing thickness so the spur's depth scales with stroke
    weight automatically instead of needing a separate constant per
    master.
    """
    if not glyph.contours:
        return
    pts = glyph.contours[0].points
    if len(pts) < 28:
        return  # not the outline shape this was written against
    top_left, bottom_left, bottom_right, top_right = pts[24], pts[25], pts[26], pts[27]
    bar_h = top_left.y - bottom_left.y
    if bar_h <= 0:
        return
    extend = bar_h * 4.0
    bottom_left.y -= extend
    bottom_right.y -= extend


def _kick_R(glyph) -> None:
    """Flare Roboto Flex's diagonal leg outward at the foot -- a subtle
    asymmetric kick rather than a straight, conservative leg. Roboto
    Flex's own 'R' draws the leg as its own small contour (a simple
    quadrilateral: two points at the baseline, two where it meets the
    bowl); this nudges the leg's outer baseline corner further out by a
    fraction of the leg's own width at the foot, leaving the inner
    corner and the bowl end untouched.
    """
    leg = None
    for contour in glyph.contours:
        pts = contour.points
        if len(pts) == 4 and all(p.type == "line" for p in pts):
            ys = [p.y for p in pts]
            if min(ys) <= 1.0:  # a quadrilateral touching the baseline
                leg = pts
                break
    if leg is None:
        return
    baseline_pts = sorted((p for p in leg if p.y <= 1.0), key=lambda p: p.x)
    if len(baseline_pts) != 2:
        return
    inner, outer = baseline_pts  # smaller x = inner (toward the stem)
    leg_w = outer.x - inner.x
    if leg_w <= 0:
        return
    outer.x += leg_w * 0.18


def _square_off_terminal(pts, right_idx, left_idx) -> None:
    """Make a 2-point horizontal cut (`right_idx` -> `left_idx`, walking
    backward through the contour) actually READ as 'c's flat, squared-off
    terminal instead of the tip of a long diagonal taper.

    Flattening the cut segment itself (`pts[left_idx].y = pts[right_idx].y`,
    this module's original fix) makes the very last unit of the cut
    technically horizontal, but confirmed by direct comparison against a
    real render (not just point inspection) that this alone isn't what
    makes 'c's own opening read as flat: 'c' gets there with FOUR
    dedicated on-curve points at each of its own two terminals -- curve
    end, a short vertical 'step in', the horizontal cut itself, a short
    vertical 'step out', curve resumes -- so the ink stays at close to
    full stroke width right up to a sharp, near-perpendicular corner.
    'e'/'g' only ever had the two on-curve points bounding the cut itself
    (no budget for 'c's own extra step points without adding one, which
    the topology invariant forbids), so the curves on EITHER side of the
    cut taper gradually all the way in, and the flat unit at the very tip
    reads as the point of a diagonal hook, not a flat chop.

    The fix: without adding a point, steepen the tangent each curve
    already has AT the cut, by moving that curve's own nearest off-curve
    control point (one step further into the curve, at `right_idx - 1`
    and `left_idx + 1`) so it shares its neighboring on-curve point's x.
    A quadratic curve's tangent at an endpoint runs straight through its
    own nearest control point, so this makes both curves arrive at (and
    leave from) the cut close to vertical -- the same near-perpendicular
    corner 'c's own dedicated step points produce, built from a curve's
    existing control point instead of a fourth on-curve point."""
    right, left = pts[right_idx], pts[left_idx]
    left.y = right.y
    entry_ctrl = pts[right_idx - 1]
    if entry_ctrl.type is None:
        entry_ctrl.x = right.x
    exit_ctrl = pts[(left_idx + 1) % len(pts)]
    if exit_ctrl.type is None:
        exit_ctrl.x = left.x


def _horizontal_terminal_e(glyph) -> None:
    """Square off 'e's lower-right opening -- see `_square_off_terminal`
    for the general fix and why the cut itself being flat (point 7 at
    point 6's own height) wasn't, on its own, enough to read as one."""
    if not glyph.contours:
        return
    pts = glyph.contours[0].points
    if len(pts) < 8 or pts[6].type != "qcurve" or pts[7].type != "line":
        return  # not the outline shape this was written against
    _square_off_terminal(pts, 6, 7)


def _horizontal_terminal_g(glyph) -> None:
    """Square off 'g's descender-loop tail -- the same defect and fix as
    'e's (see `_horizontal_terminal_e`, `_square_off_terminal`), at the
    open end of the hook between point 30 (where the tail curve lands)
    and point 0 (the loop's own start)."""
    if not glyph.contours:
        return
    pts = glyph.contours[0].points
    if len(pts) != 31 or pts[30].type != "qcurve" or pts[0].type != "line":
        return  # not the outline shape this was written against
    _square_off_terminal(pts, 30, 0)


_BASELINE_TOL = 2.0  # units; how close to y=0 both ends of a notch must be


def _sharpen_baseline_notches(glyph) -> None:
    """Collapse 'v'/'w's bottom vertex/vertices back to a genuine sharp
    point at every weight, instead of Roboto Flex's own flat-bottomed
    notch there. Roboto Flex draws the point where two diagonals meet at
    the baseline not as one vertex but as a short flat 'line' segment
    between two separate on-curve points -- barely visible at Thin
    (under 65 units wide) but Roboto Flex widens it aggressively with
    weight (past 500 units by Black), which reads as a flat-bottomed
    trough, not the sharp Akzidenz-reminiscent point this is worth
    keeping. Every such segment (one for 'v', two for 'w', found
    generically rather than hardcoded per letter since the fix is the
    same either way) gets its two endpoints collapsed onto their own
    midpoint -- both already sit exactly on the baseline, so only x
    moves, and the two points become coincident: a zero-width vertex
    that still satisfies "never add or remove a point."
    """
    if not glyph.contours:
        return
    pts = glyph.contours[0].points
    n = len(pts)
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        if a.type != "line" or b.type != "line":
            continue
        if abs(a.y) > _BASELINE_TOL or abs(b.y) > _BASELINE_TOL:
            continue
        if a.x == b.x:
            continue  # already a point, or a degenerate zero-length edge
        mid_x = (a.x + b.x) / 2.0
        a.x = mid_x
        b.x = mid_x


_APEX_MAX_WIDTH = 60.0  # units; how wide a flat run can be and still count
# as a vestigial connector rather than a real, intentionally flat design edge
# (a stem cap or serif foot runs several hundred units wide; every notch this
# was written against -- w's own middle peak, v/w's own counter tips -- is
# under 10 units at every weight tested)
_APEX_Y_TOL = 3.0  # units; how close in y the run's two ends must be
_APEX_BLEND = 0.75  # how far to move each point toward the shared midpoint
# (1.0 = the midpoint exactly) -- see _sharpen_apex_notches's own docstring
# for why less than 1.0, confirmed necessary, is used instead


def _sharpen_apex_notches(glyph) -> None:
    """Collapse the same species of vestigial flat notch
    `_sharpen_baseline_notches` fixes at v/w's own OUTER bottom point,
    generalized to every OTHER place it turns up: w's own middle upward
    point, and v/w's own counter tip(s) (the point where the counter --
    the negative-space notch cut up between the two strokes -- comes to
    what should be its own sharp vertex). Point inspection at every
    weight confirms the identical pattern: Roboto Flex approaches each
    of these spots via a curve, lands two separate on-curve points a few
    units apart at (almost exactly) the same height, then curves back
    away -- never one true vertex. Barely visible at Thin, but at
    heavier weights the stroke around it is thick enough that the flat
    plateau reads as an unmistakably blunt, chopped-off tip instead of a
    point -- confirmed this is also the direct cause of the counter's
    own tip looking asymmetric/"wonky" relative to the outer silhouette's
    sharp bottom vertex right next to it (the outer already reads as a
    clean point via `_sharpen_baseline_notches`; the counter tip, left
    unfixed, didn't).

    `_sharpen_baseline_notches` doesn't already catch these: it requires
    BOTH the flat run's own points AND the segment immediately before it
    to be straight lines (true at v/w's outer bottom, where a straight
    diagonal leg runs directly into the notch), but every spot this
    function targets is approached by a CURVE, not a straight stem, so
    that stricter match correctly leaves it alone. Found generically --
    a short (`_APEX_MAX_WIDTH`), near-flat (`_APEX_Y_TOL`) 'line' run
    whose two ends are BOTH strictly higher or BOTH strictly lower than
    their own outside neighbors (a genuine local peak or valley, not
    merely two points that happen to share a height along an otherwise
    flat edge) -- rather than hardcoded per letter, so it applies
    equally to a single run (v's one counter tip) or several (w's
    middle peak plus its own two counter tips) without needing to know
    which is which.

    Solving for where the flat run's own immediate control-point
    tangents cross (the same trick `_sharpen_w_middle_peak` uses,
    anchored on the much longer, more stable straight legs either side
    of ITS OWN curve run) was tried here too, and rejected: confirmed
    directly on 'v' that it makes the fix ITSELF weight-dependent in an
    uneven way -- Roboto Flex's own local curve steepness at this one
    small notch varies enough between adjacent real masters that the
    extrapolated corner can land a visibly different relative distance
    from the two on-curve points at, say, wght 250 versus wght 400, and
    that unevenness was enough to reopen a self-intersection in the
    compiled font's own gvar interpolation between those two masters,
    even though every individual real master still tested clean in
    isolation (the same species of failure `stabilize_diagonal_strokes`
    exists to prevent, just introduced fresh here by an over-eager
    per-master correction).

    Moving all the way to the plain midpoint turned out to have the
    identical problem, just a smaller version of it -- confirmed by
    bisecting exactly how far is safe to move: fully collapsing v's own
    counter tip onto its midpoint (`_APEX_BLEND = 1.0`) still reopens
    that same 250-400 crossing, but stopping at `_APEX_BLEND` of the
    way there doesn't, with comfortable margin either side of that
    value in direct testing. So this moves each point most, but not
    all, of the way to the midpoint -- still reads as a clean, sharp
    point at every weight tested (the residual gap is a few units, far
    below what's visible at any of v/w's own weights) while leaving
    enough of the notch's own original position untouched that its
    effect on neighboring masters stays small enough not to reopen the
    interpolation crossing `stabilize_diagonal_strokes` already exists
    to prevent."""
    if not glyph.contours:
        return
    pts = glyph.contours[0].points
    n = len(pts)
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        if b.type != "line":
            continue
        if a.x == b.x:
            continue  # already a point, or a degenerate zero-length edge
        if abs(a.y - b.y) > _APEX_Y_TOL:
            continue
        if abs(a.x - b.x) > _APEX_MAX_WIDTH:
            continue
        lo, hi = min(a.y, b.y), max(a.y, b.y)
        prev_y = pts[(i - 1) % n].y
        next_y = pts[(i + 2) % n].y
        is_local_max = prev_y < lo and next_y < lo
        is_local_min = prev_y > hi and next_y > hi
        if not (is_local_max or is_local_min):
            continue
        mid_x = (a.x + b.x) / 2.0
        mid_y = (a.y + b.y) / 2.0
        a.x += (mid_x - a.x) * _APEX_BLEND
        a.y += (mid_y - a.y) * _APEX_BLEND
        b.x += (mid_x - b.x) * _APEX_BLEND
        b.y += (mid_y - b.y) * _APEX_BLEND


def _line_intersection(p1, p2, p3, p4):
    """Where line (p1,p2) crosses line (p3,p4), extended as needed.
    None if the two lines are parallel. Pure geometry -- callers decide
    which points are meaningful to pass in."""
    x1, y1, x2, y2 = p1.x, p1.y, p2.x, p2.y
    x3, y3, x4, y4 = p3.x, p3.y, p4.x, p4.y
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-9:
        return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))


def _sharpen_w_middle_peak(glyph) -> None:
    """Straighten w's own middle upward point into a genuine sharp
    vertex, the same way its two counter tips already read after
    `_sharpen_apex_notches`. Roboto Flex draws this one differently
    from the counter tips, though (confirmed by point inspection, and
    that `_sharpen_apex_notches`'s own 2-point collapse -- correct for
    the counter tips -- left an obvious extra bump beside the real
    apex here): the whole run from where the leg's own straight outer
    edge ends (index 3) to where the next straight outer edge begins
    (index 10) is SIX points of curve, not a simple symmetric dip
    around one flat 2-point run, so collapsing only the flattest pair
    in the middle still leaves the OTHER four points bulging out to
    one side, which is exactly the extra shoulder-bump a plain 2-point
    fix can't reach.

    The fix: both straight legs (index 2->3, and 10->11) are already
    aimed at where a sharp point belongs -- find where those two lines
    actually cross, and move every point strictly between them (4
    through 9) onto that single spot. A quadratic curve whose own
    control and end points all collapse onto the same location is
    geometrically just the straight line into it, so this turns the
    whole 3-to-10 run into what it always wanted to be: two straight
    edges meeting at one clean vertex, matching the sharp,
    Akzidenz-style corners the rest of v/w already has.

    Guarded on every point's own on/off-curve type along the way, the
    same defensive pattern `quirks.py`'s other per-glyph, per-index
    edits already use -- silently no-ops (including for 'v', which
    doesn't have this run at all) if Roboto Flex's own point layout
    here isn't exactly what this was written against, rather than risk
    moving the wrong points."""
    if not glyph.contours:
        return
    pts = glyph.contours[0].points
    if len(pts) < 12:
        return
    entry_line, entry_corner = pts[2], pts[3]
    exit_corner, exit_line = pts[10], pts[11]
    expected_types = ["line", "line", None, None, "qcurve", "line", None, None, "qcurve", "line"]
    actual_types = [pts[k].type for k in range(2, 12)]
    if actual_types != expected_types:
        return
    apex = _line_intersection(entry_line, entry_corner, exit_corner, exit_line)
    if apex is None:
        return
    for k in range(4, 10):
        pts[k].x, pts[k].y = apex


def _recenter_counter_span(pts, entry_idx, exit_idx, axis_x) -> None:
    """Enforce left-right mirror symmetry, about the vertical line
    x=`axis_x`, on the points from `entry_idx` to `exit_idx` inclusive
    -- paired from both ends inward (entry with exit, entry+1 with
    exit-1, ...) -- by averaging each pair's own distance from the axis
    and placing both members that same distance out, on their own
    side. Each point's own y is left untouched; only x moves."""
    span = list(range(entry_idx, exit_idx + 1))
    m = len(span)
    for k in range((m + 1) // 2):
        i, j = span[k], span[m - 1 - k]
        pi, pj = pts[i], pts[j]
        off_i = pi.x - axis_x
        off_j = axis_x - pj.x
        target = (off_i + off_j) / 2.0
        pi.x = axis_x + target
        pj.x = axis_x - target


def _recenter_v_counter(glyph) -> None:
    """v's own counter -- the negative-space notch between its two
    strokes -- isn't centered under the outer silhouette's own sharp
    bottom point: confirmed by point inspection (and by the user
    directly, comparing the counter tip against a vertical line through
    the outer vertex) that it sits offset toward the right leg by a
    substantial, strikingly consistent amount at every point along its
    own length -- roughly 80 units at Bold, checked at both the top
    corners (index 4 vs 13) and the tip itself (index 8/9), not just
    one spot -- present in Roboto Flex's own RAW extraction already,
    confirmed by checking it before any of Azrienoch's own processing
    touches the glyph at all. That uniform, whole-path offset is what
    makes the right leg's own stroke read visibly thinner than the
    left's, and is the actual mechanism behind the counter tip looking
    "wonky" against the sharp, correctly-centered outer point right
    next to it -- not primarily a sharpness problem (`_sharpen_apex_notches`
    fixes that separately), a centering one.

    Splits the correction evenly between the two sides (`_recenter_counter_span`)
    rather than trusting one side as "correct" and moving only the
    other -- there's no basis to prefer one leg's own drawing over the
    other's, so this is the most conservative fix that actually
    restores the missing symmetry."""
    if not glyph.contours:
        return
    pts = glyph.contours[0].points
    if len(pts) != 14:
        return
    if pts[1].type != "line" or pts[4].type != "line" or pts[13].type != "line":
        return
    axis_x = (pts[1].x + pts[2].x) / 2.0
    _recenter_counter_span(pts, 4, 13, axis_x)


def _recenter_w_counters(glyph) -> None:
    """The same fix `_recenter_v_counter` applies to v's one counter,
    applied to each of w's own two -- each recentered independently,
    about its own nearby outer valley vertex (index 11/12 for the
    right counter at index 14-23, index 1/2 for the left counter at
    index 24-33), since w's two counters aren't symmetric with each
    other the way its own two valleys are."""
    if not glyph.contours:
        return
    pts = glyph.contours[0].points
    if len(pts) != 34:
        return
    if pts[1].type != "line" or pts[11].type != "line" or pts[14].type != "line" or pts[24].type != "line":
        return
    right_axis = (pts[11].x + pts[12].x) / 2.0
    left_axis = (pts[1].x + pts[2].x) / 2.0
    _recenter_counter_span(pts, 14, 23, right_axis)
    _recenter_counter_span(pts, 24, 33, left_axis)


def _realign_tip_depth(pts, entry_idx, tip_a, tip_b, exit_idx, vertex_idx, outer_far_idx, ref_idx, axis_x) -> None:
    """Move the counter tip (points `tip_a`/`tip_b`) to the height
    constant-stroke-width geometry actually predicts for it, instead of
    wherever Roboto Flex's own curve happened to leave it.

    Confirmed by the user, and by directly measuring both angles, that
    the mismatch this module's earlier fixes (sharpening, recentering)
    didn't touch is real: the OUTER vertex's own angle (measured off
    its two straight legs) is roughly 2x the counter's own angle at its
    tip -- for two strokes of genuinely constant width crossing to form
    a V, those two angles have to be equal, because the inner boundary
    is just the outer boundary's own two lines, shifted inward by the
    stroke's own width, and shifting a line doesn't change its slope.
    That's the actual mechanism behind the "bell bottom jeans" look:
    the outer silhouette flares open at one angle while the counter
    stays narrow at another.

    Whichever of the two vertices is "wrong" isn't obvious from the
    geometry alone -- the outer legs are simple, reliable 2-point
    straight lines, while the counter is Roboto Flex's own curve, so
    this keeps the outer edge exactly as drawn and moves the counter
    tip to match it instead: measures the outer leg's own half-angle
    from vertical (`outer_far_idx` relative to `vertex_idx`) and the
    TRUE perpendicular stroke width at a stable reference point well
    away from the tip's own curve rounding (`ref_idx`), then places the
    tip back on the SAME bisector the vertex already sits on, at
    exactly the distance (width / sin(half-angle)) standard miter-join
    geometry says a constant-width stroke's own inner corner belongs --
    the same construction a vector-graphics stroke-outliner uses to
    turn a centerline + width into a matching pair of offset edges.

    Moving ONLY the tip point was tried first and rejected: confirmed
    by rendering that whenever the new depth lands closer to the entry/
    exit corners than the curve's own NEIGHBORING points already were
    (a real case -- Roboto Flex's own curve doesn't always descend
    monotonically toward the tip), the tip ends up sitting on the wrong
    side of its own neighbors, and the untouched curve between them
    reads as a small but distinct spike instead of a smooth point. This
    scales EVERY point strictly between `entry_idx` and `exit_idx`
    (which sit at the same y, cap height) by the same ratio -- new tip
    depth over old tip depth -- applied to each point's own existing
    depth below that shared baseline, so the whole curve's shape
    stretches or compresses smoothly to the new tip position instead of
    only the tip itself moving independently of its neighbors."""
    vertex, outer_far, ref = pts[vertex_idx], pts[outer_far_idx], pts[ref_idx]
    dx, dy = outer_far.x - vertex.x, outer_far.y - vertex.y
    length = math.hypot(dx, dy)
    if length < 1e-6:
        return
    half_angle = math.atan2(abs(dx), abs(dy))
    if half_angle < 1e-6:
        return
    width = abs((ref.x - vertex.x) * dy - (ref.y - vertex.y) * dx) / length
    depth = width / math.sin(half_angle)
    new_tip_y = vertex.y + depth if dy > 0 else vertex.y - depth

    baseline_y = pts[entry_idx].y
    old_tip_y = (pts[tip_a].y + pts[tip_b].y) / 2.0
    old_span = baseline_y - old_tip_y
    if abs(old_span) < 1e-6:
        return
    scale = (baseline_y - new_tip_y) / old_span
    for i in range(entry_idx + 1, exit_idx):
        pts[i].y = baseline_y - (baseline_y - pts[i].y) * scale
    pts[tip_a].x = pts[tip_b].x = axis_x


def _realign_v_counter_depth(glyph) -> None:
    """`_realign_tip_depth` for v's own single counter (span index
    4-13, tip at 8/9), using its right-hand outer leg (vertex index 1/2
    to corner index 3) as the reference edge and index 5 (well clear of
    the tip's own curve rounding) as the width sample."""
    if not glyph.contours:
        return
    pts = glyph.contours[0].points
    if len(pts) != 14:
        return
    if pts[1].type != "line" or pts[3].type != "line" or pts[4].type != "line" or pts[13].type != "line":
        return
    axis_x = (pts[1].x + pts[2].x) / 2.0
    _realign_tip_depth(pts, 4, 8, 9, 13, 1, 3, 5, axis_x)


def _realign_w_counter_depths(glyph) -> None:
    """`_realign_tip_depth` for each of w's own two counters (span index
    14-23 with tip at 18/19, and span index 24-33 with tip at 28/29),
    each against its own nearby outer leg and valley vertex -- see
    `_realign_v_counter_depth`, and `_recenter_w_counters` for why each
    of w's two counters is always handled independently rather than
    assumed symmetric with the other."""
    if not glyph.contours:
        return
    pts = glyph.contours[0].points
    if len(pts) != 34:
        return
    if pts[1].type != "line" or pts[11].type != "line" or pts[0].type != "line" or pts[13].type != "line":
        return
    if pts[14].type != "line" or pts[23].type != "line" or pts[24].type != "line" or pts[33].type != "line":
        return
    right_axis = (pts[11].x + pts[12].x) / 2.0
    left_axis = (pts[1].x + pts[2].x) / 2.0
    _realign_tip_depth(pts, 14, 18, 19, 23, 11, 13, 15, right_axis)
    _realign_tip_depth(pts, 24, 28, 29, 33, 1, 0, 32, left_axis)


def _merge_w_counter_bridge(glyph) -> None:
    """Open up w's own middle peak into a genuinely standalone point,
    the way a pure geometric "double-V" w (Jost's own construction is
    the reference this was checked against directly, point for point --
    see this module's own docstring) draws it, instead of leaving it
    fused to a solid mass of ink at the top.

    Roboto Flex draws w's two counters (the negative-space notch above
    each half of the letter) as two SEPARATE dips, both reaching cap
    height, joined by a wide FLAT run at cap height between them
    (index 23 to 24 -- confirmed a genuine, deliberately wide design
    edge, not a vestigial notch: `_sharpen_apex_notches`'s own
    tolerance correctly leaves it alone, since collapsing it was never
    what that generic fix was for). That flat run is a solid bridge of
    ink connecting the tops of both counters, which is exactly what
    buries the middle peak: everything above the peak's own apex stays
    filled in all the way to cap height, so the peak itself only ever
    reads as a small notch cut into the BOTTOM of that mass, never as
    an isolated point the way the two outer legs' own tips already are.

    Jost's own "w" doesn't have this bridge at all -- point inspection
    (fetched directly from Google Fonts) shows its two counters meet at
    a SINGLE shared vertex instead, which in its own case pokes slightly
    ABOVE the letter's own flat-top line, so the middle peak stands
    alone against open space on every side, the same way its own outer
    bottom points already do.

    Collapsing index 23 and 24 onto their own shared midpoint recreates
    that directly: it removes the bridge (there's no longer any run of
    ink between them at all) and gives the two counters a single shared
    apex, exactly Jost's own construction -- still only ever moving
    existing points, never adding or removing one."""
    if not glyph.contours:
        return
    pts = glyph.contours[0].points
    if len(pts) != 34:
        return
    if pts[23].type != "line" or pts[24].type != "line":
        return
    mid_x = (pts[23].x + pts[24].x) / 2.0
    mid_y = (pts[23].y + pts[24].y) / 2.0
    pts[23].x, pts[23].y = mid_x, mid_y
    pts[24].x, pts[24].y = mid_x, mid_y


def _sharpen_v_w(glyph) -> None:
    """Every one of v/w's own vestigial-flat-notch fixes -- see
    `_sharpen_baseline_notches` (the outer bottom point),
    `_sharpen_apex_notches` (v/w's own counter tips),
    `_sharpen_w_middle_peak` (w's own middle upward point, which needs
    a wider fix than the other two), `_recenter_v_counter` /
    `_recenter_w_counters` (the counter's own left-right centering),
    `_realign_v_counter_depth` / `_realign_w_counter_depths` (the
    counter tip's own HEIGHT, so its angle actually matches the outer
    vertex's), and `_merge_w_counter_bridge` (opening the middle peak
    up into a genuinely standalone point, Jost-style, instead of
    leaving it fused to solid ink at the top) for what each one targets
    and why they're separate checks. The bridge merge runs last,
    deliberately overriding whatever `_recenter_w_counters` set for
    just its own two boundary points (14<->23's own mirror pairing) --
    merging them is a different operation than mirror-symmetrizing
    them within their own span, and takes precedence."""
    _sharpen_baseline_notches(glyph)
    _sharpen_apex_notches(glyph)
    _sharpen_w_middle_peak(glyph)
    _recenter_v_counter(glyph)
    _recenter_w_counters(glyph)
    _realign_v_counter_depth(glyph)
    _realign_w_counter_depths(glyph)
    _merge_w_counter_bridge(glyph)


_QUIRKS = {
    "G": _spur_G,
    "R": _kick_R,
    "e": _horizontal_terminal_e,
    "g": _horizontal_terminal_g,
    "v": _sharpen_v_w,
    "w": _sharpen_v_w,
}
