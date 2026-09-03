"""Builds one UFO per master in params.MASTER_GRID, glyphs drawn straight
from glyphset.py -- no imported font, nothing decompiled or extracted."""

from __future__ import annotations

from pathlib import Path

import ufoLib2

from . import params
from .glyphset import GLYPHS

SOURCES_DIR = Path(__file__).resolve().parent.parent / "sources"


def build_master_ufo(wght: int, wdth: int) -> Path:
    m = params.metrics_for(wght, wdth)
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

    for name, (codepoint, draw) in GLYPHS.items():
        glyph = font.newGlyph(name)
        glyph.unicodes = [codepoint]
        pen = glyph.getPen()
        width = draw(pen, m)
        glyph.width = width

    path = SOURCES_DIR / f"AzrienochV2-{params.style_name(wght, wdth)}.ufo"
    font.save(path, overwrite=True)
    return path


def build_all() -> list[Path]:
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    return [build_master_ufo(wght, wdth) for wght, wdth in params.MASTER_GRID]


if __name__ == "__main__":
    for p in build_all():
        print(p)
