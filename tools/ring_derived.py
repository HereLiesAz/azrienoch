"""Builds 'c' and 'e' directly from 'o's own outer+inner ring outline,
so their bowl/counter proportions are literally 'o's, at every weight,
width and serif setting.

Construction (per master)
-------------------------
Three horizontal levels, all read off Jost's own 'e' at the same
(wght, wdth, grad) by `e_levels` -- so they track the donor's own
weight/width behaviour rather than a guessed ratio:

- `bar_top` / `bar_bottom`: Jost's own 'e' crossbar edges.
- `terminal`: the vertical midpoint of Jost's own (diagonal) 'e'
  lower-terminal cut.

'e' is 'o's ring with:

- an upper bowl: 'o's inner ring above `bar_top`, closed by a straight
  line at `bar_top` -- a separately-wound hole;
- a crossbar from `bar_top` down to `bar_bottom`, running straight out
  to the ring's own outer edge on the right. The outer ring stops
  curving exactly at `bar_bottom` on the right side;
- an aperture on the lower right, between `bar_bottom` and a
  horizontal lower terminal at `terminal`.

'c' shares those levels by construction (per the project owner's
direction): its upper terminal sits level with 'e's `bar_bottom` (where
'e's own bowl stops curving), its lower terminal level with 'e's own
lower terminal. Both of 'c's terminals, and both of 'e's horizontal
edges at the aperture, are exactly horizontal by construction -- no
post-hoc `quirks.py` reorientation. (The previous approach cut the
ring at fixed ANGLES, then rotated the cuts flat via hardcoded point
indices; 'e' rendered with no visible crossbar and a broken aperture
at every weight.)

Topology
--------
Every arc is emitted as a FIXED number of quadratic segments
(`_ARC_SEGMENTS`), each one a tangent-matched quadratic between two
points sampled on 'o's actual ring at evenly spaced angles from the
ring's own center. Point count is therefore identical at every master
regardless of where a cut lands on 'o's own Bezier chain -- the
invariant fontmake needs to compile the variable font at all. With 'o's
ring this close to an ellipse, a quadratic per <= ~30 degrees tracks it
to well under a unit.

's' stays Arimo-sourced (`arimo_source.py`): an S-curve has no ring to
derive from 'o' at all.
"""

from __future__ import annotations

import math

import ufoLib2
from fontTools.pens.recordingPen import RecordingPen

from . import jost_source

# Quadratic segments per arc, by role. Fixed -> identical topology at
# every master. Long outer/inner sweeps (~300 degrees) get the most.
_ARC_SEGMENTS = {
    "outer_long": 12,
    "inner_long": 10,
    "hole": 8,
}

_SAMPLES_PER_SEGMENT = 48  # dense sampling of 'o's own Bezier chain


# ---------------------------------------------------------------------------
# Ring sampling
# ---------------------------------------------------------------------------

def _quad_segments(contour):
    """'o's TrueType-quadratic contour as a list of (p0, c, p1)
    quadratics, expanding implied on-curve points between consecutive
    off-curves."""
    pts = [(p.x, p.y, p.type) for p in contour.points]
    n = len(pts)
    start = next(i for i, p in enumerate(pts) if p[2] is not None)
    pts = pts[start:] + pts[:start]
    segs = []
    cur = (pts[0][0], pts[0][1])
    offs = []
    for x, y, t in pts[1:] + [pts[0]]:
        if t is None:
            if offs:
                mid = ((offs[-1][0] + x) / 2.0, (offs[-1][1] + y) / 2.0)
                segs.append((cur, offs[-1], mid))
                cur = mid
                offs = [(x, y)]
            else:
                offs.append((x, y))
        else:
            if offs:
                segs.append((cur, offs[-1], (x, y)))
                offs = []
            else:
                segs.append((cur, ((cur[0] + x) / 2.0, (cur[1] + y) / 2.0), (x, y)))
            cur = (x, y)
    return segs


