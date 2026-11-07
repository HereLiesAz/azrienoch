"""Hand-drawn glyphs (`sources/drawn/*.morphont.json`, drawn in Morphont).

`Y` and `y` are drawn, not derived: one cubic outline each at the three weight
extremes (`wght_lo` = 100, `regular` = 400, `wght_hi` = 900), at the default
width, serif and grade. `apply` replaces the pipeline's procedural Y/y with
them, at any master of the grid:

- weight: linear between the drawn weights (what the compiled font's own
  interpolation does between masters), at `wght` shifted by `grad` exactly as
  `jost_source.extract` does for every other glyph; the advance width follows
  the requested `wght` alone, so GRAD never reflows text;
- width: `condense.condense_x`, the same compression every other glyph gets;
- serif: nothing here; `serifs.apply_feet` runs afterwards on the result, as
  for every other glyph.

Morphont points are cubic: on-curve, off-curve, off-curve, on-curve, with
duplicated points marking corners. Every drawn weight has the same points in the
same order, so all masters stay interpolation-compatible.
"""

from __future__ import annotations

import json
from pathlib import Path

from ufoLib2.objects import Contour, Point

from . import condense
from .jost_source import GRAD_TO_WGHT

DRAWN_DIR = Path(__file__).resolve().parent.parent / "sources" / "drawn"
# Drawn anchor -> the wght it is the master for.
_ANCHORS = (("wght_lo", 100), ("regular", 400), ("wght_hi", 900))
DRAWN_CHARS = ("Y", "y")

_cache: dict[str, list[tuple[int, float, list[list[tuple[float, float, bool]]]]]] = {}


def _load(char: str):
    if char not in _cache:
        data = json.loads((DRAWN_DIR / f"{char}.morphont.json").read_text())
        out = []
        for anchor, wght in _ANCHORS:
            corner = data["corners"][anchor]
            contours = [[(p["x"], p["y"], p["onCurve"]) for p in c["points"]] for c in corner["contours"]]
            out.append((wght, float(corner["width"]), contours))
        shapes = [[len(c) for c in contours] for _, _, contours in out]
        if any(s != shapes[0] for s in shapes):
            raise ValueError(f"{char}: drawn weights are not point-compatible: {shapes}")
        _cache[char] = out
    return _cache[char]


def _blend(masters, wght: float):
    """(width, contours) at `wght`, linear between the drawn weights."""
    wght = max(masters[0][0], min(masters[-1][0], wght))
    for (w0, width0, c0), (w1, width1, c1) in zip(masters, masters[1:]):
        if wght <= w1:
            t = (wght - w0) / (w1 - w0)
            width = width0 + t * (width1 - width0)
            contours = [
                [(a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]), a[2]) for a, b in zip(ca, cb)]
                for ca, cb in zip(c0, c1)
            ]
            return width, contours
    raise AssertionError


def _pen_value(contours):
    """Cubic pen commands for the closed contours (each starts on-curve)."""
    value = []
    for pts in contours:
        n = len(pts)
        start = next(i for i, p in enumerate(pts) if p[2])
        value.append(("moveTo", ((pts[start][0], pts[start][1]),)))
        offs = []
        for k in range(1, n + 1):
            x, y, on = pts[(start + k) % n]
            if not on:
                offs.append((x, y))
            elif not offs:
                value.append(("lineTo", ((x, y),)))
            else:
                value.append(("curveTo", (offs[0], offs[-1], (x, y))))
                offs = []
        value.append(("closePath", ()))
    return value


def _contours_from_pen(value):
    contours, pts, offs = [], [], 0
    for op, args in value:
        if op == "moveTo":
            pts, offs = [], 0
            start = args[0]
        elif op == "lineTo":
            pts.append(Point(round(args[0][0]), round(args[0][1]), "line", False))
        elif op == "curveTo":
            for a in args[:2]:
                pts.append(Point(round(a[0]), round(a[1]), None, False))
            pts.append(Point(round(args[2][0]), round(args[2][1]), "curve", False))
        elif op == "closePath":
            # The closing segment ends on the start point, which starts the list.
            contours.append((start, pts))
    out = []
    for start, pts in contours:
        # The last on-curve point of the run coincides with the start: the
        # start is that point, so rotate it to the front instead of repeating it.
        last = pts[-1]
        if (last.x, last.y) == (round(start[0]), round(start[1])) and last.type in ("line", "curve"):
            pts = [last] + pts[:-1]
        else:
            pts = [Point(round(start[0]), round(start[1]), "line", False)] + pts
        out.append(Contour(points=pts))
    return out


def apply(font, glyph_name: str, char: str, wght: int, wdth: int, grad: int = 0) -> None:
    """Replaces `glyph_name`'s outline and advance with the drawn `char`."""
    masters = _load(char)
    effective = max(100, min(900, wght + round(grad * GRAD_TO_WGHT))) if grad else wght
    width_at_wght, _ = _blend(masters, wght)
    _, contours = _blend(masters, effective)
    value, width = condense.condense_x(_pen_value(contours), width_at_wght, wdth / 100.0)
    if grad and wdth != 100:
        # Advance from the requested wght alone (as jost_source.extract does).
        _, width = condense.condense_x(_pen_value(_blend(masters, wght)[1]), width_at_wght, wdth / 100.0)
    glyph = font[glyph_name]
    glyph.clearContours()
    for c in _contours_from_pen(value):
        glyph.contours.append(c)
    glyph.width = round(width)
