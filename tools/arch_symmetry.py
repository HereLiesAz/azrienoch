"""Symmetrize the counter-facing curve of arch letters ('n'/'h'/'m') and
bowl letters built the same way in reverse ('u'): Roboto Flex springs
that curve from each stem at two different heights -- e.g. 'n's left
stem meets its arch at y=693, the right stem at y=608.7, an 84-unit
difference -- which reads as a lopsided negative space even though the
letter's outer silhouette is close to symmetric. Confirmed in the raw
point data, not an illusion, and present with none of Azrienoch's other
changes anywhere near it.

``find_spring_pairs`` locates each such pair generically: a spring is
where a long, genuinely vertical straight run (a real stem, the same
length check `serifs.py`/`round_contrast.py` use) meets a curve, exactly
like `round_contrast.find_neck_point` -- but a letter can have more than
one (both arches of 'm'), and not every spring belongs to the counter:
'h' also has one where its ascender's *outer* silhouette curves over the
top, which isn't a counter boundary and shouldn't be touched. Springs
are paired by contour order (an entry spring immediately followed, with
only curve points between, by an exit spring) and then sanity-checked --
a real counter's two springs are close in height (the ~84-unit
asymmetry this is fixing, not the ~250-unit gap between an arch's inner
spring and its ascender's unrelated outer one).

``symmetrize`` moves each spring to the pair's average height, together
with the one off-curve control point immediately adjacent to it on the
curve side (translated by the same amount, so the curve's local shape
near the spring is preserved rather than kinked) -- leaving the curve's
far control point and the peak/trough between the two springs untouched.
Only ever moves existing points, so topology is unaffected.
"""

from __future__ import annotations

MIN_STEM_LEN = 300.0  # units; matches serifs.py's/round_contrast.py's own real-stem threshold
MAX_SPRING_DIFF = 200.0  # units; a real counter's two springs differ by far less than this


def find_spring_pairs(glyph):
    """List of (entry_index, entry_adjacent_index, exit_index,
    exit_adjacent_index) for each valid counter-spring pair in
    `glyph`'s first contour."""
    if not glyph.contours:
        return []
    pts = glyph.contours[0].points
    n = len(pts)
    events = []
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        if b.type != "line":
            continue
        if abs(a.x - b.x) >= 1.0 or abs(a.y - b.y) < MIN_STEM_LEN:
            continue
        after_b = pts[(i + 2) % n]
        before_a = pts[(i - 1) % n]
        if after_b.type is None:
            events.append(((i + 1) % n, "entry", (i + 2) % n))
        if before_a.type is None:
            events.append((i, "exit", (i - 1) % n))
    events.sort(key=lambda e: e[0])

    pairs = []
    pending = None
    for idx, kind, adj_idx in events:
        if kind == "entry":
            pending = (idx, adj_idx)
        elif kind == "exit" and pending is not None:
            entry_idx, entry_adj = pending
            if abs(pts[entry_idx].y - pts[idx].y) <= MAX_SPRING_DIFF:
                pairs.append((entry_idx, entry_adj, idx, adj_idx))
            pending = None
    return pairs


def symmetrize(glyph) -> None:
    if not glyph.contours:
        return
    pts = glyph.contours[0].points
    for entry_idx, entry_adj, exit_idx, exit_adj in find_spring_pairs(glyph):
        target = (pts[entry_idx].y + pts[exit_idx].y) / 2.0
        entry_dy = target - pts[entry_idx].y
        exit_dy = target - pts[exit_idx].y
        pts[entry_idx].y += entry_dy
        pts[entry_adj].y += entry_dy
        pts[exit_idx].y += exit_dy
        pts[exit_adj].y += exit_dy
