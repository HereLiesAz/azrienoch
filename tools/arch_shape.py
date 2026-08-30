"""Give an arch letter's counter-facing curve ('n'/'h'/'m'/'u') the same
round character as the closed counters in 'o'/'d'/'b'/'p'/'q'/'g'/'a' --
extending `canonical_counter.py`'s "reuse 'o's own outer contour as the
reference shape" idea to an open arch instead of a closed loop.

'e's upper counter has the identical problem for the identical reason
(Roboto Flex's own type-e counter span, structurally, is `o`'s first 8
points too -- a "waist" through one corner to the next "waist," entry
and exit inclusive) but isn't found by `arch_symmetry.find_spring_pairs`
(tuned for a stem meeting a curve, not a crossbar meeting a bowl), so it
goes through `reshape_named_span` below with its own indices hardcoded
directly, the same way `quirks.py` already hardcodes per-glyph indices
for its own single-character edits. Confirmed those indices are stable
across weight (the topology invariant every master already satisfies)
before relying on them, and `reshape_named_span` still checks the
entry/exit points' own on/off-curve types before touching anything, so
this never silently reshapes the wrong span if that assumption ever
stops holding.

An arch's counter isn't a separate contour the way a bowl's is -- it's a
curve spanning between the two spring points `arch_symmetry.py` already
finds (where a stem meets the arch), embedded in the letter's single
outer contour. Point inspection confirms this curve is structurally
identical, point-type for point-type, to the first 7 points of 'o's own
14-point template (`line, off, off, qcurve, off, off, qcurve` -- a
"waist" through one corner to the next "waist"): true for 'n', 'h', both
of 'm's arches, and 'u' alike, at every weight tested.

Rigidly copying the template's coordinates the way `canonical_counter.py`
does for a closed counter doesn't work here, though -- tried first,
verified visually, and it distorts badly: the spring points aren't free
to move (unlike a bowl's counter, which owns its own independent
contour, an arch's spring points are shared with the stems on either
side and must stay exactly where they are, or the outline kinks at the
join). Instead, `reshape_arch_counters` solves the *similarity*
transform (rotation + uniform scale + translation -- exactly determined
by 2 point correspondences) that maps the template's own matching span
onto the target's own spring points exactly as they already are, then
applies that same transform to the points in between. The spring points
themselves never move; only the curve's shape between them changes,
becoming a true scaled-and-rotated copy of 'o's own curve instead of
Roboto Flex's flatter native one.

Only ever moves the points strictly between a matched entry/exit spring
pair -- never a spring point itself, never anything outside the pair --
so topology is unaffected and the outer silhouette (traced by a
completely different, untouched part of the same contour) never moves.

A plain rotation isn't always enough, the same way a plain rotation
wasn't enough for the closed-counter case in `canonical_counter.py`
(there it could turn a hole into solid fill; here it can bulge the curve
the wrong way). Checked directly: 'o's own template curve bulges to one
side of its own start-end chord, but the *sign* of which side a target
arch bulges to, relative to *its* chord, isn't guaranteed to match --
confirmed by rendering: a first version using pure rotation gave 'n' and
'h' a curve that only looked right by chance (their sign happened to
need no correction) while 'u's came out visibly flattened (its sign
needed the mirror and didn't get it). Fixed by decomposing each
template point into (along-chord, perpendicular-to-chord) components in
the template's own frame, checking whether the target's own original
curve bulges to the same perpendicular side its template counterpart
does (via a signed cross product, not eyeballed), flipping the
perpendicular sign when it doesn't, and only then rebuilding the point
in the target's frame -- so the fix is verified per spring pair, not
assumed from one visually-plausible case.

A *uniform* scale (one factor for both the along-chord and the
perpendicular/bulge direction) isn't right either -- caught by the user
looking at 'm'/'u' at Thin, where the arch reads as a fat, ballooning
blob instead of the same even hairline the rest of the letter has.
Measured why: 'o's own bulge-to-chord ratio changes a lot across the
weight range (0.64 at Thin down to 0.33 at Black -- 'o' opens up
proportionally more at Thin, matching how a thin stroke needs a more
generous curve to still read clearly), and at Black that ratio happens
to be close to the arch's own native one (0.32), so the uniform-scale
version looked fine there and only fell apart at the opposite extreme.
The fix scales the two directions separately: `scale_along` still fits
the chord length (unchanged, needed to reach the fixed spring points
exactly), but `scale_perp` fits the template's bulge to *this letter's
own native bulge depth* (measured from its own unmodified points before
any are moved), not to the template's. That borrows only the curve's
shape/quality (smoothness, no waist-flattening) from 'o', while leaving
how far it actually bulges to what Roboto Flex already tuned correctly
for that specific weight -- confirmed this way (chord-length ratio
alone at Regular, wght 400) already lands within a few percent of
'o's own ratio there too, so Black's "just happens to match" isn't a
coincidence limited to one weight; it's what the native design already
does, and Thin was the one place the mismatch was big enough to see.
"""

from __future__ import annotations

import math

from tools import arch_symmetry as AS
from tools import canonical_counter as CC


