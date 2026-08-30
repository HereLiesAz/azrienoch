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


def _horizontal_terminal_e(glyph) -> None:
    """Cut 'e's lower-right opening flat instead of on a diagonal.
    Roboto Flex's own 'e' ends the bottom curve at an on-curve point
    (index 6) and connects it with a straight 'line' segment directly to
    the point starting the curve back into the counter (index 7) -- but
    unlike 'c's matching opening (which steps in, across, and back out,
    always vertically/horizontally), this segment is a genuine diagonal,
    growing sharply with weight (about 92 units of vertical drop over its
    length at Regular, over 200 at Black). Since there's no third point
    here to build 'c's step with, the minimal topology-safe fix is
    moving point 7 to point 6's own height -- point 6 stays exactly where
    Roboto Flex's outer curve already lands, only the cut's angle
    changes.
    """
    if not glyph.contours:
        return
    pts = glyph.contours[0].points
    if len(pts) < 8 or pts[6].type != "qcurve" or pts[7].type != "line":
        return  # not the outline shape this was written against
    pts[7].y = pts[6].y


def _horizontal_terminal_g(glyph) -> None:
    """Cut 'g's descender-loop tail flat instead of on a diagonal, the
    same defect as 'e's (see `_horizontal_terminal_e`) at the open end
    of the hook: Roboto Flex connects the tail curve's landing point
    (index 30) to the loop's own start (index 0) with a straight 'line'
    that grows from a subtle diagonal at Thin to a steep ~300-unit drop
    at Black. Point 30 stays where the outer tail curve already lands;
    point 0 moves up to match its height, leaving the loop's own return
    curve (from point 0 onward) shifted but not reshaped.
    """
    if not glyph.contours:
        return
    pts = glyph.contours[0].points
    if len(pts) != 31 or pts[30].type != "qcurve" or pts[0].type != "line":
        return  # not the outline shape this was written against
    pts[0].y = pts[30].y


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


_QUIRKS = {
    "G": _spur_G,
    "R": _kick_R,
    "e": _horizontal_terminal_e,
    "g": _horizontal_terminal_g,
    "v": _sharpen_baseline_notches,
    "w": _sharpen_baseline_notches,
}
