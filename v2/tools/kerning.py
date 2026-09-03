"""Letter-pair kerning for Azrienoch v2, extracted from vendored Jost's
own GPOS pair-positioning table (SIL OFL 1.1) rather than hand-tuned --
the same "borrow it from a real, professionally-kerned donor font"
approach `roboto_source.py::extract_kerning` uses for the repository
root's own v1 pipeline, and for the same reason: getting several
thousand pairs to look right by eye is its own multi-week type-design
task, and Jost already did that work.

Jost's kerning turns out to be entirely static across its own `wght`
axis -- every one of its 11,597 class-kerning pairs (confirmed by
diffing the full extracted table at wght=100/400/900: zero pairs
differ) has the same value at Thin as at Black, so there's no
per-master extraction to do the way `jost_source.extract` re-samples
outlines at each `wght`: one extraction, reused at every master, scaled
only by that master's own `wdth` fraction (kerning has no direct
`SERF`-axis dependence either -- a slab foot changes a stem's terminal,
not the sidebearing space two letters share).

Filtered down to pairs where BOTH sides are one of Azrienoch's own 62
glyphs (letters + digits) -- Jost has hundreds of accented and Cyrillic
glyphs with kerning of their own that's irrelevant here -- 533 pairs
survive that filter, extracted from a single class-kerning (GPOS
lookup format 2) subtable; Jost has no format-1 (glyph-to-glyph)
kerning pairs at all.

Three simplifications, same spirit as the `wdth` axis's own documented
placeholder (see `condense.py`):

- `c`/`e`/`s` are sourced from Arimo, not Jost (see `arimo_source.py`),
  but keep Jost's own kerning values for pairs involving them -- their
  Arimo shapes are close enough in overall proportion (a round bowl, a
  round bowl, a curved spine) that Jost's own numbers are a reasonable
  stand-in, the same donor-kerning-as-approximation logic the whole
  module rests on, rather than leaving them unkerned entirely.
- `a` is built from `d`'s own contours, not Jost's separately-drawn
  'a' (see `single_story_a.py`) -- so its kerning is `d`'s too, not the
  pairs Jost placed under its own, differently-shaped 'a'. Every pair
  this module pulls in keyed to Jost's native 'a' is dropped and
  replaced with `d`'s own pairs, remapped to `a`, in both positions.
  Jost's own 'd' happens to carry no class-kerning pairs at all, so
  this leaves 'a' unkerned too -- the more consistent outcome, given
  it now shares 'd's exact shape, rather than keeping a borrowed
  approximation from a different letterform. Ported from the
  repository root's own v1 kerning pipeline (see its own README), which
  does the same `d`-not-`a` substitution for the same reason.
- Kerning is scaled by `wdth`'s own fraction (75/100 -> 0.75) but not by
  `condense.py`'s own per-glyph ink-density warp -- kerning is a single
  scalar correction between two specific letters, not an outline, so
  there's no per-x profile to weight it by; a flat scale is the
  reasonable analogue of `condense.py`'s overall compression without
  redoing its full analysis for every pair.
"""

from __future__ import annotations

import string

from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

from . import jost_source

JOST_PATH = jost_source.JOST_PATH
CHARS = string.ascii_uppercase + string.ascii_lowercase + string.digits
_DIGIT_NAMES = {
    "0": "zero", "1": "one", "2": "two", "3": "three", "4": "four",
    "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine",
}


def _glyph_name(ch: str) -> str:
    return _DIGIT_NAMES.get(ch, ch)


def _extract_jost_class_pairs() -> dict[tuple[str, str], int]:
    """Every (glyph1, glyph2) -> xAdvance pair from Jost's own GPOS
    lookup, in Jost's own glyph names, confirmed identical at every
    `wght` (see module docstring) so a single wght=400 sample suffices."""
    font = TTFont(JOST_PATH)
    instantiateVariableFont(font, {"wght": 400}, inplace=True)
    if "GPOS" not in font:
        return {}
    pairs: dict[tuple[str, str], int] = {}
    for lookup in font["GPOS"].table.LookupList.Lookup:
        if lookup.LookupType != 2:
            continue
        for sub in lookup.SubTable:
            if sub.Format == 1:
                for i, glyph1 in enumerate(sub.Coverage.glyphs):
                    for rec in sub.PairSet[i].PairValueRecord:
                        value = rec.Value1.XAdvance if rec.Value1 else 0
                        if value:
                            pairs[(glyph1, rec.SecondGlyph)] = value
            elif sub.Format == 2:
                class1_glyphs: dict[int, list[str]] = {}
                for g, c in sub.ClassDef1.classDefs.items():
                    class1_glyphs.setdefault(c, []).append(g)
                class2_glyphs: dict[int, list[str]] = {}
                for g, c in sub.ClassDef2.classDefs.items():
                    class2_glyphs.setdefault(c, []).append(g)
                for c1, class1rec in enumerate(sub.Class1Record):
                    for c2, class2rec in enumerate(class1rec.Class2Record):
                        value = class2rec.Value1.XAdvance if class2rec.Value1 else 0
                        if not value:
                            continue
                        for g1 in class1_glyphs.get(c1, []):
                            for g2 in class2_glyphs.get(c2, []):
                                pairs[(g1, g2)] = value
    return pairs


_base_pairs_cache: dict[tuple[str, str], int] | None = None


def _base_pairs() -> dict[tuple[str, str], int]:
    """{(our_glyph_name, our_glyph_name): xAdvance}, filtered to
    Azrienoch's own 62 glyphs and with 'a' mirroring every 'd' pair
    (see module docstring)."""
    global _base_pairs_cache
    if _base_pairs_cache is not None:
        return _base_pairs_cache

    jost_names = jost_source.glyph_names_for_chars(CHARS)
    jost_to_ours = {jost_names[ch]: _glyph_name(ch) for ch in CHARS}

    raw = _extract_jost_class_pairs()
    pairs: dict[tuple[str, str], int] = {}
    for (g1, g2), value in raw.items():
        if g1 in jost_to_ours and g2 in jost_to_ours:
            pairs[(jost_to_ours[g1], jost_to_ours[g2])] = value

    # 'a' IS 'd's own outline here (see module docstring), so its
    # kerning should be too -- not a blend of that and whatever Jost's
    # own, differently-drawn 'a' happens to carry. Drop every pair this
    # filter just pulled in under Jost's native 'a' (both positions)
    # before copying 'd's own pairs onto 'a' in their place; Jost's 'd'
    # happens to carry zero class-kerning pairs of its own (confirmed
    # directly -- its rounded-bowl-plus-stem shape apparently doesn't
    # need the correction 'a'/'o'/'e'/'c' do), so this leaves 'a'
    # unkerned too, which is the more consistent outcome given it now
    # shares 'd's exact shape, not a borrowed approximation.
    pairs = {(l, r): v for (l, r), v in pairs.items() if l != "a" and r != "a"}
    for (left, right), value in list(pairs.items()):
        if left == "d":
            pairs[("a", right)] = value
        if right == "d":
            pairs[(left, "a")] = value
    if ("d", "d") in pairs:
        pairs[("a", "a")] = pairs[("d", "d")]

    _base_pairs_cache = pairs
    return pairs


def pairs_for(wdth: int) -> dict[tuple[str, str], int]:
    """{(our_glyph_name, our_glyph_name): xAdvance}, scaled by `wdth`'s
    own fraction -- Jost's kerning has no `wght`/`SERF` dependence to
    apply (see module docstring)."""
    scale = wdth / 100.0
    return {pair: round(value * scale) for pair, value in _base_pairs().items()}
