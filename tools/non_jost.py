"""The characters Jost does not carry, built from the finished glyphs of one
master: composed Latin letters, barred letters and digraphs
(`composites.py`), and the logic symbols (`symbols.py`).

Called once per master, after every Jost-derived glyph is final, so each new
glyph is made from this build's own letters rather than Jost's.
"""

from __future__ import annotations

import unicodedata

from fontTools.pens.boundsPen import BoundsPen

from . import composites, params, serifs, strokes, symbols


def _height(glyph) -> float:
    pen = BoundsPen(None)
    glyph.draw(pen)
    return pen.bounds[3] - pen.bounds[1]


def _outer_is_clockwise(glyph) -> bool:
    c = glyph.contours[0]
    pts = [(p.x, p.y) for p in c.points]
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    return area < 0


def build(font, namer, wght: int, wdth: int, grad: int) -> None:
    strokes.CLOCKWISE_OUTER = _outer_is_clockwise(font["I"])
    stem = serifs.stem_width(font["l"])
    bar = _height(font[namer("\u2212")])           # Jost's own minus: the horizontal stroke weight
    marks = composites.Marks(wght, wdth, grad, stem)
    ogonek_dx = composites.ogonek_offset(font, namer, wght, wdth, grad)

    for ch in params.DIGRAPHS:
        g = font.newGlyph(namer(ch))
        g.unicodes = [ord(ch)]
        composites.compose_digraph(font, g, ch, namer)
    for ch in params.BARRED:
        g = font.newGlyph(namer(ch))
        g.unicodes = [ord(ch)]
        composites.compose_barred(font, g, ch, bar, namer)
    for ch in params.COMPOSED:
        g = font.newGlyph(namer(ch))
        g.unicodes = [ord(ch)]
        composites.compose_marked(font, g, ch, marks, ogonek_dx, namer)
    symbols.build(font, namer, wght, wdth, grad)
