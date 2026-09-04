"""Greek letterform source for Azrienoch v2: the repository root's own
vendored Roboto Flex (SIL OFL 1.1, already present at
`third_party/roboto-flex/`, license at `third_party/roboto-flex/OFL.txt`)
-- not a new donor font. Jost, v2's own primary donor for everything
else, has almost no Greek coverage (4 codepoints total, confirmed
directly against its own cmap), so Greek needs a separate source; the
repository root's own v1 pipeline already solved exactly this problem
for its own (different) design by sourcing ALL of its letterforms from
Roboto Flex, including Greek.

Rather than re-deriving a second solution to "how do you get a
reasonable per-weight stroke/height progression out of Roboto Flex's
independent parametric axes" (`XOPQ`/`YOPQ` stroke weight, `XTRA`
counter width, `YTUC`/`YTLC`/`YTAS`/`YTDE`/`YTFI` vertical proportions
-- none of which move automatically with `wght` the way a normal
single-axis variable font's stroke would, since Roboto Flex deliberately
keeps them independent axes), this module reuses the root pipeline's
own already-tuned `tools/roboto_source.py::roboto_location` wholesale,
via a plain read-only import -- v1's own files are never modified. v2's
own `wdth` (75-100) and `GRAD` (-50 to 50) ranges happen to be numerically
identical to v1's own (confirmed directly against `tools/params.py`),
so both pass straight through with no rescaling; only `wght` needs a
floor clamp (see `_ROBOTO_WGHT_FLOOR` below).

Greek glyphs sourced this way necessarily look like Roboto Flex's own
grotesque design, not Jost's geometric one -- a real, visible style
seam against the Latin/Cyrillic alphabet, the same class of tradeoff
already made for 's' (Arimo/Helvetica-derived, see `arimo_source.py`)
rather than a defect unique to this module. No Azrienoch-specific
modification (terminal cuts, round-counter reshaping, serif feet) is
applied to Greek glyphs -- see `ufo_build.py`'s own module docstring.
"""

from __future__ import annotations

from fontTools.pens.recordingPen import DecomposingRecordingPen

from tools.roboto_source import instantiate

# v1's own WGHT_MASTERS floor (see that module's own `_HEIGHT_AXES_AT_WGHT`
# comment): every weight below 180 was confirmed, repeatedly, to
# self-intersect somewhere in Roboto Flex's own gvar deltas at this
# combination of axes -- a font-data limitation, not something specific
# to v1's own design, and not worth re-litigating here. v2's own `wght`
# floor (100) is clamped up to it before handing off, rather than
# extrapolating `roboto_location`'s piecewise table past its first
# sample point (which produces exactly that same self-intersection).
_ROBOTO_WGHT_FLOOR = 180


def _clamped_wght(wght: float) -> float:
    return max(_ROBOTO_WGHT_FLOOR, wght)


def glyph_names_for_chars(chars: str) -> dict[str, str]:
    """Maps each character to Roboto Flex's own glyph name for it, via
    its cmap (not assumed to equal the character itself)."""
    font = instantiate(400, 100, 0.0)
    cmap = font.getBestCmap()
    result = {}
    for ch in chars:
        cp = ord(ch)
        if cp not in cmap:
            raise KeyError(f"Roboto Flex has no glyph for {ch!r} (U+{cp:04X})")
        result[ch] = cmap[cp]
    return result


def extract(glyph_name: str, wght: int, wdth: int, grad: int = 0) -> tuple[list, float]:
    """Returns (pen_value, advance_width) for `glyph_name` at
    (wght, wdth, grad), decomposing any composite (Roboto Flex, like
    Jost, draws some accented/composite glyphs as base-plus-mark
    components) so every downstream consumer only ever sees plain
    outline data."""
    font = instantiate(_clamped_wght(wght), wdth, float(grad))
    glyph_set = font.getGlyphSet()
    pen = DecomposingRecordingPen(glyph_set)
    glyph_set[glyph_name].draw(pen)
    width = glyph_set[glyph_name].width
    return pen.value, width