def _reshape_span(pts, n, entry_idx, exit_idx, template_pts, template_types) -> bool:
    """The actual per-span similarity-transform reshape described in this
    module's docstring: find a same-length, same-type-sequence run in
    `template_pts` starting anywhere in it, solve the along-chord +
    perpendicular-bulge transform that maps that run onto `pts`'s own
    fixed entry/exit points, and apply it to every point strictly between
    them. Returns True if a matching template run was found and applied.
    Shared by `reshape_arch_counters` (which locates entry/exit pairs
    structurally, via `arch_symmetry.find_spring_pairs`) and any caller
    that already knows its own glyph's fixed entry/exit indices (e.g.
    'e's counter -- see `reshape_named_span`)."""
    span = exit_idx - entry_idx if exit_idx > entry_idx else (n - entry_idx + exit_idx)
    span_len = span + 1
    tn = len(template_pts)
    if span_len < 3 or span_len > tn:
        return False
    target_types = [CC._type_key(pts[(entry_idx + k) % n]) for k in range(span_len)]
    offset = None
    for o in range(tn):
        if all(target_types[k] == template_types[(o + k) % tn] for k in range(span_len)):
            offset = o
            break
    if offset is None:
        return False

    start = pts[entry_idx]
    end = pts[exit_idx]
    t_start = template_pts[offset]
    t_end = template_pts[(offset + span_len - 1) % tn]
    vt = (t_end.x - t_start.x, t_end.y - t_start.y)
    vt_len = math.hypot(*vt)
    vtar = (end.x - start.x, end.y - start.y)
    vtar_len = math.hypot(*vtar)
    if vt_len < 1e-6 or vtar_len < 1e-6:
        return False
    ux, uy = vt[0] / vt_len, vt[1] / vt_len  # template chord unit vector
    tux, tuy = vtar[0] / vtar_len, vtar[1] / vtar_len  # target chord unit vector
    scale_along = vtar_len / vt_len

    # Snapshot the target's own current points before any of them
    # move, and use them to measure how far this letter's own curve
    # already bulges from its chord -- see module docstring for why
    # the bulge needs its own scale, separate from the along-chord
    # one, rather than reusing scale_along for both.
    original = [(pts[(entry_idx + k) % n].x, pts[(entry_idx + k) % n].y) for k in range(span_len)]
    native_max_perp = 0.0
    template_max_perp = 0.0
    mid_k = span_len // 2
    template_perp_at_mid = 0.0
    target_perp_at_mid = 0.0
    for k in range(1, span_len - 1):
        ox, oy = original[k]
        dxo, dyo = ox - start.x, oy - start.y
        perp_o = tux * dyo - tuy * dxo
        native_max_perp = max(native_max_perp, abs(perp_o))
        tp = template_pts[(offset + k) % tn]
        dxt, dyt = tp.x - t_start.x, tp.y - t_start.y
        perp_t = ux * dyt - uy * dxt
        template_max_perp = max(template_max_perp, abs(perp_t))
        if k == mid_k:
            target_perp_at_mid = perp_o
            template_perp_at_mid = perp_t
    if template_max_perp < 1e-6:
        return False
    scale_perp = native_max_perp / template_max_perp
    mirror = (template_perp_at_mid >= 0) != (target_perp_at_mid >= 0)

    for k in range(1, span_len - 1):
        tp = template_pts[(offset + k) % tn]
        dx, dy = tp.x - t_start.x, tp.y - t_start.y
        along = ux * dx + uy * dy
        perp = ux * dy - uy * dx
        if mirror:
            perp = -perp
        target_pt = pts[(entry_idx + k) % n]
        target_pt.x = start.x + scale_along * along * tux - scale_perp * perp * tuy
        target_pt.y = start.y + scale_along * along * tuy + scale_perp * perp * tux
    return True


def reshape_arch_counters(glyph, template_contour) -> bool:
    """Reshape every spring-to-spring arch span in `glyph` that
    structurally matches a same-length run of `template_contour`'s own
    points (typically the same master's 'o' outer contour). Returns True
    if at least one span was reshaped."""
    if not glyph.contours or template_contour is None:
        return False
    pts = glyph.contours[0].points
    n = len(pts)
    template_pts = template_contour.points
    template_types = [CC._type_key(p) for p in template_pts]

    reshaped_any = False
    for entry_idx, _entry_adj, exit_idx, _exit_adj in AS.find_spring_pairs(glyph):
        if _reshape_span(pts, n, entry_idx, exit_idx, template_pts, template_types):
            reshaped_any = True
    return reshaped_any


def reshape_named_span(glyph, template_contour, entry_idx: int, exit_idx: int, entry_type: str, exit_type: str) -> bool:
    """Same reshape as `reshape_arch_counters`, for a single span whose
    entry/exit point indices are already known (rather than discovered
    via `arch_symmetry.find_spring_pairs`, which is tuned for a stem
    meeting a curve and doesn't recognize 'e's crossbar-meets-bowl
    shape). `entry_type`/`exit_type` guard against Roboto Flex ever
    reshuffling this glyph's own point order out from under a hardcoded
    index -- the same defensive pattern `quirks.py` already uses for
    its own per-glyph, per-index edits -- so this silently no-ops rather
    than reshaping the wrong points if the outline isn't the shape it
    was written against."""
    if not glyph.contours or template_contour is None:
        return False
    pts = glyph.contours[0].points
    n = len(pts)
    if entry_idx >= n or exit_idx >= n:
        return False
    if CC._type_key(pts[entry_idx]) != entry_type or CC._type_key(pts[exit_idx]) != exit_type:
        return False
    template_pts = template_contour.points
    template_types = [CC._type_key(p) for p in template_pts]
    return _reshape_span(pts, n, entry_idx, exit_idx, template_pts, template_types)
