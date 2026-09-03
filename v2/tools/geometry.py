"""Drawing primitives shared by glyphset.py.

Every glyph in this module is built from these two primitives -- a
straight-sided polygon and a concentric oval ring -- rather than
extracted from any existing font's outline data.
"""

from __future__ import annotations


def draw_oval(pen, cx: float, cy: float, rx: float, ry: float, clockwise: bool = True) -> None:
    """A single closed oval contour, four quadratic arcs.

    Each arc's off-curve point sits at the corner where the two
    quarter-arc's tangent lines meet (e.g. the vertical tangent at the
    east point and the horizontal tangent at the north point meet at
    (cx+rx, cy+ry)) -- exact tangency at both ends, a small (~3%) radial
    bulge at the arc's midpoint, the standard four-arc circle/oval
    approximation.
    """
    e = (cx + rx, cy)
    n = (cx, cy + ry)
    w = (cx - rx, cy)
    s = (cx, cy - ry)
    ne = (cx + rx, cy + ry)
    nw = (cx - rx, cy + ry)
    sw = (cx - rx, cy - ry)
    se = (cx + rx, cy - ry)

    pen.moveTo(e)
    if clockwise:
        pen.qCurveTo(se, s)
        pen.qCurveTo(sw, w)
        pen.qCurveTo(nw, n)
        pen.qCurveTo(ne, e)
    else:
        pen.qCurveTo(ne, n)
        pen.qCurveTo(nw, w)
        pen.qCurveTo(sw, s)
        pen.qCurveTo(se, e)
    pen.closePath()


def draw_polygon(pen, points: list[tuple[float, float]]) -> None:
    """A single closed contour of straight lines through `points`."""
    pen.moveTo(points[0])
    for pt in points[1:]:
        pen.lineTo(pt)
    pen.closePath()


def arch_quadrant_pair(pen, cx: float, bottom_y: float, rx: float, ry: float) -> None:
    """Two quadratic arcs forming the bottom half of an oval, right-to-left.

    Draws from (cx+rx, bottom_y+ry) down to (cx, bottom_y) and back up to
    (cx-rx, bottom_y+ry) -- the underside of an arch letter's counter
    (see glyphset.draw_n). Assumes the pen is already positioned at
    (cx+rx, bottom_y+ry); does not move or close.
    """
    pen.qCurveTo((cx + rx, bottom_y), (cx, bottom_y))
    pen.qCurveTo((cx - rx, bottom_y), (cx - rx, bottom_y + ry))
