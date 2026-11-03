"""Uniform stroke thickness for the straight-stroke letters V/W/M/v/w.

Jost draws these with deliberately unequal strokes (Futura's
convention): 'W'/'w's two inner diagonals are thinner than its outer
ones, 'M's diagonals don't match its stems, and the imbalance grows
with weight -- and `condense.py`'s X-only compression changes each
diagonal's perpendicular thickness by a different amount depending on
its slope, so the mismatch is worse again at `wdth`=75. Per the project
owner's direction, every stroke of these letters gets ONE perpendicular
thickness.

Method, per master, on the already-extracted (and already-condensed)
glyph:

- The glyph's OUTER silhouette points stay exactly where Jost put them
  (top corners, bottom vertices, apexes) -- advance width, sidebearings
  and therefore kerning are unchanged.
- The target thickness `T` is the glyph's own first outer stroke
  (V/v/W/w's leftmost diagonal, M's left stem), measured
  perpendicularly at its midpoint.
- Every other stroke's inner edge is rebuilt parallel to its outer
  edge at exactly `T`, and every inner point is recomputed as the
  intersection of the rebuilt edges. 'W'/'w's middle strokes have no
  single outer edge (their apex sits on one edge, their bottom vertex
  on the other), so each is solved as a parallel strip of width `T`
  that has the apex on one boundary and the bottom vertex on the other.

'M' additionally gets the overshoot every other pointed letter here
has (per the project owner's direction): Jost's 'M' is the one letter
whose pointed middle vertex stops short -- above the baseline -- while
'V'/'W'/'v'/'w''s vertices all hang below it. Its middle vertex is
moved down to the same master's own 'V' bottom-vertex depth, and each
diagonal is re-solved as a strip of width `T` with its apex on one
boundary and that vertex on the other (the same construction as
'W''s middle strokes); the notch between the diagonals follows.

Point count and order are untouched -- only coordinates move -- so
master topology (and `serifs.py`'s reference-instance foot detection)
is preserved.

Point roles are hardcoded per glyph against Jost's own contour order,
confirmed identical at wght 100/400/900 and wdth 75/100; `_matches`
re-checks each one structurally before touching it, so a glyph whose
first contour doesn't fit (a differently-drawn Cyrillic analog, say) is
left alone rather than mangled.
"""

from __future__ import annotations

import math

# glyph name -> (kind, contour index)
TARGETS = {
    "V": ("V", 0),
    "v": ("v", 0),
    "W": ("W", 0),
    "Wcircumflex": ("W", 0),
    "w": ("w", 0),
    "wcircumflex": ("w", 0),
    "M": ("M", 0),
    "uni041C": ("M", 0),  # Cyrillic capital Em: same drawing as 'M' in Jost
}

# Point roles by index in Jost's own contour order.
_ROLES = {
    "V": dict(iv=0, iTL=1, oTL=2, B=3, oTR=4, iTR=5),
    "v": dict(oTL=0, B=1, oTR=2, iTR=3, iv=4, iTL=5),
    "W": dict(iv3=0, P=1, iv1=2, iTL=3, oTL=4, B1=5, notch=6, B2=7, oTR=8, iTR=9),
    "w": dict(oTL=0, B1=1, notch=2, B2=3, oTR=4, iTR=5, iv3=6, P=7, iv1=8, iTL=9),
    "M": dict(iv1=0, vb=1, iv2=2, ibR=3, obR=4, aR=5, notch=6, aL=7, obL=8, ibL=9),
}
_POINT_COUNT = {"V": 6, "v": 6, "W": 10, "w": 10, "M": 10}


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def _norm(v):
    length = math.hypot(v[0], v[1])
    return (v[0] / length, v[1] / length)


def _cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def _perp_dist(pt, p, d):
    """Unsigned distance from `pt` to the line through `p` along `d`."""
    return abs(_cross(_norm(d), _sub(pt, p)))


