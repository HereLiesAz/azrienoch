"""Build Azrienoch's UFO masters + designspace from Roboto Flex.

For each (wght, wdth, SERF, GRAD) master in ``params.master_grid()``: instance
Roboto Flex at the corresponding location (``roboto_source.py``), copy
over ``CORE_CHARS``' outlines/advances/kerning, and apply the 'G'/'R'
quirks (``quirks.py``). Every master -- SERF=0 included -- gets the same
fixed set of foot contours per glyph (``serifs.py``), sized by that
master's own SERF value; that keeps every master of a glyph
topologically identical, which ``fontmake`` requires to interpolate it
at all. ``fontmake`` then compiles the result into one variable TTF.
"""

from __future__ import annotations

import pathlib

import ufoLib2
from fontTools.pens.recordingPen import DecomposingRecordingPen

from tools import dots as D
from tools import params as P
from tools import quirks as Q
from tools import roboto_source as R
from tools import round_contrast as RC
from tools import serifs as S
from tools import single_story_a as A

ROUND_CONTRAST_CHARS = {"o", "c"}

UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
LOWER = "abcdefghijklmnopqrstuvwxyz"
DIGITS = "0123456789"
PUNCT = " .,:;!?'\"()-–—/&@#*+=%·[]"

# Latin-1 Supplement: Western European accented letters (French, German,
# Spanish, Portuguese, Italian, Scandinavian, ...) plus a few punctuation
# marks (inverted !/?, degree, micro).
LATIN1 = (
    "ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞß"
    "àáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ"
    "¡¿°µ"
)

# Latin Extended-A: Central/Eastern European and Baltic accented letters
# (Polish, Czech, Slovak, Hungarian, Romanian, Turkish, Baltic languages).
LATIN_EXT_A = (
    "ĀāĂăĄąĆćĈĉĊċČčĎďĐđĒēĔĕĖėĘęĚěĜĝĞğĠġĢģĤĥĦħĨĩĪīĬĭĮįİıĲĳĴĵĶķ"
    "ĹĺĻļĽľŁłŃńŅņŇňŌōŎŏŐőŒœŔŕŖŗŘřŚśŜŝŞşŠšŢţŤťŨũŪūŬŭŮůŰűŲųŴŵŶŷŸŹźŻżŽž"
)

# Greek and Coptic: the modern monotonic Greek alphabet, upper- and
# lowercase (including final-form sigma 'ς', distinct from medial 'σ'),
# plus the tonos-accented and dialytika (diaeresis) vowels.
GREEK = (
    "ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ"
    "αβγδεζηθικλμνξοπρστυφχψω"
    "ςΆΈΉΊΌΎΏάέήίόύώΪΫϊϋΐΰ"
)

# Cyrillic: the modern Russian alphabet, upper- and lowercase, including
# 'Ё'/'ё'.
CYRILLIC = (
    "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
    "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
)

CORE_CHARS = UPPER + LOWER + DIGITS + PUNCT + LATIN1 + LATIN_EXT_A + GREEK + CYRILLIC

HERE = pathlib.Path(__file__).resolve().parent.parent
SOURCES_DIR = HERE / "sources"

REFERENCE_WGHT, REFERENCE_WDTH = 400, 100


def _copy_outline(ufo_glyph, tt_glyph, glyphset):
    """Copy a Roboto Flex (TrueType, quadratic) glyph's outline in as-is.

    Composite glyphs (e.g. '%', built from 'zerosuperior' + 'uni2044'
    components) are decomposed against Roboto Flex's *own* full
    glyphset: those component glyphs exist there even though Azrienoch
    doesn't import them as standalone characters, so drawing straight
    into our UFO's pen would leave a dangling component reference to a
    glyph our font doesn't have. ``DecomposingRecordingPen`` resolves
    that first, so what lands in the UFO is always plain contours.

    Otherwise, no curve conversion: the SERF axis (``serifs.py``) only
    ever adds plain rectangle contours alongside the imported outline --
    it never reshapes the outline itself -- so there's no reason to touch
    the quadratic points Roboto Flex's own gvar already guarantees are
    topologically identical across every master. A conversion step
    (cubic or otherwise) risks picking a different point count on
    different masters if it isn't perfectly deterministic, which silently
    breaks interpolation between them.
    """
    rec = DecomposingRecordingPen(glyphset)
    tt_glyph.draw(rec)
    rec.replay(ufo_glyph.getPen())


def _guides(cap_height, x_height, ascender, descender):
    return {
        "baseline": 0.0,
        "xheight": x_height,
        "capheight": cap_height,
        "ascender": ascender,
        "descender": descender,
    }


