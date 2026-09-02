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
tuning per master. Most edits never add or remove a point at all: point
count and order stay exactly what Roboto Flex's own gvar already
guarantees is identical across every master, so they don't touch the
topology invariant the SERF axis (and gvar interpolation generally)
depends on.

`_square_off_terminal` and `_rebuild_A_counter_apex` are the deliberate
exceptions: 'e'/'g's own open terminal (see `_square_off_terminal`'s own
docstring for why matching 'c's genuinely flat, squared-off cut needs
it) inserts two new on-curve points, and capital 'A's own counter apex
(see `_rebuild_A_counter_apex`'s own docstring for why its old flat
notch can never be made safe by moving its existing two points alone)
replaces 2 points with `2 * _A_COUNTER_SAMPLE_COUNT + 1` new ones --
both the same way `serifs.py` adds
foot contours: INVARIANT-SAFE as long as it's applied identically,
adding the exact same count/type of point(s) at the exact same relative
position, on every master, which it is (this whole module runs once per
master, unconditionally). Any code that addresses either glyph's own
points by a hardcoded absolute index AFTER `apply_quirks` has run needs
to already account for that shift -- see
`ufo_build.py::_is_e_counter_char`'s own call to `reshape_named_span`.

Applied identically to every master (not axis-conditional), so it needs
no such invariant of its own beyond "don't change the point count or
type sequence in a way that differs between masters."

A DESIGN PRINCIPLE TO HOLD ONTO, stated directly by the project owner:
every sharp apex in the alphabet where two DIAGONAL strokes meet --
v/w's own outer bottom point, w's own middle peak, capital A's own top
apex, capital M's own middle vertex, and any other the alphabet turns
out to have -- is the SAME geometric shape, and should all be built
from one shared construction rather than each solved independently
letter by letter. Likewise, every point where ONE side is flat
(vertical or horizontal) and the other diagonal -- M's own two
symmetric notches, where each outer stem's own inner edge kinks
against a diagonal, being the first confirmed member -- is its own
second shared family, distinct from the two-diagonal one.

