"""Builds one UFO per master in params.MASTER_GRID.

Glyph outlines are copied from the vendored Jost variable font
(see jost_source.py) at each master's (wght, wdth) -- not drawn from
scratch. Covers the basic Latin alphabet (A-Z, a-z) and digits (0-9),
62 glyphs, all plain contours in Jost (no composites to decompose).

Serif feet (the SERF axis) are detected ONCE per glyph, on a single
reference instance (wght=400, wdth=100, before any foot is applied --
see serifs.py), and the same fractional specs are then reapplied at
every master, scaled to that master's own glyph width -- never
redetected per master. Redetecting fresh at each master risks a
different foot count at different weights/widths (a flat run that's
long enough to count as a stem at one width might not be at another),
which would give different masters different topology and fail to
compile; reusing one reference's decision is what the root project's
own tools/serifs.py this was ported from does too, for the same reason.
"""

from __future__ import annotations

import string
from pathlib import Path

import ufoLib2

from . import arimo_source, jost_source, params, quirks, serifs, single_story_a

_ARIMO_CHARS = {"c", "e", "s"}

SOURCES_DIR = Path(__file__).resolve().parent.parent / "sources"

_DIGIT_NAMES = {
    "0": "zero", "1": "one", "2": "two", "3": "three", "4": "four",
    "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine",
}
CHARS = string.ascii_uppercase + string.ascii_lowercase + string.digits

_REFERENCE_WGHT, _REFERENCE_WDTH = 400, 100


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


def _build_raw_glyphs(wght: int, wdth: int) -> ufoLib2.Font:
    """Extracts every glyph from Jost -- except 'c'/'e'/'s', pulled from
    the vendored Arimo instead (see `arimo_source.py`: an open, metric-
    compatible Helvetica/Arial workalike, used because these three
    letters are meant to read as Helvetica-derived, and actual
    Helvetica outline data is proprietary) -- and applies the terminal-
    cut and round-counter modifications -- everything except serif feet.
    Arimo's own 'c'/'e'/'s' terminals are close to horizontal but
    genuinely diagonal by design, so they go through
    `apply_terminal_cuts` too, just with Arimo's own point indices
    rather than Jost's.
    """
    font = ufoLib2.Font()
    jost_names = jost_source.glyph_names_for_chars(CHARS)
    for ch in CHARS:
        glyph = font.newGlyph(_glyph_name(ch))
        glyph.unicodes = [ord(ch)]
        if ch in _ARIMO_CHARS:
            pen_value, width = arimo_source.extract(ch, wght, wdth)
        else:
            pen_value, width = jost_source.extract(jost_names[ch], wght, wdth)
        jost_source.replay(glyph.getPen(), pen_value)
        glyph.width = width

    quirks.fix_y_crotch(font["y"])
    quirks.fix_six_nine_notch(font["six"])
    quirks.fix_six_nine_notch(font["nine"])

    for ch in CHARS:
        quirks.apply_terminal_cuts(font[_glyph_name(ch)])

    o_inner_points = _o_inner_contour(font["o"]).points
    for name in quirks.ROUND_COUNTER_GLYPHS:
        quirks.reshape_counter_to_o(font[name], o_inner_points)

    # 'a' is single-story, built directly from 'd's own (by now fully
    # finalized -- counter already reshaped to 'o's own) outline, per the
    # project owner's direction, rather than kept as Jost's own separately
    # drawn 'a' (which happens to already be single-story too, but isn't
    # literally 'd' with a shortened stem the way this project wants it).
    font["a"] = single_story_a.build_from_d(font["d"], params.X_HEIGHT)

    return font


_serif_reference_cache: dict[str, tuple[list[dict], dict[str, float]]] | None = None


def _serif_reference() -> dict[str, tuple[list[dict], dict[str, float]]]:
    """The {char: (foot_specs, guides)} cache, built once from the
    reference instance (see module docstring)."""
    global _serif_reference_cache
    if _serif_reference_cache is not None:
        return _serif_reference_cache
    reference_font = _build_raw_glyphs(_REFERENCE_WGHT, _REFERENCE_WDTH)
    cache = {}
    for ch in CHARS:
        glyph = reference_font[_glyph_name(ch)]
        min_y = min(p.y for c in glyph.contours for p in c.points)
        guides = serifs.guides_for(ch, min_y)
        specs = serifs.detect_feet(glyph, guides, ch)
        cache[ch] = (specs, guides)
    _serif_reference_cache = cache
    return cache


def build_master_ufo(wght: int, wdth: int, serf: int) -> Path:
    font = _build_raw_glyphs(wght, wdth)
    font.info.unitsPerEm = params.UPM
    font.info.ascender = params.ASCENDER
    font.info.descender = params.DESCENDER
    font.info.capHeight = params.CAP_HEIGHT
    font.info.xHeight = params.X_HEIGHT
    font.info.familyName = "Azrienoch V2"
    font.info.styleName = params.style_name(wght, wdth, serf)
    font.info.versionMajor = 0
    font.info.versionMinor = 1

    reference = _serif_reference()
    for ch in CHARS:
        specs, guides = reference[ch]
        serifs.apply_feet(font[_glyph_name(ch)], specs, guides, serf)

    path = SOURCES_DIR / f"AzrienochV2-{params.style_name(wght, wdth, serf)}.ufo"
    font.save(path, overwrite=True)
    return path


def build_all() -> list[Path]:
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    return [build_master_ufo(wght, wdth, serf) for wght, wdth, serf in params.MASTER_GRID]


if __name__ == "__main__":
    for p in build_all():
        print(p)
