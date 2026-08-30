"""Azrienoch's letterform/spacing/kerning source: Roboto Flex.

Azrienoch does not draw its own letterforms from scratch. Roboto Flex
(OFL-1.1, https://github.com/googlefonts/roboto-flex) ships a compiled
variable font with thirteen axes, including nine "parametric" axes that
independently control stroke thickness and vertical proportions
(``XOPQ``/``YOPQ`` stroke weight, ``YTUC``/``YTLC``/``YTAS``/``YTDE``/
``YTFI`` cap/x/ascender/descender/figure height, ``XTRA`` counter width).
That is real, professionally hinted and kerned engineering -- reusing it
for the base letterforms and spacing means Azrienoch's own work can go
into what's actually new: coupling height to weight as a single lever
(Roboto Flex deliberately keeps them independent; Azrienoch deliberately
correlates them), a variable sans/serif axis Roboto Flex doesn't have, and
the horizontal/vertical-only terminal rule.

For each Azrienoch master we pick a *point* in Roboto Flex's axis space
(see ``roboto_location``), fully instantiate the variable font there
with ``fontTools.varLib.instancer`` (collapsing gvar/GPOS variation to a
static glyf/GPOS at that point), and extract glyph outlines, advance
widths and kerning straight out of the result.
"""

from __future__ import annotations

import functools
import pathlib

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

from tools import params as P

_HERE = pathlib.Path(__file__).resolve().parent.parent
ROBOTO_TTF = str(
    _HERE / "third_party" / "roboto-flex"
    / "RobotoFlex[GRAD,XOPQ,XTRA,YOPQ,YTAS,YTDE,YTFI,YTLC,YTUC,opsz,slnt,wdth,wght].ttf"
)

UPM = 2048  # Roboto Flex's unitsPerEm; Azrienoch keeps it to avoid rescaling.

# Roboto Flex's own axis extremes, at Azrienoch's wght masters (100/400/900).
# 400 uses Roboto Flex's authentic defaults; 100/900 push the parametric
# height and stroke axes to their extremes -- this is the whole "height as
# a matter of weight" mechanism, implemented on real engineered masters.
_HEIGHT_AXES_AT_WGHT = {
    100: dict(XOPQ=27, YOPQ=25, XTRA=344, YTUC=528, YTLC=416, YTAS=649, YTDE=-98, YTFI=560),
    400: dict(XOPQ=96, YOPQ=79, XTRA=468, YTUC=712, YTLC=514, YTAS=750, YTDE=-203, YTFI=738),
    900: dict(XOPQ=175, YOPQ=135, XTRA=400, YTUC=760, YTLC=570, YTAS=854, YTDE=-305, YTFI=788),
}


def _lerp3(x, xs, ys):
    x0, x1, x2 = xs
    y0, y1, y2 = ys
    if x <= x1:
        t = 0.0 if x1 == x0 else (x - x0) / (x1 - x0)
        return y0 + (y1 - y0) * t
    t = 0.0 if x2 == x1 else (x - x1) / (x2 - x1)
    return y1 + (y2 - y1) * t


def roboto_location(wght: float, wdth: float) -> dict:
    """The Roboto Flex axis location Azrienoch's (wght, wdth) maps to."""
    wghts = P.WGHT_MASTERS
    height_axes = {}
    for tag in ("XOPQ", "YOPQ", "XTRA", "YTUC", "YTLC", "YTAS", "YTDE", "YTFI"):
        ys = tuple(_HEIGHT_AXES_AT_WGHT[w][tag] for w in wghts)
        height_axes[tag] = _lerp3(wght, wghts, ys)

    # Azrienoch wdth 75..100 (Condensed..Normal) -> Roboto Flex wdth 82..100:
    # a real but moderate condensation, short of Roboto's most extreme setting.
    w0, w1 = P.WDTH_MASTERS[0], P.WDTH_MASTERS[-1]
    t_wd = 0.0 if w1 == w0 else (wdth - w0) / (w1 - w0)
    roboto_wdth = 82.0 + (100.0 - 82.0) * t_wd

    loc = dict(wght=float(wght), wdth=roboto_wdth, GRAD=0.0, slnt=0.0, opsz=24.0)
    loc.update(height_axes)
    return loc


@functools.lru_cache(maxsize=None)
def _base_font() -> TTFont:
    return TTFont(ROBOTO_TTF)


@functools.lru_cache(maxsize=None)
def instantiate(wght: float, wdth: float) -> TTFont:
    """A fully static TTFont at the Roboto Flex location for (wght, wdth)."""
    loc = roboto_location(wght, wdth)
    base = _base_font()
    return instancer.instantiateVariableFont(base, loc, inplace=False)


@functools.lru_cache(maxsize=None)
def cmap_for(wght: float, wdth: float) -> dict:
    return instantiate(wght, wdth).getBestCmap()


def glyph_name_for_char(wght: float, wdth: float, ch: str) -> str | None:
    return cmap_for(wght, wdth).get(ord(ch))


def extract_kerning(font: TTFont) -> dict[tuple[str, str], float]:
    """Decompile a (now-static) GPOS 'kern' feature into a flat pair dict.

    Handles both PairPos Format 1 (specific glyph pairs) and Format 2
    (class-based pairs, which is how most of Roboto Flex's kerning is
    actually stored) -- expanded out to a plain (left, right) -> value
    dict, which ``ufo_build.py`` then filters down to the glyphs Azrienoch
    actually imports and hands to a UFO's ``kerning`` mapping.
    """
    kerning: dict[tuple[str, str], float] = {}
    if "GPOS" not in font:
        return kerning
    gpos = font["GPOS"].table
    if gpos.FeatureList is None or gpos.LookupList is None:
        return kerning
    lookup_indices = set()
    for fr in gpos.FeatureList.FeatureRecord:
        if fr.FeatureTag == "kern":
            lookup_indices.update(fr.Feature.LookupListIndex)

    for li in lookup_indices:
        lookup = gpos.LookupList.Lookup[li]
        if lookup.LookupType != 2:  # PairPos only
            continue
        for st in lookup.SubTable:
            if st.Format == 1:
                for first, pairset in zip(st.Coverage.glyphs, st.PairSet):
                    for pvr in pairset.PairValueRecord:
                        x = getattr(pvr.Value1, "XAdvance", 0) if pvr.Value1 else 0
                        if x:
                            kerning[(first, pvr.SecondGlyph)] = x
            elif st.Format == 2:
                c1 = st.ClassDef1.classDefs
                c2 = st.ClassDef2.classDefs
                # Per the OpenType spec, class 0 is implicit: every glyph
                # not explicitly listed in ClassDef2 belongs to it. Building
                # class2_glyphs only from c2.items() (as an earlier version
                # of this function did) silently drops kerning for every
                # implicit-class-0 glyph the moment Class2Record[0] is ever
                # nonzero -- rebuild class 0 from the full glyph order.
                class2_glyphs: dict[int, list[str]] = {
                    0: [name for name in font.getGlyphOrder() if c2.get(name, 0) == 0]
                }
                for glyph, cls in c2.items():
                    if cls != 0:
                        class2_glyphs.setdefault(cls, []).append(glyph)
                for g1 in st.Coverage.glyphs:
                    c1v = c1.get(g1, 0)
                    if c1v >= len(st.Class1Record):
                        continue
                    for c2v, rec2 in enumerate(st.Class1Record[c1v].Class2Record):
                        x = getattr(rec2.Value1, "XAdvance", 0) if rec2.Value1 else 0
                        if x:
                            for g2 in class2_glyphs.get(c2v, []):
                                kerning[(g1, g2)] = x
    return kerning