class _Ring:
    """A convex closed ring ('o's outer or inner contour), queryable by
    angle from its own bounding-box center."""

    def __init__(self, contour):
        samples = []
        for p0, c, p1 in _quad_segments(contour):
            for k in range(_SAMPLES_PER_SEGMENT):
                t = k / _SAMPLES_PER_SEGMENT
                a = (p0[0] + (c[0] - p0[0]) * t, p0[1] + (c[1] - p0[1]) * t)
                b = (c[0] + (p1[0] - c[0]) * t, c[1] + (p1[1] - c[1]) * t)
                samples.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
        xs = [p[0] for p in samples]
        ys = [p[1] for p in samples]
        self.cx = (min(xs) + max(xs)) / 2.0
        self.cy = (min(ys) + max(ys)) / 2.0
        self.top = max(ys)
        self.bottom = min(ys)
        tagged = sorted((math.atan2(y - self.cy, x - self.cx), (x, y)) for x, y in samples)
        self._angles = [a for a, _ in tagged]
        self._points = [p for _, p in tagged]

    def at(self, theta: float):
        """Point on the ring at angle `theta` (radians, any range),
        linearly interpolated between the two nearest dense samples."""
        theta = math.atan2(math.sin(theta), math.cos(theta))
        angs, pts = self._angles, self._points
        n = len(angs)
        lo, hi = 0, n
        while lo < hi:
            mid = (lo + hi) // 2
            if angs[mid] < theta:
                lo = mid + 1
            else:
                hi = mid
        i1 = lo % n
        i0 = (lo - 1) % n
        a0, a1 = angs[i0], angs[i1]
        span = (a1 - a0) % (2 * math.pi) or 1e-12
        f = ((theta - a0) % (2 * math.pi)) / span
        p0, p1 = pts[i0], pts[i1]
        return (p0[0] + (p1[0] - p0[0]) * f, p0[1] + (p1[1] - p0[1]) * f)

    def tangent(self, theta: float, h: float = 1e-3):
        a = self.at(theta - h)
        b = self.at(theta + h)
        return (b[0] - a[0], b[1] - a[1])

    def angle_at_y(self, y: float, side: str, lower: bool):
        """Angle of the ring point at height `y` on the given `side`
        ("right" or "left"), in the given half ("lower" or upper).
        Bisection: y is monotonic in angle on each quarter of a convex
        ring."""
        if side == "right":
            lo, hi = (-math.pi / 2, 0.0) if lower else (0.0, math.pi / 2)
        else:
            lo, hi = (math.pi, 1.5 * math.pi) if lower else (math.pi / 2, math.pi)
        y_lo = self.at(lo)[1]
        increasing = self.at(hi)[1] > y_lo
        for _ in range(80):
            mid = (lo + hi) / 2.0
            ym = self.at(mid)[1]
            if (ym < y) == increasing:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2.0


def _line_intersect(p, d, q, e):
    """Intersection of lines p + s*d and q + u*e, or None if parallel."""
    den = d[0] * e[1] - d[1] * e[0]
    if abs(den) < 1e-9:
        return None
    s = ((q[0] - p[0]) * e[1] - (q[1] - p[1]) * e[0]) / den
    return (p[0] + s * d[0], p[1] + s * d[1])


def _arc(ring: _Ring, theta0: float, theta1: float, segments: int):
    """`segments` tangent-matched quadratics tracing `ring` from angle
    `theta0` to `theta1` (either direction, the way given). Returns
    [(ctrl, end), ...] -- the start point itself is the caller's."""
    out = []
    prev_t = theta0
    prev_p = ring.at(theta0)
    for k in range(1, segments + 1):
        t = theta0 + (theta1 - theta0) * k / segments
        p = ring.at(t)
        c = _line_intersect(prev_p, ring.tangent(prev_t), p, ring.tangent(t))
        mid = ((prev_p[0] + p[0]) / 2.0, (prev_p[1] + p[1]) / 2.0)
        if c is None or math.hypot(c[0] - mid[0], c[1] - mid[1]) > math.hypot(p[0] - prev_p[0], p[1] - prev_p[1]):
            c = mid  # degenerate tangent pair; never hit on a real ring
        out.append((c, p))
        prev_t, prev_p = t, p
    return out


