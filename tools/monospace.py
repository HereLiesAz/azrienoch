"""The Mono end of the width axis (`wdth` = 0).

At `wdth` 0 every glyph has one fixed advance (`params.MONO_ADVANCE`). The
master is built exactly like the Condensed one (`wdth` 75), then each glyph is
fitted into the cell: ink wider than the cell's usable width is compressed with
`condense.condense_x` (the same ink-density compression every other width gets,
so stems keep their weight and the counters give way), and every glyph is
centred in the cell. Zero-advance glyphs (combining marks) are left alone.

The shapes are the Condensed shapes compressed or moved, never redrawn, so
Mono, Condensed and Normal share one structure and the axis interpolates
smoothly between all three; kerning is simply absent at this end and fades
out as `wdth` approaches 0.
"""

from __future__ import annotations

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import RecordingPen

from . import condense, params


def apply(font) -> None:
    cell = params.MONO_ADVANCE
    usable = cell - 2 * params.MONO_MIN_SIDEBEARING
    for glyph in font:
        if glyph.width == 0:
            continue
        pen = BoundsPen(None)
        glyph.draw(pen)
        if pen.bounds is None:
            glyph.width = cell
            continue
        x0, _, x1, _ = pen.bounds
        ink = x1 - x0
        warp = lambda x: x
        if ink > usable:
            rec = RecordingPen()
            glyph.draw(rec)
            value = [
                (cmd, tuple(None if p is None else (p[0] - x0, p[1]) for p in args))
                for cmd, args in rec.value
            ]
            warp, ink = condense.condense_map(value, ink, usable / ink)
        else:
            warp = lambda x: x
        shift = (cell - ink) / 2.0
        # Move the points where they stand: the outline's points, their
        # order and its start point stay exactly as in the Condensed master.
        for contour in glyph.contours:
            for p in contour.points:
                p.x = round(warp(p.x - x0) + shift)
        glyph.width = cell
