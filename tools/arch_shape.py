"""Give an arch letter's counter-facing curve ('n'/'h'/'m'/'u') the same
round character as the closed counters in 'o'/'d'/'b'/'p'/'q'/'g'/'a' --
extending `canonical_counter.py`'s "reuse 'o's own outer contour as the
reference shape" idea to an open arch instead of a closed loop.

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
"""

from __future__ import annotations

import math

from tools import arch_symmetry as AS
from tools import canonical_counter as CC


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
    tn = len(template_pts)
    template_types = [CC._type_key(p) for p in template_pts]

    reshaped_any = False
    for entry_idx, _entry_adj, exit_idx, _exit_adj in AS.find_spring_pairs(glyph):
        span = exit_idx - entry_idx if exit_idx > entry_idx else (n - entry_idx + exit_idx)
        span_len = span + 1
        if span_len < 3 or span_len > tn:
            continue
        target_types = [CC._type_key(pts[(entry_idx + k) % n]) for k in range(span_len)]
        offset = None
        for o in range(tn):
            if all(target_types[k] == template_types[(o + k) % tn] for k in range(span_len)):
                offset = o
                break
        if offset is None:
            continue

        start = pts[entry_idx]
        end = pts[exit_idx]
        t_start = template_pts[offset]
        t_end = template_pts[(offset + span_len - 1) % tn]
        vt = (t_end.x - t_start.x, t_end.y - t_start.y)
        vt_len = math.hypot(*vt)
        vtar = (end.x - start.x, end.y - start.y)
        vtar_len = math.hypot(*vtar)
        if vt_len < 1e-6 or vtar_len < 1e-6:
            continue
        ux, uy = vt[0] / vt_len, vt[1] / vt_len  # template chord unit vector
        tux, tuy = vtar[0] / vtar_len, vtar[1] / vtar_len  # target chord unit vector
        scale = vtar_len / vt_len

        mid_k = span_len // 2
        mid_t = template_pts[(offset + mid_k) % tn]
        dxt, dyt = mid_t.x - t_start.x, mid_t.y - t_start.y
        template_perp = ux * dyt - uy * dxt
        mid_orig = pts[(entry_idx + mid_k) % n]
        dxo, dyo = mid_orig.x - start.x, mid_orig.y - start.y
        target_perp = tux * dyo - tuy * dxo
        mirror = (template_perp >= 0) != (target_perp >= 0)

        for k in range(1, span_len - 1):
            tp = template_pts[(offset + k) % tn]
            dx, dy = tp.x - t_start.x, tp.y - t_start.y
            along = ux * dx + uy * dy
            perp = ux * dy - uy * dx
            if mirror:
                perp = -perp
            target_pt = pts[(entry_idx + k) % n]
            target_pt.x = start.x + scale * (along * tux - perp * tuy)
            target_pt.y = start.y + scale * (along * tuy + perp * tux)
        reshaped_any = True
    return reshaped_any