This matters beyond tidiness: it's the direct explanation for why an
independent per-letter, per-master full point collapse (move this
letter's own two flat-run endpoints to THEIR OWN shared midpoint, done
fresh at every master with no reference to how any other letter's
matching apex was built) is NOT a safe general technique, even though
`_merge_w_counter_bridge` below shows it can work for one specific
case. `_sharpen_apex_notches`'s own docstring already documents this
failure mode directly: a full local collapse at each master can look
like a clean sharp point in every SINGLE master's own isolated
rendering, while still reopening a self-intersection in the compiled
font's own gvar interpolation BETWEEN adjacent masters, because the
correction's own magnitude (how far each master's own flat run had to
move to reach ITS OWN midpoint) differs unevenly master to master --
exactly what happened when this same full-collapse technique was first
tried on capital A's own apex. The fix isn't "collapse more gently"
(that's `_APEX_BLEND`'s own partial fallback, a stopgap) so much as
"stop computing the target independently per letter/master at all" --
every member of a shared family should resolve to the SAME reference
construction (this project's convention throughout is to check that
construction directly against Jost, point for point, the way
`_sharpen_A_apex`/`_sharpen_M_vertex`'s own docstrings already do),
the same way `canonical_counter.py` already gives every round counter
one shared reference shape instead of letting each letter's own
counter drift independently.
"""

from __future__ import annotations

import math

from ufoLib2.objects import Point


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


_STEP_FRACTION = 0.06  # how long each new step segment is, as a fraction
# of the cut's own length -- matched to 'c'/'s's own ratio (their step
# segments run 5-6% of their own cut's length at every weight checked)


def _square_off_terminal(pts, right_idx, left_idx) -> None:
    """Give a 2-point horizontal cut (`right_idx` -> `left_idx`, walking
    backward through the contour) 's's own genuinely flat, squared-off
    terminal construction -- curve end, a short PURELY VERTICAL 'step
    in', the horizontal cut itself, a short purely vertical 'step out',
    curve resumes -- instead of leaving it the tip of a long diagonal
    taper. Literally 's's own construction, mirrored where 'e'/'g's own
    approach curve runs the opposite way 's's does -- checked directly
    against BOTH of 's's own terminals (point inspection, every weight):
    every one of its four step segments is dx=0, exactly vertical,
    regardless of which direction the curve on either side of it happens
    to be heading -- not extrapolated along that curve's own tangent (an
    earlier version of this function's own mistake: 'vertical' is 's's
    own rule, not merely a byproduct of whatever angle a given curve
    happens to leave on).

    Confirmed by direct comparison against a real render (not just point
    inspection) that merely flattening the cut segment itself (this
    function's own first version, `pts[left_idx].y = pts[right_idx].y`)
    isn't enough to read as 's'/'c's own flat opening: both get there
    with FOUR dedicated on-curve points at each of their own terminals,
    not two, so the ink stays at close to full stroke width right up to
    a sharp, near-perpendicular corner. 'e'/'g' only ever had the two
    on-curve points bounding the cut itself.

    So this inserts the two missing points, the same way `serifs.py`
    adds foot contours: point-count-safe as long as it's applied
    identically on every master, which it is (this whole module runs
    once per master, unconditionally) -- see this module's own docstring.
    Each new point sits directly below/above (or, for a cut closer to
    vertical than horizontal -- see `_square_off_digit_notch`, the same
    species of defect turned 90 degrees -- directly beside) its own
    neighboring corner, stepping a fraction of the cut's own length in
    whichever direction continues that side's own existing approach/
    departure trend, so the two terminals this fixes each come out as
    their own mirror image of 's's, not a copy-pasted single direction.
    The corner point every reader actually sees (where Roboto Flex's own
    curve used to land) doesn't move at all; only its neighbor gets
    pulled back to make room for a real straight run into it."""
    right, left = pts[right_idx], pts[left_idx]
    entry_ctrl = pts[right_idx - 1]
    exit_ctrl = pts[(left_idx + 1) % len(pts)]

    horizontal_cut = abs(right.x - left.x) >= abs(right.y - left.y)
    if horizontal_cut:
        left.y = right.y
        cut_a, cut_b = (right.x, right.y), (left.x, left.y)
        step = abs(right.x - left.x) * _STEP_FRACTION
        entry_sign = 1.0 if right.y >= entry_ctrl.y else -1.0
        right.y += entry_sign * step
        exit_sign = 1.0 if exit_ctrl.y >= left.y else -1.0
        resume = (left.x, left.y + exit_sign * step)
    else:
        left.x = right.x
        cut_a, cut_b = (right.x, right.y), (left.x, left.y)
        step = abs(right.y - left.y) * _STEP_FRACTION
        entry_sign = 1.0 if right.x >= entry_ctrl.x else -1.0
        right.x += entry_sign * step
        exit_sign = 1.0 if exit_ctrl.x >= left.x else -1.0
        resume = (left.x + exit_sign * step, left.y)

    insertions = sorted(
        [
            (right_idx + 1, Point(*cut_a, type="line")),
            (left_idx + 1, Point(*resume, type="line")),
        ],
        key=lambda item: -item[0],
    )
    for pos, pt in insertions:
        pts.insert(pos, pt)


def _square_off_digit_notch(glyph, right_idx, left_idx) -> None:
    """'6'/'9's own version of `_square_off_terminal`, at the notch
    where the counter (split into its own contour by
    `ufo_build.py::_split_fused_digit_contour`) meets the ascender/
    descender stem -- the exact same defect, one contour later:
    Roboto Flex's own raw extraction connects them with a plain 2-point
    cut, no dedicated step points, so splitting the fused path into two
    clean contours (needed to fix 6/9's own weight-interpolation bug --
    see that function's own docstring) leaves that cut's own two
    endpoints as the new contour's closing edge, unrepaired -- confirmed
    directly (a real render) that it reads as a sharp wedge poking into
    the counter, the same diagonal-taper defect 'e'/'g' had, just this
    time closer to vertical than horizontal. `_square_off_terminal`
    itself already picks whichever axis a cut is closer to before
    deciding which way to flatten it and step, so the same call handles
    both without any extra branching here -- this wrapper only exists to
    find the OUTER contour's own closing edge after the digit split."""
    if len(glyph.contours) < 1:
        return
    pts = glyph.contours[0].points
    if len(pts) <= max(right_idx, left_idx):
        return  # not the outline shape this was written against
    _square_off_terminal(pts, right_idx, left_idx)


def _notch_terminal_6(glyph) -> None:
    """'6's own counter/stem notch -- see `_square_off_digit_notch`.
    23 points in the outer contour after `_split_fused_digit_contour`
    (indices 26..35, 0..12 of the original fused 36-point contour);
    the closing edge runs from its own last point (22) back to its
    first (0)."""
    if len(glyph.contours) != 2 or len(glyph.contours[0].points) != 23:
        return  # not the outline shape this was written against
    _square_off_digit_notch(glyph, 22, 0)


def _notch_terminal_9(glyph) -> None:
    """'9's own counter/stem notch -- see `_square_off_digit_notch`.
    24 points in the outer contour after `_split_fused_digit_contour`
    (indices 20..36, 0..6 of the original fused 37-point contour); the
    closing edge runs from its own last point (23) back to its first
    (0)."""
    if len(glyph.contours) != 2 or len(glyph.contours[0].points) != 24:
        return  # not the outline shape this was written against
    _square_off_digit_notch(glyph, 23, 0)


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


def _rigid_align_points(src_points, src_a, src_b, dst_a, dst_b):
    """Map every `(x, y)` in `src_points` through the single
    translate+rotate+uniform-scale transform that takes `src_a` -> `dst_a`
    and `src_b` -> `dst_b` exactly -- the same construction the point
    editor's own "paste over selection, aligned to neighbors" button
    uses, so a glyph built this way reproduces what hand-editing it there
    would give. Returns a list of `(x, y)` tuples, same length/order as
    `src_points`."""
    sv = (src_b[0] - src_a[0], src_b[1] - src_a[1])
    dv = (dst_b[0] - dst_a[0], dst_b[1] - dst_a[1])
    s_len = math.hypot(*sv) or 1.0
    d_len = math.hypot(*dv) or 1.0
    scale = d_len / s_len
    rot = math.atan2(dv[1], dv[0]) - math.atan2(sv[1], sv[0])
    cos_r, sin_r = math.cos(rot), math.sin(rot)
    out = []
    for x, y in src_points:
        rx, ry = (x - src_a[0]) * scale, (y - src_a[1]) * scale
        out.append((rx * cos_r - ry * sin_r + dst_a[0], rx * sin_r + ry * cos_r + dst_a[1]))
    return out


def graft_e_terminal_from_c(e_glyph, c_glyph) -> None:
    """Replace 'e's own terminal -- built by `_horizontal_terminal_e`
    into a plain squared-off, 5-point flat notch -- with a rigid-aligned
    copy of 'c's own REAL terminal curve (the 8-point bulge-then-flat-cut
    hook every 'c'/'s'-family letter actually has), instead of just
    matching its flatness.

    `_horizontal_terminal_e`'s squaring was a real improvement over
    Roboto Flex's own raw diagonal taper, but it was never actually the
    same shape as 'c's own terminal, just a flat cut in the same style
    -- confirmed directly by the project owner, hand-editing 'e' against
    an overlay of 'c' in the point editor at Thin/Regular/Black, that a
    flat cut isn't what "e's tail comes from c" means: it means this
    curve, literally, scaled to fit.

    Runs as a POST-pass, after every glyph in this master is fully
    built (see `ufo_build.py`'s own call site) -- not from inside
    `apply_quirks`, which only ever sees one glyph at a time and has no
    way to reach 'c's own final shape. It needs 'c' to be completely
    finished (through its own full quirks/counter-shape pipeline, not a
    raw extraction) or it copies the wrong curve.

    The anchors are `e_pts[3]`/`e_pts[12]` and `c_pts[3]`/`c_pts[12]` --
    on each glyph, the on-curve, smooth "shoulder" points immediately
    outside the whole arm/terminal structure (confirmed directly: both
    sit right at the point the main bowl curve stops and the terminal's
    own approach begins/ends, at the same role on both letters, not just
    the same index by coincidence -- `e`/`c` share that much of Roboto
    Flex's own point layout). A first version anchored on `e_pts[4]`/
    `e_pts[10]` (off-curve neighbors a step further in) instead --
    checked directly and confirmed wrong: those two sit much further
    apart, at a very different angle, than the true shoulder points do,
    so the rigid transform computed from them carried a huge, badly
    skewed scale (over 2x, confirmed by hand-checking the arithmetic
    against the actual built output) that blew the whole terminal miles
    outside the glyph's own bounding box. On-curve shoulder-to-shoulder
    anchors instead give a transform that's close to a plain, modest
    uniform scale (confirmed: under 1.5x at every real master, near-zero
    rotation) -- proportional, not distorting.

    Mapping `c_pts[3]` -> `e_pts[3]` and `c_pts[12]` -> `e_pts[12]` with
    `_rigid_align_points` is exactly the same move as the editor's own
    "paste over selection, aligned to its neighbors" -- 'c's own
    terminal (`c_pts[4:12]`, 8 points) lands scaled and rotated to fit
    the gap between 'e's own shoulders, replacing `e_pts[4:12]` (8
    points: the squared corner from `_horizontal_terminal_e` and its own
    step-in/cut/step-out, plus the curve either side of it) 1-for-1, no
    net point-count change, applied identically -- unconditionally,
    every master -- so point count/type sequence stays uniform across
    the whole design space, same as every other topology exception in
    this module."""
    if not e_glyph.contours or not c_glyph.contours:
        return
    e_pts = e_glyph.contours[0].points
    c_pts = c_glyph.contours[0].points
    if len(e_pts) != 34 or len(c_pts) != 32:
        return  # not the outline shapes this was written against
    if e_pts[3].type is None or e_pts[12].type is None:
        return
    if c_pts[3].type is None or c_pts[12].type is None:
        return

    e_anchor_a = (e_pts[3].x, e_pts[3].y)
    e_anchor_b = (e_pts[12].x, e_pts[12].y)
    c_anchor_a = (c_pts[3].x, c_pts[3].y)
    c_anchor_b = (c_pts[12].x, c_pts[12].y)

    graft_src = c_pts[4:12]
    aligned = _rigid_align_points(
        [(p.x, p.y) for p in graft_src], c_anchor_a, c_anchor_b, e_anchor_a, e_anchor_b
    )
    new_points = [
        Point(x, y, type=p.type, smooth=p.smooth) for (x, y), p in zip(aligned, graft_src)
    ]
    e_pts[4:12] = new_points


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


def _sharpen_A_apex(glyph) -> None:
    """Give capital 'A' the genuine sharp outer apex Jost draws (checked
    directly, point for point, against a real Jost TTF: both legs' own
    outer edges meet at exactly one point, (367, 744) at Bold), instead
    of Roboto Flex's own flattened one, then hand off to
    `_rebuild_A_counter_apex` for the counter's own separate inner apex
    -- a genuinely harder problem (see that function's own docstring),
    not safely fixable by simply moving its existing two points, which
    is why it gets its own dedicated construction instead.

    Point-by-point inspection shows 'A's single 14-point contour is NOT
    "an outer silhouette with the counter as a separate hole": it's ONE
    path that climbs the counter's own INNER edge first (points 0-1,
    the left foot, up through 2-3-4 to the TRUE outer apex at 5-6),
    comes back down the other inner edge (7-8-9, right foot at 10-11),
    then returns via the OUTER edges (11-12, the counter's own ceiling
    at 12-13, 13-0) to close. So points 5/6 -- not 12/13 -- are 'A's
    own OUTER apex; 12/13 is the COUNTER's own separate inner apex, the
    same role as v/w's own counter tip. 5/6 already sit at the
    identical Y (a purely horizontal flat run), so collapsing them is
    safe the same way `_sharpen_baseline_notches` already relies on for
    v/w's own bottom point -- only X moves, nothing else."""
    if not glyph.contours:
        return
    pts = glyph.contours[0].points
    if len(pts) != 14 or pts[5].type != "qcurve" or pts[6].type != "line":
        return  # not the outline shape this was written against
    outer_x = (pts[5].x + pts[6].x) / 2.0
    outer_y = (pts[5].y + pts[6].y) / 2.0
    pts[5].x, pts[5].y = outer_x, outer_y
    pts[6].x, pts[6].y = outer_x, outer_y
    _straighten_A_leg_approach(pts)
    _rebuild_A_counter_apex(glyph)


def _straighten_A_leg_approach(pts) -> None:
    """Reposition the off-curve control points either side of the apex
    (2/3/4 approaching it, 7/8/9 leaving it) so they sit exactly ON the
    straight line from `pts[2]`/`pts[9]` to the now-sharp apex, instead
    of wherever Roboto Flex's own slight curve left them -- degenerating
    that curve to a dead-straight leg without touching point count or
    type (still a `qcurve` chain, just a flat one; `_flatten_qcurve_pts`
    reading it afterward produces points that all fall on one line).

    Directly motivated by the project owner's own hand-edit in the point
    editor: given a straight leg, `_rebuild_A_counter_apex`'s own
    existing offset-and-intersect construction collapses to plain
    line-line offsetting -- trivial, and the two offset lines meet at
    ONE point with no risk of the baseline dip a curved approach forced
    (see `_largest_safe_width`'s own docstring for that history) --
    instead of writing a second, parallel construction to match the
    hand-edit by hand. Confirmed by rendering the result: this alone
    reproduces the same clean, sharp-counter look, at every real master,
    without needing to also touch `_rebuild_A_counter_apex` itself."""
    if len(pts) < 10:
        return
    apex = (pts[5].x, pts[5].y)
    for a_idx, off1, off2 in ((2, 3, 4), (9, 8, 7)):
        ax, ay = pts[a_idx].x, pts[a_idx].y
        for off_idx, t in ((off1, 1.0 / 3.0), (off2, 2.0 / 3.0)):
            pts[off_idx].x = ax + (apex[0] - ax) * t
            pts[off_idx].y = ay + (apex[1] - ay) * t


def _flatten_qcurve_pts(start, off_curve_pts, end, n=8):
    """The same TrueType-style quadratic-spline flattening `_square_off_terminal`'s
    own callers rely on elsewhere in this pipeline (a chain of quadratics,
    consecutive off-curve points implicitly joined by their own shared
    midpoint) -- reimplemented here, self-contained, purely as ANALYSIS to
    find where two hypothetical curves would cross; nothing this returns
    is written back into the glyph."""
    pts = []
    cur = start
    m = len(off_curve_pts)
    for i, ctrl in enumerate(off_curve_pts):
        nxt_on = end if i == m - 1 else ((off_curve_pts[i][0] + off_curve_pts[i + 1][0]) / 2.0, (off_curve_pts[i][1] + off_curve_pts[i + 1][1]) / 2.0)
        for step in range(1, n + 1):
            t = step / n
            ax = cur[0] + (ctrl[0] - cur[0]) * t
            ay = cur[1] + (ctrl[1] - cur[1]) * t
            bx = ctrl[0] + (nxt_on[0] - ctrl[0]) * t
            by = ctrl[1] + (nxt_on[1] - ctrl[1]) * t
            pts.append((ax + (bx - ax) * t, ay + (by - ay) * t))
        cur = nxt_on
    return pts


def _segments_cross(a, b, c, d):
    def ccw(p, q, r):
        return (r[1] - p[1]) * (q[0] - p[0]) > (q[1] - p[1]) * (r[0] - p[0])

    return ccw(a, c, d) != ccw(b, c, d) and ccw(a, b, c) != ccw(a, b, d)


def _segment_intersection(a, b, c, d):
    x1, y1 = a; x2, y2 = b; x3, y3 = c; x4, y4 = d
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-9:
        return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))


