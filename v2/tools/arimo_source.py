"""Extracts 'c'/'e'/'s' from Arimo (vendored at `third_party/arimo/`, SIL
OFL 1.1 -- license copied to `third_party/arimo/OFL.txt`), an open,
metric-compatible Helvetica/Arial workalike -- per the project owner's
direction that these three letters read as Helvetica-derived, without
tracing or extracting actual (proprietary) Helvetica outline data. Same
legal basis as this project's use of Jost and the repository root's use
of Roboto Flex: a freely licensed font, used and modified as its license
explicitly permits.

Arimo ships only as static instances, not a variable font, and Google
Fonts only serves four weights for it (400/500/600/700) -- this module
vendors just Regular (400) and Bold (700), the two needed to cover this
project's own `wght` sample range (100/400/900, see `params.py`), and
LINEARLY interpolates (or, for `wght` past 700, extrapolates) between
their point coordinates and advance widths directly, rather than
sampling a real gvar interpolation the source font doesn't have.
Confirmed safe to do this point-for-point (not just plausible): 'c'/'e'/
's' have IDENTICAL point-command signatures between Regular and Bold
(same command sequence, same argument count per command, checked
directly), so corresponding points can be paired by index with no
topology mismatch. Extrapolating past Bold's own 700 for this project's
`wght`=900 sample necessarily overshoots what Arimo's own designer
actually drew at any real weight -- an approximation, not a real Black
instance -- accepted for the same reason `roboto_s_source.py` clamps
`wght`=100 to root's own floor of 180: the closest available real
information, stretched a bit, beats inventing a fourth weight's geometry
from nothing.

Rescaled from Arimo's own metrics (UPM 2048, x-height 1082) to Azrienoch
v2's (UPM 1000, x-height 470) via the x-height ratio, the same shortcut
`roboto_s_source.py` uses and for the same reason: all three of these
letters sit entirely within the x-height box in both fonts.
"""

from __future__ import annotations

from pathlib import Path

from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont

from . import params

ARIMO_DIR = Path(__file__).resolve().parent.parent / "third_party" / "arimo"
ARIMO_X_HEIGHT = 1082.0
_REGULAR_WGHT, _BOLD_WGHT = 400.0, 700.0

_glyphsets_cache: dict[str, object] | None = None


def _glyphsets():
    global _glyphsets_cache
    if _glyphsets_cache is None:
        regular = TTFont(ARIMO_DIR / "Arimo-Regular.ttf")
        bold = TTFont(ARIMO_DIR / "Arimo-Bold.ttf")
        _glyphsets_cache = {
            "regular": (regular.getGlyphSet(), regular.getBestCmap()),
            "bold": (bold.getGlyphSet(), bold.getBestCmap()),
        }
    return _glyphsets_cache


def _record(ch: str, key: str):
    glyphset, cmap = _glyphsets()[key]
    gname = cmap[ord(ch)]
    glyph = glyphset[gname]
    pen = RecordingPen()
    glyph.draw(pen)
    return pen.value, glyph.width


def extract(ch: str, wght: int, wdth: int):
    """Returns (pen_value, width) for `ch` ('c', 'e', or 's'), linearly
    interpolated/extrapolated between Arimo Regular (400) and Bold (700)
    to this project's own `wght`, rescaled into Azrienoch v2's
    coordinate space -- same return shape as `jost_source.extract`."""
    reg_value, reg_width = _record(ch, "regular")
    bold_value, bold_width = _record(ch, "bold")

    frac = (wght - _REGULAR_WGHT) / (_BOLD_WGHT - _REGULAR_WGHT)
    scale = params.X_HEIGHT / ARIMO_X_HEIGHT
    wdth_scale = wdth / 100.0

    out = []
    for (cmd, reg_args), (_, bold_args) in zip(reg_value, bold_value):
        new_args = tuple(
            (
                (rx + (bx - rx) * frac) * scale * wdth_scale,
                (ry + (by - ry) * frac) * scale,
            )
            for (rx, ry), (bx, by) in zip(reg_args, bold_args)
        )
        out.append((cmd, new_args))
    width = (reg_width + (bold_width - reg_width) * frac) * scale * wdth_scale
    return out, width