def _offset(p, d, t, toward):
    """The line parallel to (p, d), shifted `t` units toward `toward`."""
    u = _norm(d)
    n = (-u[1], u[0])
    if _dot(_sub(toward, p), n) < 0:
        n = (-n[0], -n[1])
    return (p[0] + n[0] * t, p[1] + n[1] * t), d


def _meet(l1, l2):
    (p, d), (q, e) = l1, l2
    den = _cross(d, e)
    if abs(den) < 1e-9:
        raise ValueError("parallel strokes")
    s = _cross(_sub(q, p), e) / den
    return (p[0] + s * d[0], p[1] + s * d[1])


def _horizontal(y):
    return (0.0, y), (1.0, 0.0)


def _strip(a, b, t, hint):
    """Direction of a parallel strip of width `t` with point `a` on one
    boundary and `b` on the other -- of the two solutions, the one
    closest to `hint`. Returns (line through a, line through b)."""
    diff = _sub(a, b)
    dist = math.hypot(diff[0], diff[1])
    base = math.atan2(diff[1], diff[0])
    off = math.asin(min(t / dist, 1.0))
    h = _norm(hint)
    best = None
    for ang in (base + off, base - off):
        u = (math.cos(ang), math.sin(ang))
        score = abs(_dot(u, h))
        if best is None or score > best[0]:
            best = (score, u)
    u = best[1]
    return (a, u), (b, u)


def _matches(kind, pts) -> bool:
    if len(pts) != _POINT_COUNT[kind] or any(p.type not in ("line",) for p in pts):
        return False
    r = _ROLES[kind]
    y = lambda k: pts[r[k]].y
    x = lambda k: pts[r[k]].x
    if kind in ("V", "v"):
        return abs(y("oTL") - y("iTL")) < 1 and abs(y("oTR") - y("iTR")) < 1 and y("B") < y("iv") < y("oTL")
    if kind in ("W", "w"):
        return (abs(y("oTL") - y("iTL")) < 1 and abs(y("oTR") - y("iTR")) < 1
                and y("B1") < y("iv1") and y("B2") < y("iv3") and y("notch") < y("P")
                and x("B1") < x("notch") < x("B2"))
    if kind == "M":
        return (abs(y("obL") - y("ibL")) < 1 and abs(y("obR") - y("ibR")) < 1
                and y("vb") < y("notch") < y("aL") and x("obL") < x("vb") < x("obR"))
    return False


