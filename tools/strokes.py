"""Procedural strokes: turn centerline paths into closed outline contours.

Used for glyphs that have no donor outline (logic symbols, the hook-above and
horn marks). A path is a list of cubic segments `(p0, p1, p2, p3)`; a straight
line is a cubic whose controls sit on its thirds. Every function is purely
structural: the number and kind of segments in the result depend on the input
path's structure, never on its coordinates, so the same glyph built at every
master is interpolation-compatible.

Winding: outer contours are clockwise (TrueType), counters counter-clockwise.
Offsetting is Tiller-Hanson (offset the control polygon, intersect neighbours)
with mitered corners, which is exact for lines and close for the gentle arcs
used here.
"""

from __future__ import annotations

import math

Pt = tuple[float, float]
Seg = tuple[Pt, Pt, Pt, Pt]

KAPPA = 0.5522847498307936


def line(p: Pt, q: Pt) -> Seg:
    return (p, _lerp(p, q, 1 / 3), _lerp(p, q, 2 / 3), q)


def polyline(*pts: Pt, closed: bool = False) -> list[Seg]:
    pts = list(pts) + ([pts[0]] if closed else [])
    return [line(a, b) for a, b in zip(pts, pts[1:])]


def arc(cx: float, cy: float, r: float, a0: float, a1: float, ry: float | None = None) -> list[Seg]:
    """Elliptical arc from angle a0 to a1 (degrees, counter-clockwise positive),
    in as many quarter-or-less cubics as needed (at least one per 90 degrees)."""
    ry = r if ry is None else ry
    n = max(1, math.ceil(abs(a1 - a0) / 90.0 - 1e-9))
    out = []
    for i in range(n):
        t0 = math.radians(a0 + (a1 - a0) * i / n)
        t1 = math.radians(a0 + (a1 - a0) * (i + 1) / n)
        k = 4 / 3 * math.tan((t1 - t0) / 4)
        p0 = (cx + r * math.cos(t0), cy + ry * math.sin(t0))
        p3 = (cx + r * math.cos(t1), cy + ry * math.sin(t1))
        p1 = (p0[0] - k * r * math.sin(t0), p0[1] + k * ry * math.cos(t0))
        p2 = (p3[0] + k * r * math.sin(t1), p3[1] - k * ry * math.cos(t1))
        out.append((p0, p1, p2, p3))
    return out


def join(*parts: list[Seg]) -> list[Seg]:
    return [s for part in parts for s in part]


def reverse(path: list[Seg]) -> list[Seg]:
    return [(s[3], s[2], s[1], s[0]) for s in reversed(path)]


def _lerp(a: Pt, b: Pt, t: float) -> Pt:
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def _norm(v: Pt) -> Pt:
    n = math.hypot(*v)
    return (v[0] / n, v[1] / n) if n > 1e-9 else (0.0, 0.0)


def _left(v: Pt) -> Pt:
    return (-v[1], v[0])


def _isect(p: Pt, d: Pt, q: Pt, e: Pt) -> Pt | None:
    den = d[0] * e[1] - d[1] * e[0]
    if abs(den) < 1e-6:
        return None
    t = ((q[0] - p[0]) * e[1] - (q[1] - p[1]) * e[0]) / den
    return (p[0] + d[0] * t, p[1] + d[1] * t)


def _is_line(s: Seg) -> bool:
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = s
    dx, dy = x3 - x0, y3 - y0
    n = math.hypot(dx, dy) or 1.0
    return abs((x1 - x0) * dy - (y1 - y0) * dx) / n < 1e-6 and abs((x2 - x0) * dy - (y2 - y0) * dx) / n < 1e-6


def _tangents(s: Seg) -> tuple[Pt, Pt]:
    p0, p1, p2, p3 = s
    a = _norm((p1[0] - p0[0], p1[1] - p0[1]))
    if a == (0.0, 0.0):
        a = _norm((p2[0] - p0[0], p2[1] - p0[1]))
    b = _norm((p3[0] - p2[0], p3[1] - p2[1]))
    if b == (0.0, 0.0):
        b = _norm((p3[0] - p1[0], p3[1] - p1[1]))
    return a, b


def _offset_seg(s: Seg, d: float) -> Seg:
    """Tiller-Hanson offset of one cubic by `d` to its left."""
    p0, p1, p2, p3 = s
    if _is_line(s):
        t = _norm((p3[0] - p0[0], p3[1] - p0[1]))
        n = _left(t)
        o = (n[0] * d, n[1] * d)
        a = (p0[0] + o[0], p0[1] + o[1])
        b = (p3[0] + o[0], p3[1] + o[1])
        return line(a, b)
    ta, tb = _tangents(s)
    pts = [p0, p1, p2, p3]
    edges = []
    for i in range(3):
        e = _norm((pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]))
        if e == (0.0, 0.0):
            e = ta if i == 0 else tb
        n = _left(e)
        edges.append(((pts[i][0] + n[0] * d, pts[i][1] + n[1] * d), e))
    q0 = edges[0][0]
    n3 = _left(tb)
    q3 = (p3[0] + n3[0] * d, p3[1] + n3[1] * d)
    q1 = _isect(*edges[0], *edges[1]) or (edges[0][0][0] + edges[0][1][0] * 0, edges[0][0][1])
    q2 = _isect(*edges[1], *edges[2]) or q3
    # Keep the controls on the correct side of their endpoints.
    if (q1[0] - q0[0]) * ta[0] + (q1[1] - q0[1]) * ta[1] < 0:
        q1 = (q0[0] + ta[0] * 1e-3, q0[1] + ta[1] * 1e-3)
    if (q3[0] - q2[0]) * tb[0] + (q3[1] - q2[1]) * tb[1] < 0:
        q2 = (q3[0] - tb[0] * 1e-3, q3[1] - tb[1] * 1e-3)
    return (q0, q1, q2, q3)


