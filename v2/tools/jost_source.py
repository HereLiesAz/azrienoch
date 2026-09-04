"""Extracts real glyph outlines from the vendored Jost variable font.

Jost (SIL OFL 1.1, https://github.com/indestructible-type/Jost --
license copied to `v2/third_party/jost/OFL.txt`) is a real,
professionally drawn geometric sans. Per the project owner's direction,
this module takes its actual outlines as the starting point for v2's
letterforms -- the same way the repository root's own pipeline builds
from Roboto Flex -- rather than the from-scratch primitive
construction `geometry.py`/`glyphset.py` attempted first. Nothing here
is redrawn: `ufo_build.py` copies these outlines through as-is, and
Azrienoch's own modifications (Helvetica-inspired terminals/apertures,
axis behavior) are meant to be layered on top of this real data in
later passes.

Jost only exposes a `wght` axis (100-900) -- there is no `wdth` axis to
draw from. This module's width handling (`condense.condense_x`) is a
per-x compression profile derived from the glyph's own ink density, not
a true optically condensed redraw (no counter is actually reshaped) --
still a known simplification, see README.md, but no longer a flat
`x *= wf` scale: that thinned stems by the same factor it narrowed
counters, visibly uneven against horizontal strokes (untouched by any
X-axis scale) at heavy weight -- see `condense.py`'s own docstring.
"""

from __future__ import annotations

from pathlib import Path

from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

from . import condense

JOST_PATH = Path(__file__).resolve().parent.parent / "third_party" / "jost" / "Jost[wght].ttf"

_instance_cache: dict[int, TTFont] = {}


def _instance_at(wght: int) -> TTFont:
    if wght not in _instance_cache:
        font = TTFont(JOST_PATH)
        instantiateVariableFont(font, {"wght": wght}, inplace=True)
        _instance_cache[wght] = font
    return _instance_cache[wght]


def glyph_names_for_chars(chars: str) -> dict[str, str]:
    """Maps each character to Jost's own glyph name for it, via Jost's
    cmap (not assumed to equal the character itself, though for basic
    Latin it always does)."""
    font = _instance_at(400)
    cmap = font.getBestCmap()
    result = {}
    for ch in chars:
        cp = ord(ch)
        if cp not in cmap:
            raise KeyError(f"Jost has no glyph for {ch!r} (U+{cp:04X})")
        result[ch] = cmap[cp]
    return result


def extract(glyph_name: str, wght: int, wdth: int) -> tuple[list, float]:
    """Returns (pen_value, advance_width) for `glyph_name` at (wght, wdth).

    `pen_value` is a fontTools RecordingPen's `.value` -- a list of
    (operator, args) tuples, replayable onto another pen via `replay`.
    `wdth` != 100 runs `condense.condense_x` (see module docstring);
    coordinates are rounded to integers same as any font's units must be.
    """
    font = _instance_at(wght)
    glyph_set = font.getGlyphSet()
    if glyph_name not in glyph_set:
        raise KeyError(f"Jost has no glyph named {glyph_name!r}")

    # DecomposingRecordingPen, not a plain RecordingPen: a handful of
    # Jost's own accented Latin-Extended-A glyphs (e.g. Ohungarumlaut,
    # uni0162) are TrueType composites (a base letter + a separately
    # drawn diacritic component), which a plain RecordingPen just
    # records as an opaque addComponent call instead of actual point
    # data -- confirmed directly: condense_x crashed trying to treat a
    # component's own (glyph name, transform) args as an (x, y) point.
    # Decomposing here means every downstream consumer of this pen
    # value (condense_x, quirks.py, ring_derived.py) only ever sees
    # plain move/line/qCurve commands, never a component reference.
    pen = DecomposingRecordingPen(glyph_set)
    glyph_set[glyph_name].draw(pen)
    width = glyph_set[glyph_name].width

    value, width = condense.condense_x(pen.value, width, wdth / 100.0)
    rounded = [(op, tuple(None if pt is None else (round(pt[0]), round(pt[1])) for pt in args)) for op, args in value]
    if wdth != 100:
        _match_closing_duplicates(rounded, _reference_closing_state(glyph_name, wght))
    return rounded, width


