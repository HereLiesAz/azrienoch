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


def flat_topped_notch(pen, left_x: float, right_x: float, ceiling_y: float, radius: float) -> None:
    """A flat ceiling with a small fixed-radius rounded corner at each
    end -- an arch letter's counter (n/m/h/u/r), not a smooth oval
    spanning the whole gap: the ceiling stays flat and close to the
    letter's own top for nearly the entire span, only turning down right
    at each stem. A gradual oval across the full width (the previous
    approach here) makes the counter lens-shaped -- short at the stems,
    only opening up in the dead centre -- instead of the tall, roughly
    constant-width doorway a real arch counter is.

    Assumes the pen is already positioned at (right_x, ceiling_y -
    radius); ends at (left_x, ceiling_y - radius). Does not move or
    close.
    """
    pen.qCurveTo((right_x, ceiling_y), (right_x - radius, ceiling_y))
    pen.lineTo((left_x + radius, ceiling_y))
    pen.qCurveTo((left_x, ceiling_y), (left_x, ceiling_y - radius))