def _polyline_crossing(poly_a, poly_b):
    """Where `poly_a` and `poly_b` first cross, AND the index into each
    (the crossing sits between that index and the next) -- both are
    needed by `_resample_polyline` to know which portion of each
    original polyline is still valid to sample from."""
    for i in range(len(poly_a) - 1):
        for j in range(len(poly_b) - 1):
            if _segments_cross(poly_a[i], poly_a[i + 1], poly_b[j], poly_b[j + 1]):
                point = _segment_intersection(poly_a[i], poly_a[i + 1], poly_b[j], poly_b[j + 1])
                if point is not None:
                    return point, i, j
    return None, None, None


def _offset_curve(poly, sign, w):
    """Every point of `poly` (an already-flattened curve), offset by a
    CONSTANT perpendicular distance `w` from its own local tangent at
    that point (estimated from its immediate neighbors) -- a genuine,
    uniform-width parallel copy of `poly`, not merely a shape that
    happens not to cross it. `sign` picks which of the two perpendicular
    directions."""
    out = []
    n = len(poly)
    for i, p in enumerate(poly):
        if i == 0:
            dx, dy = poly[1][0] - poly[0][0], poly[1][1] - poly[0][1]
        elif i == n - 1:
            dx, dy = poly[-1][0] - poly[-2][0], poly[-1][1] - poly[-2][1]
        else:
            dx, dy = poly[i + 1][0] - poly[i - 1][0], poly[i + 1][1] - poly[i - 1][1]
        length = math.hypot(dx, dy)
        ux, uy = dx / length, dy / length
        nx, ny = -uy * sign, ux * sign
        out.append((p[0] + nx * w, p[1] + ny * w))
    return out


