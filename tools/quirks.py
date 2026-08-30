"""Small, deliberately barely-noticeable Akzidenz-Grotesk-style idiosyncrasies.

Roboto Flex's letterforms are rational and even-tempered almost to a fault
-- exactly the "modern sensibilities" this project wants, but on their own
they read as neutral rather than *analytical* in the Helvetica/Akzidenz
sense. This module makes a handful of small, targeted edits to specific
glyphs, on top of the imported outline, to give the design a little more
character without redrawing anything: a proper spur on 'G', a slightly
kicked leg on 'R'.

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


_QUIRKS = {
    "G": _spur_G,
    "R": _kick_R,
}