COPYRIGHT = (
    "Copyright 2011 The Roboto Flex Project Authors "
    "(https://github.com/googlefonts/roboto-flex). "
    "Copyright 2026 The Azrienoch Project Authors."
)
LICENSE = (
    "This Font Software is licensed under the SIL Open Font License, "
    "Version 1.1. This license is available with a FAQ at: "
    "http://scripts.sil.org/OFL"
)
LICENSE_URL = "http://scripts.sil.org/OFL"


def _font_info(ufo: ufoLib2.Font, inst, wght, wdth, serf, grad):
    os2 = inst["OS/2"]
    hhea = inst["hhea"]
    fi = ufo.info
    fi.unitsPerEm = R.UPM
    fi.ascender = hhea.ascender
    fi.descender = hhea.descender
    fi.capHeight = os2.sCapHeight
    fi.xHeight = os2.sxHeight
    fi.familyName = "Azrienoch"
    fi.styleName = P.master_name(wght, wdth, serf, grad)
    fi.versionMajor, fi.versionMinor = 1, 0
    # A distributed .ttf carries its own copyright/license -- OFL clause 2
    # requires each copy to include the license, and a copy of the raw
    # binary distributed apart from this repo's OFL.txt would otherwise
    # have nothing machine-readable to point to.
    fi.copyright = COPYRIGHT
    fi.openTypeNameLicense = LICENSE
    fi.openTypeNameLicenseURL = LICENSE_URL
    return fi


def _extract_glyph(gname, glyphset, hmtx, unicode_val):
    glyph = ufoLib2.objects.Glyph(name=gname)
    _copy_outline(glyph, glyphset[gname], glyphset)
    glyph.width = hmtx[gname][0]
    if unicode_val is not None:
        glyph.unicodes = [unicode_val]
    return glyph


def _prop_glyph_name(gname: str, glyphset) -> str | None:
    """Roboto Flex's alternate proportional-figure glyph for a digit, if any."""
    prop = gname + ".prop"
    return prop if prop in glyphset else None


def _extract_char_glyph(ch, gname, glyphset, hmtx, cmap, xheight):
    """The base outline for character `ch` (named `gname`), before
    quirks/dots/feet. Every character reuses Roboto Flex's own glyph
    unmodified except 'a' -- see single_story_a.py."""
    if ch == "a":
        d_gname = cmap.get(ord("d"))
        if d_gname is not None:
            d_glyph = _extract_glyph(d_gname, glyphset, hmtx, None)
            return A.build_from_d(d_glyph, xheight)
    return _extract_glyph(gname, glyphset, hmtx, ord(ch))


def compute_reference_specs() -> tuple[dict[str, list[dict]], dict[str, list[int]]]:
    """Foot specs (``serifs.py``) and dot-contour indices (``dots.py``) per
    glyph name, both detected once from the (400, 100) instance and
    reapplied identically on every master -- see those modules'
    docstrings for why detecting once and reusing by index/fraction,
    rather than redetecting per master, is what keeps every master of a
    glyph topologically identical."""
    inst = R.instantiate(REFERENCE_WGHT, REFERENCE_WDTH)
    glyphset = inst.getGlyphSet()
    hmtx = inst["hmtx"]
    cmap = R.cmap_for(REFERENCE_WGHT, REFERENCE_WDTH)
    os2, hhea = inst["OS/2"], inst["hhea"]
    guides = _guides(os2.sCapHeight, os2.sxHeight, hhea.ascender, hhea.descender)

    feet_by_glyph = {}
    dots_by_glyph = {}
    for ch in CORE_CHARS:
        gname = cmap.get(ord(ch))
        if gname is None or gname in feet_by_glyph:
            continue
        glyph = _extract_char_glyph(ch, gname, glyphset, hmtx, cmap, guides["xheight"])
        Q.apply_quirks(ch, glyph)
        if ch in ROUND_CONTRAST_CHARS:
            RC.thin_round(glyph)
        feet_by_glyph[gname] = S.detect_feet(glyph, guides)
        dots_by_glyph[gname] = D.detect_dot_contours(glyph)

        prop_name = _prop_glyph_name(gname, glyphset)
        if prop_name is not None and prop_name not in feet_by_glyph:
            prop_glyph = _extract_glyph(prop_name, glyphset, hmtx, None)
            feet_by_glyph[prop_name] = S.detect_feet(prop_glyph, guides)
            dots_by_glyph[prop_name] = D.detect_dot_contours(prop_glyph)
    return feet_by_glyph, dots_by_glyph