def _resample_polyline(poly, crossing_idx, tip, count, from_tip):
    """`count` points, evenly spaced by ARC LENGTH (not by index), along
    the portion of `poly` that's still valid once truncated at `tip`
    (the point `_polyline_crossing` found between `poly[crossing_idx]`
    and `poly[crossing_idx + 1]`) -- from `poly`'s own start up to
    `tip` when `from_tip` is False, or from `tip` onward to `poly`'s own
    end when `from_tip` is True.

    Which direction to keep matters, and isn't arbitrary: right where
    two curves meet at a shared point (a CUSP -- here, 'A's own true
    outer apex, where the left and right apex-approach curves meet),
    the tangent direction is discontinuous, so `_offset_curve`'s own
    per-point local-tangent estimate is unreliable in the curve's own
    few points nearest that cusp. Whichever side of `tip` sits close to
    the cusp has to be the side that's DISCARDED here -- confirmed
    directly: keeping it produced a spurious crossing against the
    apex's own true curve, an artifact of the bad tangent estimate
    right at the cusp, not a real safety problem.

    A FIXED `count`, not "however many samples happen to fall before
    the crossing" -- the crossing's own position (an index into a
    fixed-resolution sample array) varies smoothly with the master's
    own geometry, but which ARRAY INDEX it lands nearest can jump
    around between masters. Re-parametrizing by the truncated path's
    own arc length and sampling a fixed count from that is what keeps
    the point count identical at every master, the invariant this
    whole construction depends on."""
    if from_tip:
        chain = [tip] + poly[crossing_idx + 1 :]
    else:
        chain = poly[: crossing_idx + 1] + [tip]
    cumulative = [0.0]
    for i in range(1, len(chain)):
        cumulative.append(cumulative[-1] + math.hypot(chain[i][0] - chain[i - 1][0], chain[i][1] - chain[i - 1][1]))
    total = cumulative[-1]
    out = []
    for s in range(count):
        target = total * s / (count - 1)
        for i in range(1, len(cumulative)):
            if cumulative[i] >= target or i == len(cumulative) - 1:
                span = cumulative[i] - cumulative[i - 1]
                t = (target - cumulative[i - 1]) / span if span > 1e-9 else 0.0
                out.append((chain[i - 1][0] + (chain[i][0] - chain[i - 1][0]) * t, chain[i - 1][1] + (chain[i][1] - chain[i - 1][1]) * t))
                break
    return out


def _perpendicular_distance(p, line_a, line_b):
    dx, dy = line_b[0] - line_a[0], line_b[1] - line_a[1]
    length = math.hypot(dx, dy)
    return abs((p[0] - line_a[0]) * dy - (p[1] - line_a[1]) * dx) / length


_A_COUNTER_SAMPLE_COUNT = 6  # points sampled per side, evenly spaced by
# arc length -- see `_resample_polyline`'s own docstring for why this
# has to be a FIXED count rather than "however many happen to fall
# before the crossing"

_A_COUNTER_MAX_FOOT_DIP = 5.0  # units (UPM 2048) the new inner-foot
# point (`foot1`/`foot2` in `_largest_safe_width`) is allowed to sit
# below the baseline -- see that function's own docstring for why this
# can't be a hard 0.0 floor. 30.0 (an earlier value here) technically
# worked but still read wrong once the leg approach was straightened
# (see `_straighten_A_leg_approach`): with a straight leg, the segment
# from the OUTER foot corner down to this dipped point runs nearly
# parallel to the baseline over a long span (confirmed directly: ~700
# units at Black), so even a "small" 30-unit dip reads as a long,
# visible underhang, not a subtle notch. 5.0 keeps that same segment
# close enough to flush that it reads as sitting on the baseline.


def _offset_point(p, dx, dy, sign, w):
    """`p` offset by `w`, perpendicular to direction `(dx, dy)` (the
    same sign convention as `_offset_curve`'s own per-point step) --
    the single-point version, used where the direction is already
    known exactly (a straight segment's own two endpoints), not
    estimated from neighbors."""
    length = math.hypot(dx, dy)
    ux, uy = dx / length, dy / length
    nx, ny = -uy * sign, ux * sign
    return (p[0] + nx * w, p[1] + ny * w)


