"""Build Azrienoch's UFO masters + designspace from Roboto Flex.

For each (wght, wdth, SERF) master in ``params.master_grid()``: instance
Roboto Flex at the corresponding location (``roboto_source.py``), copy
over the Core Latin MVP glyph set's outlines/advances/kerning. Every
master -- SERF=0 included -- gets the same fixed set of foot contours per
glyph (``serifs.py``), sized by that master's own SERF value; that keeps
every master of a glyph topologically identical, which ``fontmake``
requires to interpolate it at all. ``fontmake`` then compiles the result
into one variable TTF.
"""

from __future__ import annotations

import pathlib

import ufoLib2
from fontTools.pens.recordingPen import DecomposingRecordingPen

from tools import params as P
from tools import roboto_source as R
from tools import serifs as S

UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
LOWER = "abcdefghijklmnopqrstuvwxyz"
DIGITS = "0123456789"
PUNCT = " .,:;!?'\"()-–—/&@#*+=%·[]"

CORE_CHARS = UPPER + LOWER + DIGITS + PUNCT

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


def _font_info(ufo: ufoLib2.Font, inst, wght, wdth, serf):
    os2 = inst["OS/2"]
    hhea = inst["hhea"]
    fi = ufo.info
    fi.unitsPerEm = R.UPM
    fi.ascender = hhea.ascender
    fi.descender = hhea.descender
    fi.capHeight = os2.sCapHeight
    fi.xHeight = os2.sxHeight
    fi.familyName = "Azrienoch"
    fi.styleName = P.master_name(wght, wdth, serf)
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


def compute_reference_feet() -> dict[str, list[dict]]:
    """Foot specs per glyph name, detected once from the (400, 100) instance."""
    inst = R.instantiate(REFERENCE_WGHT, REFERENCE_WDTH)
    glyphset = inst.getGlyphSet()
    hmtx = inst["hmtx"]
    cmap = R.cmap_for(REFERENCE_WGHT, REFERENCE_WDTH)
    os2, hhea = inst["OS/2"], inst["hhea"]
    guides = _guides(os2.sCapHeight, os2.sxHeight, hhea.ascender, hhea.descender)

    feet_by_glyph = {}
    for ch in CORE_CHARS:
        gname = cmap.get(ord(ch))
        if gname is None or gname in feet_by_glyph:
            continue
        glyph = _extract_glyph(gname, glyphset, hmtx, ord(ch))
        feet_by_glyph[gname] = S.detect_feet(glyph, guides)
    return feet_by_glyph


def build_master_ufo(wght, wdth, serf, feet_by_glyph) -> ufoLib2.Font:
    inst = R.instantiate(wght, wdth)
    glyphset = inst.getGlyphSet()
    hmtx = inst["hmtx"]
    cmap = R.cmap_for(wght, wdth)

    ufo = ufoLib2.Font()
    _font_info(ufo, inst, wght, wdth, serf)
    guides = _guides(ufo.info.capHeight, ufo.info.xHeight, ufo.info.ascender, ufo.info.descender)

    imported_names = set()

    notdef = _extract_glyph(".notdef", glyphset, hmtx, None)
    ufo[".notdef"] = notdef
    imported_names.add(".notdef")

    for ch in CORE_CHARS:
        gname = cmap.get(ord(ch))
        if gname is None:
            continue
        glyph = _extract_glyph(gname, glyphset, hmtx, ord(ch))
        S.apply_feet(glyph, feet_by_glyph.get(gname, []), guides, serf)
        ufo[gname] = glyph
        imported_names.add(gname)

    raw_kerning = R.extract_kerning(inst)
    kerning = {
        pair: value
        for pair, value in raw_kerning.items()
        if pair[0] in imported_names and pair[1] in imported_names
    }
    ufo.kerning.update(kerning)

    return ufo


def build_all():
    SOURCES_DIR.mkdir(exist_ok=True)
    feet_by_glyph = compute_reference_feet()
    paths = {}
    for wght, wdth, serf in P.master_grid():
        ufo = build_master_ufo(wght, wdth, serf, feet_by_glyph)
        name = P.master_name(wght, wdth, serf)
        path = SOURCES_DIR / f"Azrienoch-{name}.ufo"
        ufo.save(path, overwrite=True)
        paths[(wght, wdth, serf)] = path
        print("wrote", path, "glyphs:", len(ufo), "kerning pairs:", len(ufo.kerning))
    return paths


if __name__ == "__main__":
    build_all()
