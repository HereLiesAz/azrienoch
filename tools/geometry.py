"""Multiplex glyph-construction primitives.

Every letterform in Multiplex is assembled from a small set of primitive
shapes (stems, bars, diagonal bands, true circular/elliptical arcs) that
are combined with boolean union/intersection/difference (via
``booleanOperations``, the same engine RoboFont uses). Multiplex is a
conventional, smooth-curved grotesque sans -- the primitive/union
construction is an engineering convenience, not a "blocky" aesthetic:
arcs are real cubic-Bezier approximations of circles/ellipses (standard
4-segment-per-quadrant kappa construction), not faceted polygons.

Terminal rule
--------------
Multiplex never ends a stroke on a cut that follows the stroke's own angle
(no diagonal terminals). Every free stroke end is closed off with either:

* a **horizontal** cut, when the end sits on a guide line (baseline,
  x-height, cap-height, ascender) -- the default case, and
* a **vertical** cut, for free ends that fall away from a guide line
  (arm tips, spurs, ears, hooks) -- used only when a horizontal cut isn't
  available.

``stroke()`` implements this directly via the ``cap0``/``cap1`` arguments;
``clip_flat()`` is the general-purpose guillotine used everywhere else
(diagonal bands, open arcs) to guarantee the same rule.
"""

from __future__ import annotations

import math

import booleanOperations
import ufoLib2

BIG = 100_000


# ---------------------------------------------------------------------------
# low-level shape construction
# ---------------------------------------------------------------------------

def _glyph_from_points(pts):
    g = ufoLib2.objects.Glyph()
    pen = g.getPen()
    pen.moveTo(pts[0])
    for p in pts[1:]:
        pen.lineTo(p)
    pen.closePath()
    return g


def polygon(pts):
    """A single closed polygon primitive from a list of (x, y) points."""
    pts = [(round(x, 2), round(y, 2)) for x, y in pts]
    return _glyph_from_points(pts)


def rect(x0, y0, x1, y1):
    """Axis-aligned rectangle -- the stem/bar primitive."""
    if x0 > x1:
        x0, x1 = x1, x0
    if y0 > y1:
        y0, y1 = y1, y0
    return polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


def empty():
    return ufoLib2.objects.Glyph()


# ---------------------------------------------------------------------------
# boolean combinators
# ---------------------------------------------------------------------------

def _contours(shape):
    return list(shape.contours) if shape is not None else []


def union(shapes):
    """Union a list of primitive shapes into a single glyph."""
    contours = []
    for s in shapes:
        contours.extend(_contours(s))
    out = ufoLib2.objects.Glyph()
    if contours:
        booleanOperations.union(contours, out.getPointPen())
    return out


def subtract(shape, hole):
    out = ufoLib2.objects.Glyph()
    a, b = _contours(shape), _contours(hole)
    if not a:
        return out
    if not b:
        return shape
    booleanOperations.difference(a, b, out.getPointPen())
    return out


def intersect(shape, clip):
    out = ufoLib2.objects.Glyph()
    a, b = _contours(shape), _contours(clip)
    if not a or not b:
        return out
    booleanOperations.intersection(a, b, out.getPointPen())
    return out


def half_plane(direction, coord):
    """A huge rectangle used to guillotine-clip a shape to a flat edge.

    direction in {'above', 'below', 'left', 'right'} names the side of the
    ``coord`` line (a y value for above/below, an x value for left/right)
    that survives the clip.
    """
    if direction == "above":
        return rect(-BIG, coord, BIG, BIG)
    if direction == "below":
        return rect(-BIG, -BIG, BIG, coord)
    if direction == "right":
        return rect(coord, -BIG, BIG, BIG)
    if direction == "left":
        return rect(-BIG, -BIG, coord, BIG)
    raise ValueError(direction)


def clip_flat(shape, direction, coord):
    """Guillotine ``shape`` flat along a horizontal or vertical line.

    This is the one function that enforces the terminal rule everywhere:
    it only ever cuts along a horizontal or vertical line, never along an
    arbitrary angle.
    """
    return intersect(shape, half_plane(direction, coord))


# ---------------------------------------------------------------------------
# straight strokes
# ---------------------------------------------------------------------------

def vstem(cx, y0, y1, w):
    """A vertical stem -- inherently flat-topped and flat-bottomed."""
    return rect(cx - w / 2, y0, cx + w / 2, y1)


def hbar(x0, x1, cy, w):
    """A horizontal bar -- inherently flat-ended (vertical cuts)."""
    return rect(x0, cy - w / 2, x1, cy + w / 2)


def _unit(p0, p1):
    x0, y0 = p0
    x1, y1 = p1
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy)
    return dx / length, dy / length, length


