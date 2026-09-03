"""Extracts real glyph outlines from the vendored Jost variable font.

Jost (SIL OFL 1.1, https://github.com/indestructible-type/Jost --
license copied to `v2/third_party/jost/OFL.txt`) is a real,
professionally drawn geometric sans. Per the project owner's direction,
this module takes its actual outlines as the starting point for v2's
letterforms -- the same way the repository root's own pipeline builds
from Roboto Flex -- rather than the from-scratch primitive
construction `geometry.py`/`glyphset.py` attempted first. Nothing here
is redrawn: `ufo_build.py` copies these outlines through as-is, and
Azrienoch's own modifications (Helvetica-inspired terminals/apertures,
axis behavior) are meant to be layered on top of this real data in
later passes.

Jost only exposes a `wght` axis (100-900) -- there is no `wdth` axis to
draw from. This module's width handling (`condense.condense_x`) is a
per-x compression profile derived from the glyph's own ink density, not
a true optically condensed redraw (no counter is actually reshaped) --
still a known simplification, see README.md, but no longer a flat
`x *= wf` scale: that thinned stems by the same factor it narrowed
counters, visibly uneven against horizontal strokes (untouched by any
X-axis scale) at heavy weight -- see `condense.py`'s own docstring.
"""

from __future__ import annotations

from pathlib import Path

from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

from . import condense

JOST_PATH = Path(__file__).resolve().parent.parent / "third_party" / "jost" / "Jost[wght].ttf"

_instance_cache: dict[int, TTFont] = {}


def _instance_at(wght: int) -> TTFont:
    if wght not in _instance_cache:
        font = TTFont(JOST_PATH)
        instantiateVariableFont(font, {"wght": wght}, inplace=True)
        _instance_cache[wght] = font
    return _instance_cache[wght]


def glyph_names_for_chars(chars: str) -> dict[str, str]:
    """Maps each character to Jost's own glyph name for it, via Jost's
    cmap (not assumed to equal the character itself, though for basic
    Latin it always does)."""
    font = _instance_at(400)
    cmap = font.getBestCmap()
    result = {}
    for ch in chars:
        cp = ord(ch)
        if cp not in cmap:
            raise KeyError(f"Jost has no glyph for {ch!r} (U+{cp:04X})")
        result[ch] = cmap[cp]
    return result


def extract(glyph_name: str, wght: int, wdth: int) -> tuple[list, float]:
    """Returns (pen_value, advance_width) for `glyph_name` at (wght, wdth).

    `pen_value` is a fontTools RecordingPen's `.value` -- a list of
    (operator, args) tuples, replayable onto another pen via `replay`.
    `wdth` != 100 runs `condense.condense_x` (see module docstring);
    coordinates are rounded to integers same as any font's units must be.
    """
    font = _instance_at(wght)
    glyph_set = font.getGlyphSet()
    if glyph_name not in glyph_set:
        raise KeyError(f"Jost has no glyph named {glyph_name!r}")

    pen = RecordingPen()
    glyph_set[glyph_name].draw(pen)
    width = glyph_set[glyph_name].width

    value, width = condense.condense_x(pen.value, width, wdth / 100.0)
    rounded = [(op, tuple(None if pt is None else (round(pt[0]), round(pt[1])) for pt in args)) for op, args in value]
    return rounded, width


def replay(pen, pen_value: list) -> None:
    for op, args in pen_value:
        getattr(pen, op)(*args)