# ---------------------------------------------------------------------------
# Contour emission
# ---------------------------------------------------------------------------

def _emit(pen, start, pieces):
    """pieces: list of ("line", pt) / ("arc", [(ctrl, end), ...])."""
    pen.moveTo(start)
    for kind, data in pieces:
        if kind == "line":
            pen.lineTo(data)
        else:
            for c, p in data:
                pen.qCurveTo(c, p)
    pen.closePath()


def _signed_area_poly(pts):
    total = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        total += x1 * y2 - x2 * y1
    return total / 2.0


def _outer_inner(o_glyph):
    def area(c):
        xs = [p.x for p in c.points]
        ys = [p.y for p in c.points]
        return (max(xs) - min(xs)) * (max(ys) - min(ys))
    contours = sorted(o_glyph.contours, key=area, reverse=True)
    return contours[0], contours[1]


def _o_outer_is_ccw(o_glyph) -> bool:
    outer, _ = _outer_inner(o_glyph)
    return _signed_area_poly([(p.x, p.y) for p in outer.points]) > 0


def _new_glyph(name: str, width: float) -> ufoLib2.objects.Glyph:
    glyph = ufoLib2.objects.Glyph(name=name)
    glyph.unicodes = [ord(name)]
    glyph.width = width
    return glyph


def _reverse_recording(value):
    """Reverses every contour in a RecordingPen value (winding flip)."""
    from fontTools.pens.reverseContourPen import ReverseContourPen
    out = RecordingPen()
    rev = ReverseContourPen(out)
    for cmd, args in value:
        getattr(rev, cmd)(*args)
    return out.value


def _finish(name, width, ccw_contours, outer_ccw: bool):
    """`ccw_contours`: RecordingPen values, filled contours CCW, holes
    CW. Flipped wholesale if 'o's own outer contour runs the other way,
    so 'c'/'e' share 'o's winding convention."""
    glyph = _new_glyph(name, width)
    pen = glyph.getPen()
    for value in ccw_contours:
        if not outer_ccw:
            value = _reverse_recording(value)
        for cmd, args in value:
            getattr(pen, cmd)(*args)
    return glyph


# ---------------------------------------------------------------------------
# Levels
# ---------------------------------------------------------------------------

# Point indices on Jost's own 'e' (single 42-point contour), confirmed
# identical at wght 100/400/900 x wdth 75/100: 3/4 = lower-terminal
# cut (outer, inner); 23/24 = crossbar top edge; 25/26 = crossbar
# bottom edge.
_JOST_E_TERMINAL = (3, 4)
_JOST_E_BAR_TOP = (23, 24)
_JOST_E_BAR_BOTTOM = (25, 26)


def e_levels(wght: float, wdth: float, grad: float = 0) -> dict[str, float]:
    """{bar_top, bar_bottom, terminal} y-levels, read off Jost's own 'e'
    at this exact axis location (see module docstring)."""
    name = jost_source.glyph_names_for_chars("e")["e"]
    pen_value, _ = jost_source.extract(name, wght, wdth, grad)
    glyph = ufoLib2.objects.Glyph(name="e")
    jost_source.replay(glyph.getPen(), pen_value)
    pts = glyph.contours[0].points
    on = {i: p for i, p in enumerate(pts)}
    def mean_y(pair):
        return (on[pair[0]].y + on[pair[1]].y) / 2.0
    return {
        "bar_top": mean_y(_JOST_E_BAR_TOP),
        "bar_bottom": mean_y(_JOST_E_BAR_BOTTOM),
        "terminal": mean_y(_JOST_E_TERMINAL),
    }