def _largest_safe_width(curve1, curve2, p0, p1, p2, p10, p9, p11, w_cap, iterations=40):
    """The largest constant offset width, up to `w_cap`, for which the
    two apex-approach curves' own constant-width offsets (`_offset_curve`,
    extended down to the real foot corners -- see `_rebuild_A_counter_apex`'s
    own docstring for why) still cross at a genuine corner, at or above
    the baseline, without the new edge crossing back over the real
    `p1`/`p10` corner it passes on its way down to `p0`/`p11`.

    Extending all the way down to the foot -- not just offsetting the
    curve's own short apex-adjacent run, tried first -- matters:
    confirmed directly that the short-curve-only version silently capped
    the width far below what the terminal's own gap actually allows at
    Regular and heavier (the corner these masters' own true target width
    needs sits BELOW where the short curve even starts, so a search
    confined to it finds nothing and falls back to whatever narrower
    width happens to fit, independent of how much wider the terminal
    itself keeps getting) -- exactly backwards from a real stroke, whose
    width should grow with weight, not plateau.

    The foot point itself (`foot1`/`foot2`, inside `crossing_at`) is a
    plain perpendicular offset of `p1`/`p10` (`_offset_point`) -- NOT a
    genuine miter join with the foot cut's own offset line, tried next
    and confirmed wrong by an actual self-intersection sweep (a render
    alone missed it): walking the diagonal's own offset line up to meet
    the foot cut's own offset (at Y=`w`, the mathematically "correct"
    corner for two edges meeting at `p1`) moves the foot point far
    enough along the diagonal's own offset that the closing edge back
    to `p0` crosses back OVER `p1`/`p10` itself -- a real point still in
    the contour, not something a later edge can route past. A plain
    perpendicular offset stays close enough to the real corner to avoid
    that -- at the cost of the offset foot landing below the baseline
    when the width pushed that far, which a first version of this
    function let happen (writing it off as a small cosmetic
    compromise); rendered, it's not small -- a visible gash cut into
    the bottom of the counter at Regular and heavier, invisible to the
    self-intersection sweep since nothing actually crosses. `crossing_at`
    now checks both the crossing (`_segments_cross`) AND that `foot1`/
    `foot2` stay at or above y=0, rather than trusting either
    construction to work out on its own.

    Shrinking the width always eventually works: as it shrinks toward
    zero, each offset curve shrinks toward the ORIGINAL, un-offset
    curve, and the two original curves already share one point (the true
    apex itself) -- so their crossing point converges toward the apex,
    comfortably above the baseline. And the relationship is monotonic
    (confirmed directly): a narrower width's own corresponding corner
    always sits closer to the apex than a wider width's does, never
    further. So a plain bisection between 0 and `w_cap` -- first
    checking whether `w_cap` itself already works, the common case at
    Thin/ExtraLight -- finds the largest safe width directly, no
    guessing needed."""

    def crossing_at(w):
        # `foot1`/`foot2` anchor the new inner edge back to the REAL
        # `p0`/`p11` corners, so they have to sit on `p0`/`p11`'s own
        # side of the diagonal (`p1`->`p2`/`p10`->`p9`) -- otherwise the
        # closing edge (`foot1`->`p0`) crosses that diagonal itself,
        # since `p1` is a genuine, separate point still in the contour,
        # not something this edge can route around. Two earlier
        # versions got this wrong in opposite directions, both confirmed
        # by a real self-intersection sweep (not just a render, which
        # missed both): walking the diagonal's own offset line to
        # exactly Y=0 (or to Y=`w`, a genuine miter join with the flat
        # foot cut's own offset -- correct in isolation, but it walks
        # far enough up the line to land on the WRONG side of `p1`
        # relative to `p0`) both put `foot1`/`foot2` past that boundary.
        # A plain perpendicular offset of `p1`/`p10` themselves doesn't
        # have that failure mode -- it stays close to the real corner --
        # so this checks it directly (`_segments_cross`) rather than
        # trusting the geometry to work out.
        foot1 = _offset_point(p1, p2[0] - p1[0], p2[1] - p1[1], -1, w)
        foot2 = _offset_point(p10, p9[0] - p10[0], p9[1] - p10[1], 1, w)
        if _segments_cross(p0, foot1, p1, p2) or _segments_cross(p11, foot2, p10, p9):
            return None
        if foot1[1] < -_A_COUNTER_MAX_FOOT_DIP or foot2[1] < -_A_COUNTER_MAX_FOOT_DIP:
            return None  # the earlier version let a wide-enough width push
            # `foot1`/`foot2` below the baseline with NO limit at all -- at
            # Regular and heavier, where the diagonal's own angle is
            # shallow, that perpendicular offset is mostly VERTICAL, not
            # horizontal, and the foot lands so far below y=0 (confirmed
            # directly: ~150-190 units at Black) that it reads as a real,
            # visible gash cut into the bottom of the counter (confirmed by
            # rendering it, not just by the self-intersection sweep, which
            # never flagged it since the two new edges don't cross anything
            # -- they just dip below the glyph's own baseline). A hard
            # floor at exactly y=0 is too strict, though -- confirmed
            # directly that `p1`/`p10` themselves already sit AT y=0 in
            # this source, so ANY positive width dips at least a little,
            # and a strict >=0 floor made every bisection here return None,
            # silently skipping the whole rebuild (a topology break far
            # worse than the dip: it leaves that master's own point count
            # at the raw, unrebuilt 14 instead of the uniform 23 every
            # other master gets, which corrupts gvar interpolation for
            # every wght between it and its rebuilt neighbors -- exactly
            # the self-intersecting garbage the sweep then found at low
            # wght, nothing to do with the counter construction itself).
            # `_A_COUNTER_MAX_FOOT_DIP` allows the small, ordinary amount
            # (comparable to a typographic overshoot) every safe width at
            # light weights already produces, while still capping the
            # runaway dip at heavy weights down to whatever width the
            # shallow apex angle actually allows within that tolerance.
        off1 = [foot1] + _offset_curve(curve1, -1, w)
        off2 = _offset_curve(curve2, -1, w) + [foot2]
        tip, i, j = _polyline_crossing(off1, off2)
        if tip is None or tip[1] < 0:
            return None  # a genuine crossing has to exist, at or above
            # the baseline -- checked directly (see this function's own
            # docstring)
        return tip, i, j, off1, off2

    result = crossing_at(w_cap)
    if result is not None:
        return w_cap, result
    lo, hi = 0.0, w_cap
    best = None
    for _ in range(iterations):
        mid = (lo + hi) / 2.0
        result = crossing_at(mid)
        if result is not None:
            best = (mid, result)
            lo = mid
        else:
            hi = mid
    return best


