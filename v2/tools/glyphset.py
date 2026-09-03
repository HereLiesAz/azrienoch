"""Parametric glyph constructions -- the proof set for Azrienoch v2.

Each `draw_*` function draws one glyph's outline(s) onto a fontTools
segment pen and returns its advance width, given this master's Metrics
(stem thickness, width factor, fixed vertical metrics). Every letterform
here is a from-scratch geometric construction: straight-sided strokes and
concentric-oval bowls/arches, in the spirit of geometric sans
construction (Jost's own circle/square/triangle discipline), cut to flat
rational terminals (no bracketed serifs, no ball terminals -- Helvetica's
directness) rather than traced from any existing font's outline data.

This is deliberately a small proof set (H O o n v T l one) covering the
four stroke situations the rest of the alphabet reuses -- straight stems,
a diagonal join, a full round bowl, and a stem-to-curve arch spring --
not the full character set. See v2/README.md.
"""

from __future__ import annotations

from .geometry import arch_quadrant_pair, draw_oval, draw_polygon
from .params import Metrics


def draw_H(pen, m: Metrics) -> float:
    stem = m.stem
    width = round(640 * m.wf)
    bar_h = stem * 0.9
    bar_c = m.cap * 0.5
    bar_top, bar_bot = bar_c + bar_h / 2, bar_c - bar_h / 2
    draw_polygon(pen, [
        (0, 0), (0, m.cap), (stem, m.cap), (stem, bar_top),
        (width - stem, bar_top), (width - stem, m.cap), (width, m.cap), (width, 0),
        (width - stem, 0), (width - stem, bar_bot), (stem, bar_bot), (stem, 0),
    ])
    return width


def draw_T(pen, m: Metrics) -> float:
    stem = m.stem
    width = round(560 * m.wf)
    top = m.cap - stem
    mid_l, mid_r = width / 2 - stem / 2, width / 2 + stem / 2
    draw_polygon(pen, [
        (0, m.cap), (width, m.cap), (width, top), (mid_r, top),
        (mid_r, 0), (mid_l, 0), (mid_l, top), (0, top),
    ])
    return width


def draw_l(pen, m: Metrics) -> float:
    stem = m.stem
    margin = round(60 * m.wf)
    width = stem + 2 * margin
    draw_polygon(pen, [
        (margin, 0), (margin, m.asc), (margin + stem, m.asc), (margin + stem, 0),
    ])
    return width


def draw_one(pen, m: Metrics) -> float:
    stem = m.stem
    margin = round(60 * m.wf)
    x0, x1 = margin, margin + stem
    flag_h = stem * 1.1
    flag_tip = (x0 - stem * 0.8, m.cap - flag_h)
    draw_polygon(pen, [
        (x1, m.cap), (x0, m.cap), flag_tip, (x0, m.cap - flag_h),
        (x0, 0), (x1, 0),
    ])
    width = x1 + margin
    return width


def draw_v(pen, m: Metrics) -> float:
    width = round(560 * m.wf)
    inner = min(m.stem * 1.4, width * 0.4)
    apex = (width / 2, 0)
    draw_polygon(pen, [
        (0, m.xh), apex, (width, m.xh),
        (width - inner, m.xh), apex, (inner, m.xh),
    ])
    return width


def draw_O(pen, m: Metrics) -> float:
    width = round(700 * m.wf)
    rx, ry = width / 2, m.cap / 2
    cx, cy = width / 2, m.cap / 2
    hole = m.stem * 0.85
    draw_oval(pen, cx, cy, rx, ry, clockwise=True)
    draw_oval(pen, cx, cy, max(rx - hole, rx * 0.1), max(ry - hole, ry * 0.1), clockwise=False)
    return width


def draw_o(pen, m: Metrics) -> float:
    width = round(560 * m.wf)
    rx, ry = width / 2, m.xh / 2
    cx, cy = width / 2, m.xh / 2
    hole = m.stem * 0.85
    draw_oval(pen, cx, cy, rx, ry, clockwise=True)
    draw_oval(pen, cx, cy, max(rx - hole, rx * 0.1), max(ry - hole, ry * 0.1), clockwise=False)
    return width


def draw_n(pen, m: Metrics) -> float:
    """Stem, stem, and an arch: the counter's ceiling is a curve embedded
    in the single outer contour, not a separate contour (there's nothing
    to subtract a hole from -- the arch is open at the bottom).

    The stem tops are flat at x-height (the outer silhouette is a plain
    rectangle); all of the arch's roundness is in the counter's ceiling,
    which rises to a thin bridge just under x-height across the middle
    and drops to meet each stem's inner edge at its own spring point --
    a dome, not a valley: `arch_quadrant_pair` is reused with a negative
    `ry` to flip it from the sagging-valley curve it draws by default
    into this rising-dome one.
    """
    stem = m.stem
    width = max(round(620 * m.wf), 2 * stem + 60)
    spring = m.xh * 0.42
    bridge = stem * 0.85
    peak = m.xh - bridge
    cx = width / 2
    rx = width / 2 - stem

    pen.moveTo((0, 0))
    pen.lineTo((0, m.xh))
    pen.lineTo((width, m.xh))
    pen.lineTo((width, 0))
    pen.lineTo((width - stem, 0))
    pen.lineTo((width - stem, spring))
    arch_quadrant_pair(pen, cx, peak, rx, spring - peak)
    pen.lineTo((stem, 0))
    pen.closePath()
    return width


# glyph name -> (unicode codepoint, draw function)
GLYPHS = {
    "H": (0x0048, draw_H),
    "T": (0x0054, draw_T),
    "O": (0x004F, draw_O),
    "o": (0x006F, draw_o),
    "n": (0x006E, draw_n),
    "v": (0x0076, draw_v),
    "l": (0x006C, draw_l),
    "one": (0x0031, draw_one),
}
