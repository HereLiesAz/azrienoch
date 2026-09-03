"""Builds one UFO per master in params.MASTER_GRID.

Glyph outlines are copied from the vendored Jost variable font
(see jost_source.py) at each master's (wght, wdth) -- not drawn from
scratch. Covers the basic Latin alphabet (A-Z, a-z) and digits (0-9),
62 glyphs, all plain contours in Jost (no composites to decompose)."""

from __future__ import annotations

import string
from pathlib import Path

import ufoLib2

from . import jost_source, params, quirks

SOURCES_DIR = Path(__file__).resolve().parent.parent / "sources"

_DIGIT_NAMES = {
    "0": "zero", "1": "one", "2": "two", "3": "three", "4": "four",
    "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine",
}
CHARS = string.ascii_uppercase + string.ascii_lowercase + string.digits


def _glyph_name(ch: str) -> str:
    return _DIGIT_NAMES.get(ch, ch)


def _contour_area(contour) -> float:
    xs = [p.x for p in contour.points]
    ys = [p.y for p in contour.points]
    return (max(xs) - min(xs)) * (max(ys) - min(ys))


def _o_inner_contour(o_glyph):
    """'o's two contours are its outer silhouette and its inner counter;
    the inner one is simply the smaller of the two by bounding-box area
    -- true for any letter 'o' by construction, no need for a general
    point-in-polygon test here."""
    return min(o_glyph.contours, key=_contour_area)


def build_master_ufo(wght: int, wdth: int) -> Path:
    font = ufoLib2.Font()
    font.info.unitsPerEm = params.UPM
    font.info.ascender = params.ASCENDER
    font.info.descender = params.DESCENDER
    font.info.capHeight = params.CAP_HEIGHT
    font.info.xHeight = params.X_HEIGHT
    font.info.familyName = "Azrienoch V2"
    font.info.styleName = params.style_name(wght, wdth)
    font.info.versionMajor = 0
    font.info.versionMinor = 1

    jost_names = jost_source.glyph_names_for_chars(CHARS)
    for ch in CHARS:
        pen_value, width = jost_source.extract(jost_names[ch], wght, wdth)
        glyph = font.newGlyph(_glyph_name(ch))
        glyph.unicodes = [ord(ch)]
        jost_source.replay(glyph.getPen(), pen_value)
        glyph.width = width

    for ch in CHARS:
        quirks.apply_terminal_cuts(font[_glyph_name(ch)])

    o_inner_points = _o_inner_contour(font["o"]).points
    for name in quirks.ROUND_COUNTER_GLYPHS:
        quirks.reshape_counter_to_o(font[name], o_inner_points)

    path = SOURCES_DIR / f"AzrienochV2-{params.style_name(wght, wdth)}.ufo"
    font.save(path, overwrite=True)
    return path


def build_all() -> list[Path]:
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    return [build_master_ufo(wght, wdth) for wght, wdth in params.MASTER_GRID]


if __name__ == "__main__":
    for p in build_all():
        print(p)