def _rebuild_A_counter_apex(glyph) -> None:
    """Give capital 'A's own counter a genuine inner apex, replacing its
    two flat-notch points (12/13) with a real, genuinely PARALLEL curve
    -- the actual fix for the self-intersection `_sharpen_A_apex`'s own
    docstring proves is impossible to solve by moving 12/13 alone,
    given the topology that fix left untouched.

    Exhaustive analysis (searching every notch height, width, and even
    single-point placements, documented in `_sharpen_A_apex`'s own
    docstring) proved the counter's own ceiling can never be a flat,
    two-point notch here: at every height, the boundary that keeps it
    clear of the outer leg's own straight edge and the boundary that
    keeps it clear of the curve leading to the outer apex don't
    overlap. The reason is structural, not a tuning problem: the
    counter's own straight edge (0->13, 11->12) runs dead straight all
    the way from the foot, while the curve it has to stay clear of
    (2->3->4->apex) genuinely curves -- two edges with different shapes
    can't maintain a safe, consistent separation.

    A first attempt here built the new edge by offsetting the
    apex-approach curve INWARD, TAPERING linearly from zero (at the
    foot) all the way up to the tip. It passed the self-intersection
    sweep, but was wrong regardless -- confirmed directly (measuring the
    perpendicular distance between the new edge and the true
    apex-approach curve at several points) that a LINEAR taper all the
    way to the tip means the stroke's own width is never constant
    anywhere: the two edges are never actually parallel, which is not
    how a real stroke is drawn, self-intersection-free or not.

    Told directly by the project owner, after that first attempt, what
    the right target actually is: the counter's own inner apex and the
    outer apex should sit the SAME DISTANCE apart as the terminal's own
    inner and outer points already do (`p0`/`p1` at the left foot,
    `p11`/`p10` at the right) -- i.e. this counter, like `v`/`w`'s own,
    should read as one genuinely constant-width stroke from foot to tip,
    not a stroke that tapers away near the point. `foot_w_left`/
    `foot_w_right` measure that terminal gap directly (perpendicular
    distance from the OUTER foot corner to the line through the INNER
    foot corner and the curve's own next point) -- `w_cap`, the smaller
    of the two, is the target width this construction tries to hold
    constant all the way to the tip.

    Holding it EXACTLY, though, isn't always geometrically possible:
    checked directly (see `_largest_safe_width`'s own docstring) that at
    some masters -- Regular and heavier, where Roboto Flex's own
    original apex angle is shallow enough that a stroke of the
    terminal's own full width would need to converge to a point below
    the baseline -- the terminal's own width has no valid, physically
    real single-point apex at all. `_largest_safe_width` extends the
    search all the way down to the real foot corners (`_offset_point`,
    not just the short apex-adjacent curve run an earlier version of
    this function tried first and confirmed capped the width far too
    aggressively -- see that function's own docstring) and finds the
    largest width, up to the terminal target, whose corresponding
    corner is still at or above the baseline, without crossing back
    over `p1`/`p10` on its way to `p0`/`p11`. Since a
    NARROWER constant width's own corresponding corner sits closer to
    the true tip (confirmed directly, monotonically), this holds the
    terminal's own exact width whenever geometry allows it (every master
    at Thin/ExtraLight, and now Regular/Bold too, not just the two
    lightest weights an earlier version of this construction managed),
    and gets as close to it as the apex angle actually permits at the
    very heaviest weights, rather than picking an arbitrary width that
    doesn't track weight at all or silently falling back to Roboto
    Flex's own broken notch.

    The two constant-width offset curves (`_offset_curve`, one from each
    side, at that width, extended down to the real foot corners) genuinely
    cross at a real corner -- `_polyline_crossing` finds that point, the
    counter's own new, real, single-point apex. Building each side is
    `_resample_polyline`'s own job: a FIXED count of points, evenly
    spaced by arc length, from that real foot corner up to the shared
    apex point.

    This is a deliberate topology exception, the same kind
    `_square_off_terminal` already is for e/g/6/9's terminal (see this
    module's own top-of-file docstring): it replaces 2 points (12/13)
    with `2 * _A_COUNTER_SAMPLE_COUNT + 1` new ones, applied identically
    -- the same computation, unconditionally -- on every master, so the
    point count/type sequence stays identical across the whole design
    space even though it's different from Roboto Flex's own original
    count. Verified both ways: a real self-intersection sweep (flattened
    curves, every 5 units of `wght`, 180-900) is clean at every weight
    tested, AND the new edge measures as genuinely constant-width
    (parallel) against the apex-approach curve, not just non-crossing."""
    pts = glyph.contours[0].points
    if len(pts) != 14 or pts[12].type != "line" or pts[13].type != "line":
        return  # not the outline shape this was written against, or
        # already rebuilt by a previous pass -- either way, leave alone
    p0, p1, p2 = (pts[0].x, pts[0].y), (pts[1].x, pts[1].y), (pts[2].x, pts[2].y)
    p3, p4 = (pts[3].x, pts[3].y), (pts[4].x, pts[4].y)
    apex = (pts[5].x, pts[5].y)
    p7, p8, p9 = (pts[7].x, pts[7].y), (pts[8].x, pts[8].y), (pts[9].x, pts[9].y)
    p10, p11 = (pts[10].x, pts[10].y), (pts[11].x, pts[11].y)
    if apex[1] <= p2[1] or apex[1] <= p9[1]:
        return  # degenerate proportions this construction wasn't built for

    curve1 = [p2] + _flatten_qcurve_pts(p2, [p3, p4], apex)
    curve2 = [apex] + _flatten_qcurve_pts(apex, [p7, p8], p9)

    foot_w_left = _perpendicular_distance(p0, p1, p2)
    foot_w_right = _perpendicular_distance(p11, p10, p9)
    w_cap = min(foot_w_left, foot_w_right)

    result = _largest_safe_width(curve1, curve2, p0, p1, p2, p10, p9, p11, w_cap)
    if result is None:
        return  # no safe width found at all -- leave the glyph as-is
        # rather than guess (checked by the self-intersection sweep at
        # every real master; if this ever fires, the sweep catches it
        # immediately rather than silently shipping a bug)
    _w, (tip, i, j, off1, off2) = result

    left_pts = _resample_polyline(off1, i, tip, _A_COUNTER_SAMPLE_COUNT, from_tip=False)
    right_pts = _resample_polyline(off2, j, tip, _A_COUNTER_SAMPLE_COUNT, from_tip=True)

    outer_points = list(reversed(right_pts)) + list(reversed(left_pts))[1:]
    new_points = [Point(x, y, type="line") for x, y in outer_points]
    pts[12:14] = new_points