def _clamp_levels(levels, outer: _Ring, inner: _Ring):
    """Keeps every level strictly inside 'o's own counter (a cut must
    hit both rings, and the upper bowl must stay open), with a margin
    of 10% of the counter's height."""
    margin = 0.10 * (inner.top - inner.bottom)
    lo, hi = inner.bottom + margin, inner.top - margin
    term = min(max(levels["terminal"], lo), hi)
    bar_b = min(max(levels["bar_bottom"], term + margin), hi)
    bar_t = min(max(levels["bar_top"], bar_b + 1.0), hi)
    return bar_t, bar_b, term


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def build_c_from_o(o_glyph, levels: dict[str, float]):
    """'c': 'o's ring opened on the right, from `levels["bar_bottom"]`
    (upper terminal) down to `levels["terminal"]` (lower terminal) --
    both exactly horizontal."""
    outer_c, inner_c = _outer_inner(o_glyph)
    outer, inner = _Ring(outer_c), _Ring(inner_c)
    _, y_top, y_bot = _clamp_levels(levels, outer, inner)

    o_top = outer.angle_at_y(y_top, "right", lower=y_top < outer.cy)
    o_bot = outer.angle_at_y(y_bot, "right", lower=True) + 2 * math.pi
    i_top = inner.angle_at_y(y_top, "right", lower=y_top < inner.cy)
    i_bot = inner.angle_at_y(y_bot, "right", lower=True) + 2 * math.pi

    rec = RecordingPen()
    _emit(rec, outer.at(o_top), [
        ("arc", _arc(outer, o_top, o_bot, _ARC_SEGMENTS["outer_long"])),
        ("line", inner.at(i_bot)),
        ("arc", _arc(inner, i_bot, i_top, _ARC_SEGMENTS["inner_long"])),
    ])
    return _finish("c", o_glyph.width, [rec.value], _o_outer_is_ccw(o_glyph))


def build_e_from_o(o_glyph, levels: dict[str, float]):
    """'e': 'o's ring, upper bowl closed at `bar_top`, crossbar running
    out to the outer edge on the right down to `bar_bottom` (where the
    outer ring stops curving), aperture from there down to a horizontal
    lower terminal at `terminal`."""
    outer_c, inner_c = _outer_inner(o_glyph)
    outer, inner = _Ring(outer_c), _Ring(inner_c)
    y_bar_t, y_bar_b, y_term = _clamp_levels(levels, outer, inner)

    # Outer contour (CCW): outer ring from the bar bottom on the right,
    # up and around to the lower terminal; in to the inner ring; back
    # along the inner ring (CW) to the bar bottom on the LEFT; straight
    # across the bar's bottom edge to the start.
    o_bar = outer.angle_at_y(y_bar_b, "right", lower=y_bar_b < outer.cy)
    o_term = outer.angle_at_y(y_term, "right", lower=True) + 2 * math.pi
    i_term = inner.angle_at_y(y_term, "right", lower=True) + 2 * math.pi
    i_bar_left = inner.angle_at_y(y_bar_b, "left", lower=y_bar_b < inner.cy)
    if i_bar_left < 0:
        i_bar_left += 2 * math.pi

    outer_rec = RecordingPen()
    _emit(outer_rec, outer.at(o_bar), [
        ("arc", _arc(outer, o_bar, o_term, _ARC_SEGMENTS["outer_long"])),
        ("line", inner.at(i_term)),
        ("arc", _arc(inner, i_term, i_bar_left, _ARC_SEGMENTS["inner_long"])),
    ])

    # Upper bowl hole (CW): inner ring above the bar top, left to right
    # over the top, closed by the bar's top edge.
    h_left = inner.angle_at_y(y_bar_t, "left", lower=y_bar_t < inner.cy)
    if h_left < 0:
        h_left += 2 * math.pi
    h_right = inner.angle_at_y(y_bar_t, "right", lower=y_bar_t < inner.cy)
    hole_rec = RecordingPen()
    _emit(hole_rec, inner.at(h_left), [
        ("arc", _arc(inner, h_left, h_right, _ARC_SEGMENTS["hole"])),
    ])

    return _finish("e", o_glyph.width, [outer_rec.value, hole_rec.value], _o_outer_is_ccw(o_glyph))