_closing_state_cache: dict[tuple[str, int], list] = {}


def _reference_closing_state(glyph_name: str, wght: int) -> list:
    """This glyph's own per-contour "does the last point exactly
    duplicate the first" state, at `wght`/wdth=100 (uncondensed) --
    the ground truth `_match_closing_duplicates` corrects any condensed
    master back to matching, see that function's own docstring."""
    key = (glyph_name, wght)
    if key not in _closing_state_cache:
        pen_value, _ = extract(glyph_name, wght, 100)
        _closing_state_cache[key] = _closing_duplicate_state(pen_value)
    return _closing_state_cache[key]


def _closing_duplicate_state(pen_value: list) -> list:
    """[bool, ...], one per contour in order: whether that contour's
    last explicit on-curve point (the single command immediately before
    its own closePath, if that command has one -- a qCurveTo whose own
    trailing arg is `None` doesn't, its close is already implicit)
    exactly duplicates its first point (`moveTo`'s own point)."""
    result = []
    first = None
    start_idx = None
    for i, (op, args) in enumerate(pen_value):
        if op == "moveTo":
            first = args[0]
            start_idx = i
        elif op == "closePath" and first is not None and start_idx is not None:
            last_pt = None
            if i - 1 > start_idx:
                pop, pargs = pen_value[i - 1]
                if pop in ("lineTo", "qCurveTo") and pargs and pargs[-1] is not None:
                    last_pt = pargs[-1]
            result.append(last_pt is not None and last_pt == first)
            first = None
            start_idx = None
    return result


def _match_closing_duplicates(pen_value: list, reference_state: list) -> None:
    """Corrects `pen_value` (in place) so each contour's own "does the
    last point duplicate the first" state matches `reference_state`'s,
    contour for contour -- nudging the last point 1 unit off the first
    if the reference says they shouldn't coincide but rounding made
    them anyway, or snapping it exactly onto the first if the reference
    says they should but rounding missed by a unit.

    `SegmentToPointPen` (what `replay` ultimately feeds into, via
    ufoLib2's `glyph.getPen()`) silently DROPS a last point that's an
    exact on-curve duplicate of the first -- correct, standalone
    behavior (many contours, like 'o's own, are intentionally drawn
    that way at every weight), but not safe to leave to chance across a
    whole designspace: `condense_x`'s squish can round two DIFFERENT
    coordinates onto the same integer at one master and not another,
    flipping this state for a glyph that wasn't intentionally drawn
    with a duplicate closing point -- confirmed directly (a diacritic
    mark on 'Ĭ': 18 points at every master except 17 at wght=100/
    wdth=75) -- which fontmake requires to be identical across the
    whole designspace to compile a variable font at all. Comparing
    against this SAME glyph's own wdth=100 (uncondensed) state, rather
    than a flat "never allow this" rule, is what keeps contours like
    'o's -- genuinely, consistently closed with a duplicate point at
    every weight and width -- untouched."""
    idx = 0
    first = None
    start_idx = None
    for i, (op, args) in enumerate(pen_value):
        if op == "moveTo":
            first = args[0]
            start_idx = i
        elif op == "closePath" and first is not None and start_idx is not None:
            last_idx, last_pt = None, None
            if i - 1 > start_idx:
                pop, pargs = pen_value[i - 1]
                if pop in ("lineTo", "qCurveTo") and pargs and pargs[-1] is not None:
                    last_idx, last_pt = i - 1, pargs[-1]
            if last_pt is not None and idx < len(reference_state):
                is_dup = last_pt == first
                should_be_dup = reference_state[idx]
                if is_dup and not should_be_dup:
                    new_pt = (last_pt[0] + 1, last_pt[1])
                elif not is_dup and should_be_dup:
                    new_pt = first
                else:
                    new_pt = None
                if new_pt is not None:
                    pop, pargs = pen_value[last_idx]
                    pen_value[last_idx] = (pop, pargs[:-1] + (new_pt,))
            idx += 1
            first = None
            start_idx = None


def replay(pen, pen_value: list) -> None:
    for op, args in pen_value:
        getattr(pen, op)(*args)