def band(p0, p1, w):
    """A straight stroke from p0 to p1 with perpendicular (butt) caps.

    Used for the interior of a diagonal where both ends are joints that
    will be absorbed into a union with a neighbouring stroke -- the caps
    themselves are never visible in the final silhouette.
    """
    x0, y0 = p0
    x1, y1 = p1
    ux, uy, length = _unit(p0, p1)
    if length == 0:
        return rect(x0 - w / 2, y0 - w / 2, x0 + w / 2, y0 + w / 2)
    nx, ny = -uy, ux
    hw = w / 2
    pts = [
        (x0 + nx * hw, y0 + ny * hw),
        (x1 + nx * hw, y1 + ny * hw),
        (x1 - nx * hw, y1 - ny * hw),
        (x0 - nx * hw, y0 - ny * hw),
    ]
    return polygon(pts)


def stroke(p0, p1, w, cap0="butt", cap1="butt"):
    """A straight stroke (usually diagonal) with controlled end caps.

    cap0/cap1 apply to the p0/p1 end respectively, each one of:

    * ``'butt'``     -- a plain perpendicular cap, meant to be hidden
                        under a union with an adjoining stroke (a joint).
    * ``'flat_h'``   -- a horizontal terminal cut through that endpoint
                        (used when the end sits on a guide line).
    * ``'flat_v'``   -- a vertical terminal cut through that endpoint
                        (used for free ends off the guide lines).
    """
    x0, y0 = p0
    x1, y1 = p1
    ux, uy, length = _unit(p0, p1)
    # Only extend an end that will actually be trimmed by clip_flat --
    # extending a plain 'butt' end pushes it *away* from the other end,
    # which (for a joint meant to sit inside a neighbouring stem/bar) pokes
    # a spike outside that shape's silhouette instead of embedding cleanly.
    e0 = w if cap0 in ("flat_h", "flat_v") else 0
    e1 = w if cap1 in ("flat_h", "flat_v") else 0
    pA = (x0 - ux * e0, y0 - uy * e0)
    pB = (x1 + ux * e1, y1 + uy * e1)
    shape = band(pA, pB, w)
    if cap0 == "flat_h":
        shape = clip_flat(shape, "above" if y1 >= y0 else "below", y0)
    elif cap0 == "flat_v":
        shape = clip_flat(shape, "right" if x1 >= x0 else "left", x0)
    if cap1 == "flat_h":
        shape = clip_flat(shape, "below" if y1 >= y0 else "above", y1)
    elif cap1 == "flat_v":
        shape = clip_flat(shape, "left" if x1 >= x0 else "right", x1)
    return shape


def dominant_axis_cap(p0, p1):
    """Pick the terminal-rule-compliant cap style for a free end at p1.

    Steep (near-vertical) strokes end on a guide line already (flat_h is
    natural there); shallow (near-horizontal) strokes get a vertical cut
    instead, since they rarely land exactly on a guide line.
    """
    x0, y0 = p0
    x1, y1 = p1
    return "flat_h" if abs(y1 - y0) >= abs(x1 - x0) else "flat_v"


# ---------------------------------------------------------------------------
# arcs -- true cubic-Bezier circular/elliptical curves
# ---------------------------------------------------------------------------

def _arc_chunks(a0_deg, a1_deg, max_seg_deg=89.0):
    """Split an angular span into pieces no wider than max_seg_deg."""
    span = a1_deg - a0_deg
    n = max(1, math.ceil(abs(span) / max_seg_deg))
    step = span / n
    return [(a0_deg + i * step, a0_deg + (i + 1) * step) for i in range(n)]


def _cubic_arc_ctrl(cx, cy, rx, ry, a0_deg, a1_deg):
    """Control points for one <=90deg cubic-Bezier circular/elliptical arc."""
    a0 = math.radians(a0_deg)
    a1 = math.radians(a1_deg)
    sin0, cos0 = math.sin(a0), math.cos(a0)
    sin1, cos1 = math.sin(a1), math.cos(a1)
    t = math.tan((a1 - a0) / 2)
    alpha = math.sin(a1 - a0) * (math.sqrt(4 + 3 * t * t) - 1) / 3
    p1 = (cos0 - alpha * sin0, sin0 + alpha * cos0)
    p2 = (cos1 + alpha * sin1, sin1 - alpha * cos1)
    p3 = (cos1, sin1)

    def scale(p):
        return (round(cx + rx * p[0], 2), round(cy + ry * p[1], 2))

    return scale(p1), scale(p2), scale(p3)


def _arc_start_point(cx, cy, rx, ry, a0_deg):
    a0 = math.radians(a0_deg)
    return (round(cx + rx * math.cos(a0), 2), round(cy + ry * math.sin(a0), 2))


def _draw_arc(pen, cx, cy, rx, ry, a0_deg, a1_deg, move_to):
    """Emit cubic curveTo segments for an arc; optionally moveTo the start."""
    if move_to:
        pen.moveTo(_arc_start_point(cx, cy, rx, ry, a0_deg))
    for seg0, seg1 in _arc_chunks(a0_deg, a1_deg):
        c1, c2, end = _cubic_arc_ctrl(cx, cy, rx, ry, seg0, seg1)
        pen.curveTo(c1, c2, end)


def _ellipse_glyph(cx, cy, rx, ry):
    g = ufoLib2.objects.Glyph()
    pen = g.getPen()
    _draw_arc(pen, cx, cy, rx, ry, 0, 360, move_to=True)
    pen.closePath()
    return g