def _solve(kind, P, overshoot=None):
    """P: role -> (x, y) of Jost's original points. Returns role ->
    new (x, y) for every inner point (and, for 'M' given `overshoot`,
    its middle vertex and notch)."""
    if kind in ("V", "v"):
        T = _perp_dist(_mid(P["iTL"], P["iv"]), P["oTL"], _sub(P["B"], P["oTL"]))
        left = _offset(P["oTL"], _sub(P["B"], P["oTL"]), T, P["iTL"])
        right = _offset(P["oTR"], _sub(P["B"], P["oTR"]), T, P["iTR"])
        return {
            "iTL": _meet(left, _horizontal(P["oTL"][1])),
            "iTR": _meet(right, _horizontal(P["oTR"][1])),
            "iv": _meet(left, right),
        }
    if kind in ("W", "w"):
        T = _perp_dist(_mid(P["iTL"], P["iv1"]), P["oTL"], _sub(P["B1"], P["oTL"]))
        s1 = _offset(P["oTL"], _sub(P["B1"], P["oTL"]), T, P["iTL"])
        s4 = _offset(P["oTR"], _sub(P["B2"], P["oTR"]), T, P["iTR"])
        s2_p, s2_b = _strip(P["P"], P["B1"], T, _sub(P["notch"], P["B1"]))
        s3_p, s3_b = _strip(P["P"], P["B2"], T, _sub(P["notch"], P["B2"]))
        return {
            "iTL": _meet(s1, _horizontal(P["oTL"][1])),
            "iTR": _meet(s4, _horizontal(P["oTR"][1])),
            "iv1": _meet(s1, s2_p),
            "iv3": _meet(s4, s3_p),
            "notch": _meet(s2_b, s3_b),
        }
    if kind == "M":
        T = _perp_dist(_mid(P["ibL"], P["iv1"]), P["obL"], _sub(P["aL"], P["obL"]))
        stem_l = _offset(P["obL"], _sub(P["aL"], P["obL"]), T, P["ibL"])
        stem_r = _offset(P["obR"], _sub(P["aR"], P["obR"]), T, P["ibR"])
        if overshoot is None:
            diag_l = _offset(P["aL"], _sub(P["notch"], P["aL"]), T, P["vb"])
            diag_r = _offset(P["aR"], _sub(P["notch"], P["aR"]), T, P["vb"])
            return {
                "ibL": _meet(stem_l, _horizontal(P["obL"][1])),
                "ibR": _meet(stem_r, _horizontal(P["obR"][1])),
                "iv1": _meet(stem_l, diag_l),
                "iv2": _meet(stem_r, diag_r),
                "vb": _meet(diag_l, diag_r),
            }
        vb = (P["vb"][0], overshoot)
        up_l, low_l = _strip(P["aL"], vb, T, _sub(P["notch"], P["aL"]))
        up_r, low_r = _strip(P["aR"], vb, T, _sub(P["notch"], P["aR"]))
        return {
            "ibL": _meet(stem_l, _horizontal(P["obL"][1])),
            "ibR": _meet(stem_r, _horizontal(P["obR"][1])),
            "iv1": _meet(stem_l, low_l),
            "iv2": _meet(stem_r, low_r),
            "vb": vb,
            "notch": _meet(up_l, up_r),
        }
    raise ValueError(kind)


def _mid(a, b):
    return ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)


def vertex_overshoot(v_glyph) -> float:
    """Depth of 'V''s own pointed bottom vertex at this master -- the
    overshoot 'M''s middle vertex is given (see module docstring)."""
    return min(p.y for p in v_glyph.contours[0].points)


def apply(glyph, overshoot: float | None = None) -> bool:
    """Equalizes `glyph`'s strokes in place if it's one of `TARGETS`
    and its contour matches the expected structure. `overshoot`
    (`vertex_overshoot`) is used by 'M'-kind glyphs only. Returns
    whether it was changed."""
    target = TARGETS.get(glyph.name)
    if target is None or len(glyph.contours) <= target[1]:
        return False
    kind, ci = target
    pts = glyph.contours[ci].points
    if not _matches(kind, pts):
        return False
    roles = _ROLES[kind]
    original = {role: (pts[i].x, pts[i].y) for role, i in roles.items()}
    for role, (x, y) in _solve(kind, original, overshoot if kind == "M" else None).items():
        pts[roles[role]].x = x
        pts[roles[role]].y = y
    return True


def stroke_thicknesses(glyph) -> list[float] | None:
    """Every stroke's perpendicular thickness at its midpoint, for
    verification (not used by the build)."""
    target = TARGETS.get(glyph.name)
    if target is None:
        return None
    kind, ci = target
    pts = glyph.contours[ci].points
    r = _ROLES[kind]
    P = {role: (pts[i].x, pts[i].y) for role, i in r.items()}
    def th(edge_a, edge_b, other_a, other_b):
        return _perp_dist(_mid(P[other_a], P[other_b]), P[edge_a], _sub(P[edge_b], P[edge_a]))
    if kind in ("V", "v"):
        return [th("oTL", "B", "iTL", "iv"), th("oTR", "B", "iTR", "iv")]
    if kind in ("W", "w"):
        return [th("oTL", "B1", "iTL", "iv1"), th("B1", "notch", "iv1", "P"),
                th("B2", "notch", "iv3", "P"), th("oTR", "B2", "iTR", "iv3")]
    return [th("obL", "aL", "ibL", "iv1"), th("aL", "notch", "iv1", "vb"),
            th("aR", "notch", "iv2", "vb"), th("obR", "aR", "ibR", "iv2")]
