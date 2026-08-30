"""Minimal glyph-contour helpers used by the SERF axis (see serifs.py).

Just enough to build a rectangle contour and append it into a glyph:
serif feet are always plain rectangles (by the terminal rule -- see
serifs.py), so nothing fancier than this is needed.
"""

from __future__ import annotations

import ufoLib2


def polygon(pts):
    """A single closed polygon primitive from a list of (x, y) points."""
    g = ufoLib2.objects.Glyph()
    pen = g.getPen()
    pts = [(round(x, 2), round(y, 2)) for x, y in pts]
    pen.moveTo(pts[0])
    for p in pts[1:]:
        pen.lineTo(p)
    pen.closePath()
    return g


def rect(x0, y0, x1, y1):
    """Axis-aligned rectangle -- the serif-foot primitive."""
    if x0 > x1:
        x0, x1 = x1, x0
    if y0 > y1:
        y0, y1 = y1, y0
    return polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


def append_into(glyph, shape):
    """Append shape's contours into an existing ufoLib2 glyph, in place."""
    pen = glyph.getPointPen()
    for contour in shape.contours:
        pen.beginPath()
        for p in contour.points:
            pen.addPoint((p.x, p.y), segmentType=p.type, smooth=p.smooth)
        pen.endPath()
    return glyph