def build_master_ufo(wght, wdth, serf, grad, feet_by_glyph, dots_by_glyph) -> ufoLib2.Font:
    inst = R.instantiate(wght, wdth, grad)
    glyphset = inst.getGlyphSet()
    hmtx = inst["hmtx"]
    cmap = R.cmap_for(wght, wdth, grad)

    ufo = ufoLib2.Font()
    _font_info(ufo, inst, wght, wdth, serf, grad)
    guides = _guides(ufo.info.capHeight, ufo.info.xHeight, ufo.info.ascender, ufo.info.descender)
    dot_factor = D.boost_factor_for_wght(wght)

    # The true height ascender letters (h/d/b/k/l) actually reach -- not
    # `guides["ascender"]` (`hhea.ascender`), which is line-spacing
    # padding, well above any real glyph -- measured off 'h' itself so
    # `reposition_tittle` can align 'i'/'j' to it (see dots.py).
    h_gname = cmap.get(ord("h"))
    ascender_height = None
    if h_gname is not None:
        h_glyph = _extract_glyph(h_gname, glyphset, hmtx, None)
        ascender_height = max(p.y for c in h_glyph.contours for p in c.points)

    imported_names = set()

    notdef = _extract_glyph(".notdef", glyphset, hmtx, None)
    ufo[".notdef"] = notdef
    imported_names.add(".notdef")

    prop_subs: dict[str, str] = {}
    for ch in CORE_CHARS:
        gname = cmap.get(ord(ch))
        if gname is None:
            continue
        glyph = _extract_char_glyph(ch, gname, glyphset, hmtx, cmap, guides["xheight"])
        Q.apply_quirks(ch, glyph)
        if ch in ROUND_CONTRAST_CHARS:
            RC.thin_round(glyph)
        D.boost_dots(glyph, dots_by_glyph.get(gname, []), dot_factor)
        if ch in D.TITTLE_CHARS and ascender_height is not None:
            D.reposition_tittle(glyph, dots_by_glyph.get(gname, []), ascender_height)
        S.apply_feet(glyph, feet_by_glyph.get(gname, []), guides, serf)
        ufo[gname] = glyph
        imported_names.add(gname)

        prop_name = _prop_glyph_name(gname, glyphset)
        if prop_name is not None:
            prop_glyph = _extract_glyph(prop_name, glyphset, hmtx, None)
            D.boost_dots(prop_glyph, dots_by_glyph.get(prop_name, []), dot_factor)
            S.apply_feet(prop_glyph, feet_by_glyph.get(prop_name, []), guides, serf)
            ufo[prop_name] = prop_glyph
            imported_names.add(prop_name)
            prop_subs[gname] = prop_name

    if prop_subs:
        # Roboto Flex's own `pnum` (proportional figures) GSUB feature:
        # default figures are tabular (fixed-width, for columns of numbers),
        # this substitutes in Roboto Flex's alternate proportional-width
        # digit outlines when the feature is enabled.
        subs = "\n".join(f"    sub {a} by {b};" for a, b in sorted(prop_subs.items()))
        ufo.features.text = f"feature pnum {{\n{subs}\n}} pnum;\n"

    raw_kerning = R.extract_kerning(inst)

    # 'a' is now built from 'd's own outline (single_story_a.py) -- its
    # left edge (the bowl) and right edge (the stem, up to x-height) are
    # geometrically identical to 'd's, so its kerning should be too.
    # Roboto Flex's own pairs for 'a' were tuned for the old double-story
    # shape; overwrite them with 'd's pairs in both positions rather than
    # keep pairs tuned for a shape 'a' no longer has.
    a_gname, d_gname = cmap.get(ord("a")), cmap.get(ord("d"))
    if a_gname is not None and d_gname is not None:
        for (left, right), value in list(raw_kerning.items()):
            if left == d_gname:
                raw_kerning[(a_gname, right)] = value
            if right == d_gname:
                raw_kerning[(left, a_gname)] = value
        if (d_gname, d_gname) in raw_kerning:
            raw_kerning[(a_gname, a_gname)] = raw_kerning[(d_gname, d_gname)]

    kerning = {
        pair: value
        for pair, value in raw_kerning.items()
        if pair[0] in imported_names and pair[1] in imported_names
    }
    ufo.kerning.update(kerning)

    return ufo


def build_all():
    SOURCES_DIR.mkdir(exist_ok=True)
    feet_by_glyph, dots_by_glyph = compute_reference_specs()
    paths = {}
    for wght, wdth, serf, grad in P.master_grid():
        ufo = build_master_ufo(wght, wdth, serf, grad, feet_by_glyph, dots_by_glyph)
        name = P.master_name(wght, wdth, serf, grad)
        path = SOURCES_DIR / f"Azrienoch-{name}.ufo"
        ufo.save(path, overwrite=True)
        paths[(wght, wdth, serf, grad)] = path
        print("wrote", path, "glyphs:", len(ufo), "kerning pairs:", len(ufo.kerning))
    return paths


if __name__ == "__main__":
    build_all()