_A_CROSSBAR_MIN_HEIGHT = 2.0  # units; how tall a 4-point all-'line'
# contour has to be to count as the real crossbar -- this runs as part
# of `apply_quirks`, BEFORE `serifs.py::apply_feet` adds its own foot
# rectangles (also 4-point, all-'line'), so the crossbar is the only
# such contour that exists yet; this is a low floor purely against a
# degenerate zero-height contour, not a filter against anything real.
# Checked directly against every real master's own crossbar height,
# including the smallest (Condensed Thin, ~6.7 units) -- an earlier,
# much higher threshold (50.0) here silently skipped Thin/ExtraLight
# entirely, since Roboto Flex's own crossbar is genuinely only a few
# units tall at those weights, leaving their own overhang unfixed.


def _fit_A_crossbar(glyph) -> None:
    """Pull capital 'A's own crossbar in so its left/right corners land
    exactly on the legs' own outer edge, instead of overhanging past it
    -- confirmed directly (a real render, every weight checked) that
    Roboto Flex's own raw crossbar is simply WIDER than the legs are at
    both of its own heights, by a roughly constant horizontal amount on
    each side (not proportional to the leg's own slope), so it visibly
    pokes out past the leg's own diagonal edge on both ends instead of
    meeting it flush -- worse at heavier weights, where the overhang is
    large enough to read as its own little "wing" at each corner rather
    than a subtle optical extension.

    The legs' own outer edge, at the crossbar's own two heights, is
    still the plain straight run from each foot corner (`pts[1]`/
    `pts[10]`, the INNER-facing foot points, not `pts[0]`/`pts[11]`
    themselves -- see `_rebuild_A_counter_apex`'s own docstring for why
    `pts[1]`/`pts[10]` mark where that straight run actually begins) up
    to where the curve to the apex begins (`pts[2]`/`pts[9]`) --
    confirmed the crossbar's own height range sits well below where
    that curve starts at every master, so this is always a single
    straight-line lookup, never needing the curve itself. Finds the
    crossbar itself structurally (a 4-point, all-'line' contour taller
    than `_A_CROSSBAR_MIN_HEIGHT`) rather than assuming a fixed contour
    index, the same defensive pattern `_kick_R` already uses -- this
    runs before `serifs.py::apply_feet` adds any foot contours, but
    matching by shape rather than position costs nothing and stays
    correct even if that ever changes.

    Only ever moves each corner along X, onto the leg's own existing
    line -- never changes the crossbar's own height or Y positions, so
    this can't interact with `arch_shape.py`/`counter_shape.py`'s own
    handling of the crossbar-meets-leg counter above it."""
    if len(glyph.contours) < 2:
        return
    outline = glyph.contours[0].points
    if len(outline) < 12 or outline[2].type != "line" or outline[10].type != "line":
        return  # not the outline shape this was written against -- a
        # point's own `type` names the segment ARRIVING at it, so
        # `outline[2]` (ending the straight 1->2 run) and `outline[10]`
        # (ending the straight 9->10 run) are the ones that must read
        # "line"; `outline[9]` legitimately reads "qcurve" instead (it
        # ends the curve chain down from the apex), not a sign anything
        # is wrong
    left_a, left_b = (outline[1].x, outline[1].y), (outline[2].x, outline[2].y)
    right_a, right_b = (outline[10].x, outline[10].y), (outline[9].x, outline[9].y)

    crossbar = None
    for contour in glyph.contours[1:]:
        pts = contour.points
        if len(pts) != 4 or any(p.type != "line" for p in pts):
            continue
        ys = [p.y for p in pts]
        if max(ys) - min(ys) >= _A_CROSSBAR_MIN_HEIGHT:
            crossbar = pts
            break
    if crossbar is None:
        return

    for p in crossbar:
        left_x = _x_on_line_at_y(left_a, left_b, p.y)
        right_x = _x_on_line_at_y(right_a, right_b, p.y)
        if left_x is None or right_x is None:
            continue
        # whichever line's own X is closer to this corner's own existing
        # X is the leg this particular corner belongs to -- left corners
        # sit near the left leg, right corners near the right, without
        # needing to assume a fixed point order
        p.x = left_x if abs(p.x - left_x) <= abs(p.x - right_x) else right_x


def _x_on_line_at_y(a, b, y):
    if a[1] == b[1]:
        return None
    t = (y - a[1]) / (b[1] - a[1])
    return a[0] + t * (b[0] - a[0])


