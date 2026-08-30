"""A deterministic (non-adaptive) quadratic-to-cubic conversion pen.

fontTools' own ``Qu2CuPen`` fits cubics to a curve-error tolerance, which
can pick a *different number* of output segments for glyph instances that
started with the same point topology (guaranteed by gvar across every
master of a variable font) but happen to have differently-curved
coordinates at each master -- silently breaking interpolation
compatibility between Multiplex's masters. Degree-elevating each
TrueType quadratic segment to exactly one cubic, with no fitting or
merging, is lossless and always emits the same number of segments as the
input has -- which is what compatibility actually requires here.
"""

from __future__ import annotations

from fontTools.pens.basePen import BasePen


class ExactQu2CuPen(BasePen):
    def __init__(self, other_pen):
        super().__init__(glyphSet={})
        self.otherPen = other_pen

    def _moveTo(self, pt):
        self.otherPen.moveTo(pt)

    def _lineTo(self, pt):
        self.otherPen.lineTo(pt)

    def _curveToOne(self, p1, p2, p3):
        self.otherPen.curveTo(p1, p2, p3)

    def _qCurveToOne(self, p1, p2):
        p0 = self._getCurrentPoint()
        c1 = (p0[0] + 2 / 3 * (p1[0] - p0[0]), p0[1] + 2 / 3 * (p1[1] - p0[1]))
        c2 = (p2[0] + 2 / 3 * (p1[0] - p2[0]), p2[1] + 2 / 3 * (p1[1] - p2[1]))
        self.otherPen.curveTo(c1, c2, p2)

    def _closePath(self):
        self.otherPen.closePath()

    def _endPath(self):
        self.otherPen.endPath()