def ellipse_ring(cx, cy, rx, ry, w):
    """A closed ring (annulus) -- e.g. the bowl of 'O'."""
    outer = _ellipse_glyph(cx, cy, rx + w / 2, ry + w / 2)
    inner = _ellipse_glyph(cx, cy, rx - w / 2, ry - w / 2)
    return subtract(outer, inner)


def ellipse_fill(cx, cy, rx, ry):
    """A filled ellipse -- e.g. a dot."""
    return _ellipse_glyph(cx, cy, rx, ry)


def arc_band(cx, cy, rx, ry, w, a0_deg, a1_deg, cut0=None, cut1=None, pad=8):
    """An open arc-shaped stroke from angle a0 to a1 (degrees, CCW positive).

    cut0/cut1 are ``(direction, coord)`` pairs passed to ``clip_flat`` for
    ends that terminate freely (see module docstring); pass ``None`` for
    an end that will be absorbed into a union with another stroke instead.
    The arc itself is a true circular/elliptical curve; only the terminal
    cuts (when present) are straight horizontal/vertical lines.
    """
    ea0 = a0_deg - (pad if cut0 else 0)
    ea1 = a1_deg + (pad if cut1 else 0)
    g = ufoLib2.objects.Glyph()
    pen = g.getPen()
    _draw_arc(pen, cx, cy, rx + w / 2, ry + w / 2, ea0, ea1, move_to=True)
    # Bridge to the inner arc with an explicit line: curveTo control points
    # for the inner arc are computed relative to *its own* start point, so
    # without this the pen's actual position (the outer arc's end) doesn't
    # match and the curve distorts.
    pen.lineTo(_arc_start_point(cx, cy, rx - w / 2, ry - w / 2, ea1))
    _draw_arc(pen, cx, cy, rx - w / 2, ry - w / 2, ea1, ea0, move_to=False)
    pen.closePath()
    if cut0:
        g = clip_flat(g, *cut0)
    if cut1:
        g = clip_flat(g, *cut1)
    return g


# ---------------------------------------------------------------------------
# whole-glyph utilities
# ---------------------------------------------------------------------------

def translate(shape, dx, dy=0):
    g = ufoLib2.objects.Glyph()
    pen = g.getPointPen()
    for contour in shape.contours:
        pen.beginPath()
        for p in contour.points:
            pen.addPoint((p.x + dx, p.y + dy), segmentType=p.type, smooth=p.smooth)
        pen.endPath()
    return g


def bbox(shape):
    xs, ys = [], []
    for c in shape.contours:
        for p in c.points:
            xs.append(p.x)
            ys.append(p.y)
    if not xs:
        return (0, 0, 0, 0)
    return (min(xs), min(ys), max(xs), max(ys))


def append_into(glyph, shape):
    """Append shape's contours into an existing ufoLib2 glyph, in place."""
    pen = glyph.getPointPen()
    for contour in shape.contours:
        pen.beginPath()
        for p in contour.points:
            pen.addPoint((p.x, p.y), segmentType=p.type, smooth=p.smooth)
        pen.endPath()
    return glyph


def radial_cut(cx, cy, r, angle_deg, keep_angle_deg, axis):
    """A ``clip_flat`` (direction, coord) pair that trims the overshoot at
    ``angle_deg`` while keeping the side of the cut that contains the point
    at ``keep_angle_deg`` (an angle safely inside the arc you want to keep).

    axis is ``'h'`` for a horizontal cut (terminal near the vertical
    meridian) or ``'v'`` for a vertical cut (terminal near the horizontal
    meridian) -- matching the terminal rule's horizontal/vertical-only
    choice. Deriving the keep-side from a reference angle, rather than
    reasoning about signs by hand, is what it's for: it's easy to get the
    'above' vs 'below' direction backwards and silently clip away the part
    of the arc you meant to keep.
    """
    x = cx + r * math.cos(math.radians(angle_deg))
    y = cy + r * math.sin(math.radians(angle_deg))
    xm = cx + r * math.cos(math.radians(keep_angle_deg))
    ym = cy + r * math.sin(math.radians(keep_angle_deg))
    if axis == "h":
        return ("above", y) if ym >= y else ("below", y)
    return ("right", x) if xm >= x else ("left", x)


def serif_foot(cx, y, stroke_w, serif_amount, direction=1):
    """A horizontal slab foot, sized by the 0-100 SERF axis value.

    direction=+1 sits above y (a serif hanging from a cap-height/x-height
    guide), direction=-1 sits below y (a foot resting on the baseline).
    Always a rectangle -- serifs obey the same horizontal-terminal rule
    as everything else.
    """
    if serif_amount <= 0:
        return None
    foot_w = stroke_w + serif_amount * (stroke_w * 1.5) / 100.0
    foot_h = max(stroke_w * 0.16, serif_amount * (stroke_w * 0.55) / 100.0)
    if direction > 0:
        y0, y1 = y, y + foot_h
    else:
        y0, y1 = y - foot_h, y
    return rect(cx - foot_w / 2, y0, cx + foot_w / 2, y1)