def fit_A_serif_feet(glyph, serif_amount: float) -> None:
    """Resize `serifs.py::apply_feet`'s own two foot rectangles (already
    added to `glyph` by the time this runs -- see this function's own
    caller in `ufo_build.py`) so each one's own un-flared run spans
    EXACTLY the real foot cut it belongs to (`p0`->`p1` on the left,
    `p10`->`p11` on the right), instead of `detect_feet`'s own
    fractional width -- confirmed directly (a real render, Black
    weight) that the fractional width leaves a visible gap between the
    foot rectangle's own top edge and the leg's own foot corner.

    The gap is structural, not a tuning problem: `detect_feet` measures
    the foot cut's own run length ONCE, as a fraction of ONE reference
    master's own glyph width, and `apply_feet` reproduces it at every
    OTHER master by multiplying that same fraction by THAT master's own
    width -- correct only if the foot run's own width grows in the same
    proportion the whole glyph's advance width does. Checked directly:
    'A's own foot run grows roughly twice as fast, weight for weight,
    as its own advance width does (the legs splay outward with weight
    much faster than the sidebearings shrink to compensate), so the
    fractional reproduction increasingly undershoots the real span at
    heavier weights -- by nearly 90 units at Black.

    Recomputes the SAME construction `apply_feet` itself uses (a run
    width, grown by `serif_amount`-scaled `extra` on both sides, then a
    height proportional to that run width) -- just sourced from this
    master's own real `p0`-`p1`/`p10`-`p11` span instead of an inherited
    fraction, so the two stay numerically identical at the one
    reference weight `detect_feet` was measured from, and only diverge
    (correctly) as weight moves away from it.

    Finds the two foot rectangles structurally (a 4-point, all-'line'
    contour whose own bottom edge sits at the baseline, `_A_CROSSBAR_MIN_HEIGHT`'s
    own crossbar comfortably excluded by sitting well above it) rather
    than by a fixed contour index, since `serifs.py::apply_feet` can
    add other letters' own feet at different counts/positions -- this
    only ever touches contours that are actually feet."""
    if len(glyph.contours) < 3:
        return
    outline = glyph.contours[0].points
    if len(outline) < 12:
        return
    p0 = (outline[0].x, outline[0].y)
    p1 = (outline[1].x, outline[1].y)
    p10 = (outline[10].x, outline[10].y)
    p11 = (outline[11].x, outline[11].y)
    left_span = tuple(sorted((p0[0], p1[0])))
    right_span = tuple(sorted((p10[0], p11[0])))

    feet = [
        contour.points
        for contour in glyph.contours[1:]
        if len(contour.points) == 4
        and all(p.type == "line" for p in contour.points)
        and min(p.y for p in contour.points) <= 5.0
    ]
    if len(feet) != 2:
        return  # not the shape this was written against -- either
        # `apply_feet` didn't add exactly two baseline feet for this
        # master, or something upstream changed; leave it alone

    left_run_w = left_span[1] - left_span[0]
    right_run_w = right_span[1] - right_span[0]
    if left_run_w <= 0 or right_run_w <= 0:
        return
    # Both feet share ONE height, from the narrower side's own run --
    # confirmed directly (the project owner, looking at a render) that
    # computing each foot's own height from only ITS OWN local run width
    # left the two feet at visibly different heights, their own top
    # edges not level with each other: Roboto Flex's own raw `p0`-`p1`
    # and `p10`-`p11` spans aren't actually equal (roughly 150 units
    # apart at Black), so two independently-sized feet faithfully reproduced
    # that asymmetry instead of reading as one matched pair. A real
    # slab-serif foot doesn't split into two different heights depending
    # on which leg happens to be a little wider -- shared_run_w, the
    # smaller of the two (the same conservative choice this module
    # already makes wherever two candidate widths disagree -- see
    # `_rebuild_A_counter_apex`'s own `w_cap`), is what both feet size
    # their OWN height from; each foot still gets its OWN width, sized
    # to its own real span, only the height is shared.
    shared_run_w = min(left_run_w, right_run_w)
    foot_h = 1.0 + serif_amount * (shared_run_w * 0.42) / 100.0

    for pts in feet:
        cx = sum(p.x for p in pts) / 4.0
        left_mid = (left_span[0] + left_span[1]) / 2.0
        right_mid = (right_span[0] + right_span[1]) / 2.0
        x0, x1 = left_span if abs(cx - left_mid) <= abs(cx - right_mid) else right_span
        run_w = x1 - x0
        extra = serif_amount * (run_w * 0.9) / 100.0
        new_x0, new_x1 = x0 - extra / 2.0, x1 + extra / 2.0
        # `g.rect`'s own point order is always (x0,y0), (x1,y0),
        # (x1,y1), (x0,y1) with y0 < y1 -- see `geometry.py::rect` --
        # and every foot this function matches has y0 == 0 (the
        # baseline itself), so writing by POSITION is safe here, not
        # a guess at which corner is which.
        pts[0].x, pts[0].y = new_x0, 0.0
        pts[1].x, pts[1].y = new_x1, 0.0
        pts[2].x, pts[2].y = new_x1, foot_h
        pts[3].x, pts[3].y = new_x0, foot_h


def _sharpen_A(glyph) -> None:
    """Capital 'A's own two genuine points -- see `_sharpen_A_apex`'s own
    docstring for the outer apex (a plain full collapse), and
    `_rebuild_A_counter_apex`'s own docstring for the counter's own
    inner apex (a real, genuinely parallel curve replacing the old flat
    notch, a deliberate topology exception). `_sharpen_apex_notches`
    still runs after both as a safety net for any OTHER flat run this
    glyph might carry -- a no-op on the outer apex (already fully
    collapsed, `a.x == b.x`, which that function's own scan already
    skips); the counter apex's own new points are ordinary 'line'
    points along a real curve, none of them a flat run at all, so that
    scan has nothing there to find. `_fit_A_crossbar` runs last, pulling
    the crossbar's own corners flush with the legs -- see its own
    docstring."""
    _sharpen_A_apex(glyph)
    _sharpen_apex_notches(glyph)
    _fit_A_crossbar(glyph)


def _sharpen_M_vertex(glyph) -> None:
    """Deliberately a no-op for now -- see this docstring for why, since
    the obvious fix (collapse the flattened vertices, the same
    Jost-referenced idea as `_sharpen_A_apex`) turned out unsafe here
    for the identical reason `_sharpen_A_apex`'s own docstring documents
    in detail for 'A's counter apex, just with more interacting points.

    'M's single 34-point contour interleaves INNER and OUTER edges the
    same way 'A's does: it climbs the left stem's own INNER edge, kinks
    into the diagonal at a notch (5/6), descends to the V's own bottom,
    crosses to the right stem's INNER edge, kinks at a second notch
    (15/16), then -- after the right stem's own OUTER edge -- comes
    back down as the OUTER diagonal to the V's own OUTER-path bottom
    vertex (27/28), and closes via the left stem's own OUTER edge,
    kinking at a THIRD notch (32/33, mirrored at 22/23).

    Every attempt tried here -- full collapse of just 5/6/15/16/27/28;
    the same with `_APEX_BLEND`'s partial collapse instead; full
    collapse of all five pairs including the two previously-untouched
    OUTER notches -- was confirmed unsafe by an actual self-intersection
    sweep (flattened curves, `wght` 180-900), and each fix attempt didn't
    just fail to help, it relocated the crossing to a different pair of
    edges rather than removing it: collapsing 5/6/15/16/27/28 alone left
    the INNER curve approaching each notch free to cross the untouched
    OUTER notch right next to it; collapsing the OUTER notches too then
    made THEM cross the stem's own inner edge instead. This is the same
    root cause `_sharpen_A_apex`'s own docstring works through in detail
    for 'A': the crossing is present even in the original merged build
    with no 'M' quirk at all (confirmed directly), it's a same-master
    bug baked into Roboto Flex's own low-weight extraction, and there is
    no single placement of these on-curve points, within the current
    34-point topology, that clears every nearby edge at once -- fixing
    it for real needs a topology change (a new point, the same kind of
    deliberate exception `_square_off_terminal` already uses elsewhere
    in this module), not another point-position guess. Left as a
    tracked follow-up rather than shipped as a fix that only moves the
    bug around."""
    return


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
    "6": _notch_terminal_6,
    "9": _notch_terminal_9,
    "A": _sharpen_A,
    "M": _sharpen_M_vertex,
}