def offset(path: list[Seg], d: float, closed: bool = False) -> list[Seg]:
    """Offset a path to its left by `d`, mitering corners."""
    segs = [_offset_seg(s, d) for s in path]
    n = len(path)
    pairs = range(n) if closed else range(n - 1)
    for i in pairs:
        j = (i + 1) % n
        _, tend = _tangents(path[i])
        tstart, _ = _tangents(path[j])
        if abs(tend[0] * tstart[1] - tend[1] * tstart[0]) < 1e-4 and tend[0] * tstart[0] + tend[1] * tstart[1] > 0:
            continue
        m = _isect(segs[i][3], tend, segs[j][0], tstart)
        if m is None:
            continue
        # Cap runaway miters on very sharp turns.
        c = path[i][3]
        if math.hypot(m[0] - c[0], m[1] - c[1]) > 4.0 * abs(d) + 1e-6:
            f = 4.0 * abs(d) / math.hypot(m[0] - c[0], m[1] - c[1])
            m = (c[0] + (m[0] - c[0]) * f, c[1] + (m[1] - c[1]) * f)
        segs[i] = _set_end(segs[i], m)
        segs[j] = _set_start(segs[j], m)
    return segs


def _set_end(s: Seg, p: Pt) -> Seg:
    if _is_line(s):
        return line(s[0], p)
    return (s[0], s[1], (s[2][0] + p[0] - s[3][0], s[2][1] + p[1] - s[3][1]), p)


def _set_start(s: Seg, p: Pt) -> Seg:
    if _is_line(s):
        return line(p, s[3])
    return (p, (s[1][0] + p[0] - s[0][0], s[1][1] + p[1] - s[0][1]), s[2], s[3])


def _cap(end: Pt, tangent: Pt, w: float, kind: str, a: Pt, b: Pt) -> list[Seg]:
    """Segments from `a` (left of the end) around the end to `b` (right)."""
    if kind == "butt":
        return [line(a, b)]
    h = w / 2.0
    if kind == "square":
        ext = (tangent[0] * h, tangent[1] * h)
        a2 = (a[0] + ext[0], a[1] + ext[1])
        b2 = (b[0] + ext[0], b[1] + ext[1])
        return [line(a, a2), line(a2, b2), line(b2, b)]
    # round: two quarter arcs around the end point
    k = KAPPA * h
    tip = (end[0] + tangent[0] * h, end[1] + tangent[1] * h)
    n = _left(tangent)
    s1 = (a, (a[0] + tangent[0] * k, a[1] + tangent[1] * k),
          (tip[0] + n[0] * k, tip[1] + n[1] * k), tip)
    s2 = (tip, (tip[0] - n[0] * k, tip[1] - n[1] * k),
          (b[0] + tangent[0] * k, b[1] + tangent[1] * k), b)
    return [s1, s2]


def stroke(path: list[Seg], width: float, cap: str = "butt") -> list[list[Seg]]:
    """Outline of an open path: one clockwise contour."""
    h = width / 2.0
    left = offset(path, h)
    right = reverse(offset(path, -h))
    ta, _ = _tangents(path[0])
    _, tb = _tangents(path[-1])
    end_cap = _cap(path[-1][3], tb, width, cap, left[-1][3], right[0][0])
    start_cap = _cap(path[0][0], (-ta[0], -ta[1]), width, cap, right[-1][3], left[0][0])
    return [_orient(left + end_cap + right + start_cap)]


def ring(path: list[Seg], width: float) -> list[list[Seg]]:
    """Outline of a closed path: a clockwise outer contour plus a
    counter-clockwise counter. `path` must run clockwise."""
    h = width / 2.0
    outer = offset(path, h, closed=True)
    inner = reverse(offset(path, -h, closed=True))
    return [outer, inner]


def _area(contour: list[Seg]) -> float:
    a = 0.0
    for s in contour:
        pts = [s[0], s[1], s[2], s[3]]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            a += x0 * y1 - x1 * y0
    return a / 2.0


def _orient(contour: list[Seg]) -> list[Seg]:
    """Clockwise outer contour (negative signed area)."""
    return reverse(contour) if _area(contour) > 0 else contour


def fill(path: list[Seg]) -> list[list[Seg]]:
    """A filled closed path, as a clockwise contour."""
    return [_orient(path)]


# Whether the font's outer contours run clockwise (set per build from a real
# glyph; see `non_jost.build`). Contours here are built clockwise.
CLOCKWISE_OUTER = True


def draw(pen, contours: list[list[Seg]]) -> None:
    """Replay contours into a glyph pen as lineTo/curveTo. The last segment is
    closed onto the first point exactly, so a contour never gains or loses a
    duplicate end point from floating-point noise."""
    for c in contours:
        if not CLOCKWISE_OUTER:
            c = reverse(c)
        start = c[0][0]
        pen.moveTo(start)
        for i, s in enumerate(c):
            last = i == len(c) - 1
            if _is_line(s):
                if not last:
                    pen.lineTo(s[3])
            else:
                pen.curveTo(s[1], s[2], start if last else s[3])
        pen.closePath()
