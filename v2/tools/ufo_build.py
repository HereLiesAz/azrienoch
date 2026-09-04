"""Builds one UFO per master in params.MASTER_GRID.

Glyph outlines are copied from the vendored Jost variable font
(see jost_source.py) at each master's (wght, wdth) -- not drawn from
scratch. Covers the basic Latin alphabet (A-Z, a-z), digits (0-9),
punctuation, Latin-1 Supplement, Latin Extended-A, and Cyrillic --
every script the repository root's own v1 pipeline covers except
Greek, which Jost barely has any glyphs for (4 codepoints total) and
so needs a separate donor font, not yet vendored here. All plain
contours in vendored Jost (no composites to decompose) for every
character in this set, confirmed directly rather than assumed.

Extending PAST plain extraction: `quirks.py`'s round-counter treatment
and `serifs.py`'s per-letter-class foot rules now extend to accented
Latin variants too, via `params.base_letter` (NFD-decomposition-based:
'ē' resolves to 'e', 'ō' to 'o', etc.) -- an accented o/b/d/p/q/g gets
its counter reshaped to match plain 'o's the same way its base letter
does, and every accented letter grows serif feet at the same guide
lines its base letter would, rather than falling through to the
uppercase/digit baseline-only default. `quirks.py`'s terminal-cut
treatment covers the 18 c/e/s-based accented letters (via
`accent_marks.py`'s mark-splicing, see below) plus 3 r-based ones
directly; Cyrillic has no equivalent per-letter-class treatment yet
(no NFD-decomposable base to resolve to), so it still gets Jost's raw
shape at the whole-letter level only. `kerning.py`, unlike the above,
is NOT similarly scoped -- it already covers the full character set
(see its own module docstring).

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

from pathlib import Path

import ufoLib2
from fontTools.pens.recordingPen import RecordingPen

from . import accent_marks, arimo_source, jost_source, kerning, params, quirks, ring_derived, serifs, single_story_a

_ARIMO_CHARS = {"s"}
_RING_DERIVED_CHARS = {"c", "e"}

SOURCES_DIR = Path(__file__).resolve().parent.parent / "sources"

_DIGIT_NAMES = {
    "0": "zero", "1": "one", "2": "two", "3": "three", "4": "four",
    "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine",
}
_SPACE_NAME = "space"

# Character set (all scripts this project covers except Greek) lives in
# params.py, not here -- kerning.py (which this module imports) needs
# the same set without importing this module back (a cycle).
CHARS = params.CHARS

_REFERENCE_WGHT, _REFERENCE_WDTH = 400, 100

_jost_name_map: dict[str, str] | None = None


def _glyph_name(ch: str) -> str:
    """The name this project's own UFO/TTF glyph gets for `ch`. Digits
    and space get their own conventional names (kept for backward
    compatibility with `kerning.py` and existing sources, which already
    key off "zero"/"a"/etc., not a literal "0"/" "); everything else
    reuses Jost's own glyph name for that character. Jost's own names
    are already safe, ASCII-only, standard glyph names (e.g. "Agrave",
    "uni0401") -- using the character itself as a glyph name instead
    (tried first) compiles fine as a UFO but fails at the very last
    TTF-writing step, where the 'post' table can't encode a non-Latin-1
    glyph name at all -- confirmed directly: fontmake errored trying to
    write "Ā" (U+0100) as a glyph name once this project's own
    character set grew past ASCII."""
    if ch == " ":
        return _SPACE_NAME
    if ch in _DIGIT_NAMES:
        return _DIGIT_NAMES[ch]
    global _jost_name_map
    if _jost_name_map is None:
        _jost_name_map = jost_source.glyph_names_for_chars(CHARS)
    return _jost_name_map[ch]


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


def _build_raw_glyphs(wght: int, wdth: int, grad: int = 0) -> ufoLib2.Font:
    """Extracts every glyph from Jost -- except 's', pulled from the
    vendored Arimo instead (see `arimo_source.py`: an open, metric-
    compatible Helvetica/Arial workalike, used because 's' is meant to
    read as Helvetica-derived, and actual Helvetica outline data is
    proprietary), and 'c'/'e', built directly from this master's own
    'o' (see `ring_derived.py`: a cut-open ring, guaranteeing their
    bowl/counter shape actually matches 'o's, not just an approximation
    of it) -- and applies the terminal-cut and round-counter
    modifications -- everything except serif feet. Arimo's own 's'
    terminal is close to horizontal but genuinely diagonal by design,
    and 'c'/'e's own terminals (the straight cuts closing their
    aperture) aren't quite horizontal either (Bezier subdivision at an
    exact angle doesn't land the cut flush), so all three go through
    `apply_terminal_cuts` too.
    """
    font = ufoLib2.Font()
    jost_names = jost_source.glyph_names_for_chars(CHARS)
    for ch in CHARS:
        if ch in _RING_DERIVED_CHARS:
            continue
        glyph = font.newGlyph(_glyph_name(ch))
        glyph.unicodes = [ord(ch)]
        if ch in _ARIMO_CHARS:
            pen_value, width = arimo_source.extract(ch, wght, wdth, grad)
        else:
            pen_value, width = jost_source.extract(jost_names[ch], wght, wdth, grad)
        jost_source.replay(glyph.getPen(), pen_value)
        glyph.width = width

    font["c"], _ = ring_derived.build_c_from_o(font["o"])
    font["e"], _ = ring_derived.build_e_from_o(font["o"])

    quirks.fix_y_crotch(font["y"])
    quirks.fix_six_nine_notch(font["six"])
    quirks.fix_six_nine_notch(font["nine"])

    for ch in CHARS:
        quirks.apply_terminal_cuts(font[_glyph_name(ch)])

    # Accented 'c'/'e'/'s' variants (see accent_marks.py): re-splice
    # Jost's own diacritic mark onto THIS project's own finished base
    # letter (after its terminal cut, above), replacing Jost's own
    # fused base+mark drawing wholesale -- otherwise every accented 'c'/
    # 'e'/'s' would carry Jost's own native shape for that letter
    # instead of this project's own ring-derived/Arimo-sourced one.
    for ch, base_ch in accent_marks.BASE_OF.items():
        if ch not in CHARS:
            continue
        base_glyph = font[_glyph_name(base_ch)]
        base_pen = RecordingPen()
        base_glyph.draw(base_pen)
        spliced = accent_marks.splice_mark(ch, wght, wdth, grad, base_pen.value)
        glyph = font[_glyph_name(ch)]
        glyph.clearContours()
        jost_source.replay(glyph.getPen(), spliced)
        glyph.width = base_glyph.width

    o_inner_points = _o_inner_contour(font["o"]).points
    for ch in CHARS:
        # Extends past the original 62: any accented Latin variant of
        # o/b/d/p/q/g (params.base_letter strips the diacritic) gets the
        # same counter-reshape as its base letter -- 'reshape_counter_to_o'
        # already matches purely by point-topology, not by name, so this
        # is just widening WHICH glyphs get offered to it, not new logic.
        # Non-Latin/unaccented characters (Cyrillic, digits, punctuation)
        # resolve to themselves and are skipped unless already a base name.
        if params.base_letter(ch) not in quirks.ROUND_COUNTER_GLYPHS:
            continue
        quirks.reshape_counter_to_o(font[_glyph_name(ch)], o_inner_points)

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
        if not glyph.contours:
            # 'space' (and any other whitespace-only glyph) has no ink
            # to grow a foot on at all.
            cache[ch] = ([], {})
            continue
        min_y = min(p.y for c in glyph.contours for p in c.points)
        guides = serifs.guides_for(ch, min_y)
        specs = serifs.detect_feet(glyph, guides, ch)
        cache[ch] = (specs, guides)
    _serif_reference_cache = cache
    return cache


def build_master_ufo(wght: int, wdth: int, serf: int, grad: int = 0) -> Path:
    font = _build_raw_glyphs(wght, wdth, grad)
    font.info.unitsPerEm = params.UPM
    font.info.ascender = params.ASCENDER
    font.info.descender = params.DESCENDER
    font.info.capHeight = params.CAP_HEIGHT
    font.info.xHeight = params.X_HEIGHT
    font.info.familyName = "Azrienoch V2"
    # A human name ("Regular", "Black Slab", ...), not `style_name`'s
    # technical `Wght900_Wdth75_Serf100` (still used for the UFO's own
    # folder name below) -- the DEFAULT master's `font.info` gets copied
    # into the compiled variable font's base name table (nameID 1/2/16/
    # 17) via its SourceDescriptor's `copyInfo=True`, so a technical
    # styleName here leaked straight into the font's actual family/style
    # name -- confirmed by dumping the compiled font's name table and
    # finding "Azrienoch V2 Wght400_Wdth100_Serf0" where "Azrienoch V2"/
    # "Regular" belonged.
    font.info.styleName = params.instance_style_name(wght, wdth, serf, grad)
    font.info.versionMajor = 0
    font.info.versionMinor = 1

    reference = _serif_reference()
    for ch in CHARS:
        specs, guides = reference[ch]
        serifs.apply_feet(font[_glyph_name(ch)], specs, guides, serf)

    for (left, right), value in kerning.pairs_for(wdth).items():
        font.kerning[(left, right)] = value

    path = SOURCES_DIR / f"AzrienochV2-{params.style_name(wght, wdth, serf, grad)}.ufo"
    font.save(path, overwrite=True)
    return path


def build_all() -> list[Path]:
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    return [build_master_ufo(wght, wdth, serf, grad) for wght, wdth, serf, grad in params.MASTER_GRID]


if __name__ == "__main__":
    for p in build_all():
        print(p)
