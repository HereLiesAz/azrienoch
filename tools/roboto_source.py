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
# Trimmed from Roboto Flex's original 13-axis release: `opsz` and `slnt` are
# pinned to their defaults (24, 0) and dropped, since Azrienoch never varies
# them (see params.py's module docstring for why) -- this instances them out
# with `fontTools.varLib.instancer` rather than leaving unused gvar/avar
# data sitting in every build. Shrinks the vendored file from ~1.78 MB to
# ~0.68 MB with no behavior change (Azrienoch's own `roboto_location()`
# always requested the same fixed opsz/slnt values from the untrimmed font).
ROBOTO_TTF = str(
    _HERE / "third_party" / "roboto-flex"
    / "RobotoFlex[GRAD,XOPQ,XTRA,YOPQ,YTAS,YTDE,YTFI,YTLC,YTUC,wdth,wght].ttf"
)

UPM = 2048  # Roboto Flex's unitsPerEm; Azrienoch keeps it to avoid rescaling.

# Roboto Flex's own axis extremes, at Azrienoch's wght masters (100/400/
# 700/900). The height/stroke axes (XOPQ, YOPQ, YTUC/YTLC/YTAS/YTDE/YTFI)
# push toward Roboto Flex's own extremes -- the "height as a matter of
# weight" mechanism. The 700 (Bold) sample isn't the linear midpoint
# between Regular and Black: height growth is front-loaded (most of it
# happens by Bold, tapering off toward Black) while stroke thickness
# keeps growing roughly proportionally, so the curve actually bends
# there instead of being two straight segments pretending to be one.
#
# XTRA (counter width, range 323-603) deliberately does NOT follow that
# same thin->thick progression: it's pushed wide at every weight, most
# pointedly at Black, where a typeface would normally let its counters
# get crowded out by ink. Refusing that trade -- keeping the void as
# prominent as the stroke even under the heaviest weight -- is the
# point: Azrienoch's counters are a considered shape, not leftover space.
_HEIGHT_AXES_AT_WGHT = {
    # XOPQ=45, not Roboto Flex's own floor of 27: at 27, the exclamation
    # mark's dot balloons into an oversized oval while every other dot
    # (i/j tittles, period, colon, question mark) stays a small fleck --
    # confirmed (via a headless-browser render, and a per-axis bisection
    # that isolated XOPQ as the only one of the eight axes responsible)
    # to be a bad interpolation corner in Roboto Flex's own exclam glyph
    # at its most extreme XOPQ value, not something Azrienoch's other
    # axis choices caused. 45 is comfortably clear of that corner (it
    # stays broken through ~40) while changing the overall Thin stroke
    # weight by an imperceptible amount -- verified side by side.
    100: dict(XOPQ=45, YOPQ=25, XTRA=420, YTUC=528, YTLC=416, YTAS=649, YTDE=-98, YTFI=560),
    # 175 and 250 each land exactly on the straight line the two points
    # bracketing them already defined (250 is the 100->400 segment's own
    # midpoint; once 250 existed, 175 is the 100->250 segment's own
    # midpoint in turn) -- neither is a separately-tuned design point,
    # both exist only so params.py::WGHT_MASTERS has explicit masters for
    # rotation_align.py/taper_align.py to anchor shorter Roboto Flex
    # extraction jumps to (see those modules' docstrings, and
    # params.py::WGHT_INSTANCE_MASTERS). Landing exactly on the
    # pre-existing line at each step means adding them changes nothing
    # about this curve's own shape -- `_lerp_piecewise` still returns the
    # same value anywhere from 100 to 400 it did before either entry
    # existed, including at 175 and 250 themselves.
    175: dict(XOPQ=58, YOPQ=38, XTRA=450, YTUC=574, YTLC=440, YTAS=674, YTDE=-124, YTFI=604),
    250: dict(XOPQ=70, YOPQ=52, XTRA=480, YTUC=620, YTLC=465, YTAS=700, YTDE=-150, YTFI=649),
    400: dict(XOPQ=96, YOPQ=79, XTRA=540, YTUC=712, YTLC=514, YTAS=750, YTDE=-203, YTFI=738),
    700: dict(XOPQ=145, YOPQ=113, XTRA=565, YTUC=748, YTLC=555, YTAS=820, YTDE=-270, YTFI=772),
    900: dict(XOPQ=175, YOPQ=135, XTRA=580, YTUC=760, YTLC=570, YTAS=854, YTDE=-305, YTFI=788),
}


def _lerp_piecewise(x, xs, ys):
    """Piecewise-linear interpolation across any number of sample points."""
    for i in range(len(xs) - 1):
        x0, x1 = xs[i], xs[i + 1]
        if x <= x1 or i == len(xs) - 2:
            t = 0.0 if x1 == x0 else (x - x0) / (x1 - x0)
            y0, y1 = ys[i], ys[i + 1]
            return y0 + (y1 - y0) * t
    raise AssertionError("unreachable")  # xs is non-empty by construction


def roboto_location(wght: float, wdth: float, grad: float = 0.0) -> dict:
    """The Roboto Flex axis location Azrienoch's (wght, wdth, GRAD) maps to."""
    wghts = P.WGHT_MASTERS
    height_axes = {}
    for tag in ("XOPQ", "YOPQ", "XTRA", "YTUC", "YTLC", "YTAS", "YTDE", "YTFI"):
        ys = tuple(_HEIGHT_AXES_AT_WGHT[w][tag] for w in wghts)
        height_axes[tag] = _lerp_piecewise(wght, wghts, ys)

    # Azrienoch wdth 75..100 (Condensed..Normal) -> Roboto Flex wdth 82..100:
    # a real but moderate condensation, short of Roboto's most extreme setting.
    w0, w1 = P.WDTH_MASTERS[0], P.WDTH_MASTERS[-1]
    t_wd = 0.0 if w1 == w0 else (wdth - w0) / (w1 - w0)
    roboto_wdth = 82.0 + (100.0 - 82.0) * t_wd

    # Azrienoch's GRAD passes straight through to Roboto Flex's own GRAD
    # (same units, degrees of grade) -- it's a narrower slice of Roboto's
    # full -200..150 range, since Azrienoch only needs a modest, safe
    # compensation swing rather than the extremes.
    #
    # No `slnt`/`opsz` keys here: the vendored font is pre-trimmed to those
    # two axes' defaults (see `ROBOTO_TTF` above), so they no longer exist
    # on it at all -- passing a value for an axis the font doesn't have
    # raises a KeyError in `instancer.instantiateVariableFont`.
    loc = dict(wght=float(wght), wdth=roboto_wdth, GRAD=float(grad))
    loc.update(height_axes)
    return loc


@functools.lru_cache(maxsize=None)
def _base_font() -> TTFont:
    return TTFont(ROBOTO_TTF)


@functools.lru_cache(maxsize=None)
def instantiate(wght: float, wdth: float, grad: float = 0.0) -> TTFont:
    """A fully static TTFont at the Roboto Flex location for (wght, wdth, GRAD)."""
    loc = roboto_location(wght, wdth, grad)
    base = _base_font()
    return instancer.instantiateVariableFont(base, loc, inplace=False)


@functools.lru_cache(maxsize=None)
def cmap_for(wght: float, wdth: float, grad: float = 0.0) -> dict:
    return instantiate(wght, wdth, grad).getBestCmap()


def glyph_name_for_char(wght: float, wdth: float, ch: str, grad: float = 0.0) -> str | None:
    return cmap_for(wght, wdth, grad).get(ord(ch))


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
