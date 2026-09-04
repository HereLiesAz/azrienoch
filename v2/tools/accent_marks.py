"""Re-attaches Jost's own diacritic marks onto THIS project's own
modified base letters, for the accented Latin letters whose base ('c',
'e', or 's') this project no longer draws the way Jost itself does --
'c'/'e' are cut-open rings derived from 'o' (`ring_derived.py`), and
's' is Arimo-sourced (`arimo_source.py`), not Jost's own outline.

Without this, an accented glyph like 'ć' or 'ś' would still carry
Jost's own native 'c'/'s' shape merged into the same drawing as its
accent mark (confirmed directly: `jost_source.extract` returns
`ccedilla` as a single, already-fused two-contour glyph, not a
`c` + a separate cedilla component) -- reading visibly inconsistent
with this project's own, differently-shaped 'c'/'e'/'s' right next to
it.

Jost's own accented glyphs are NOT a base contour byte-identical to
its own plain letter plus a mark contour appended -- confirmed
directly: 'ę's own first contour has a different point count than
plain 'e' (44 vs 42 points), evidently redrawn slightly to fit the
mark, not literally reused. So this doesn't try to detect "the same
points, plus more" and swap only what differs; it takes a coarser, more
robust cut: 'c'/'e'/'s' are always drawn as a single contour (confirmed
across the whole accented set below), so contour 0 of Jost's own
accented glyph is always its own version of the base letter, and every
contour after it is the mark -- regardless of whether that base
contour matches Jost's own plain letter point-for-point. The mark
contours are repositioned only horizontally, to this project's own
base letter's own horizontal center instead of Jost's -- vertically
they're left exactly where Jost placed them, since both letters share
the same baseline and cap/x-height metrics (`params.py`), confirmed by
comparing bounding boxes directly rather than assumed.
"""

from __future__ import annotations

from . import jost_source

# accented character -> its base character, for every Latin-1/Latin
# Extended-A lowercase accented letter whose base is 'c', 'e', or 's'
# (this project's own three ring-derived/Arimo-sourced letters --
# uppercase C/E/S and 'r'/'f' are untouched by this project, so their
# own accented variants already carry Jost's own consistent shape
# and need no re-splicing).
BASE_OF = {
    # LATIN1
    "ç": "c",
    "è": "e", "é": "e", "ê": "e", "ë": "e",
    # LATIN_EXT_A
    "ć": "c", "ĉ": "c", "ċ": "c", "č": "c",
    "ē": "e", "ĕ": "e", "ė": "e", "ę": "e", "ě": "e",
    "ś": "s", "ŝ": "s", "ş": "s", "š": "s",
}


def _contours_of(pen_value: list) -> list[list]:
    contours = []
    current: list = []
    for cmd, args in pen_value:
        current.append((cmd, args))
        if cmd == "closePath":
            contours.append(current)
            current = []
    return contours


def _bbox(points: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def _points_of(contours: list[list]) -> list[tuple[float, float]]:
    return [pt for contour in contours for cmd, args in contour for pt in args if pt is not None]


def splice_mark(ch: str, wght: int, wdth: int, grad: int, our_base_pen_value: list) -> list:
    """Returns `our_base_pen_value` (this project's own already-built
    'c'/'e'/'s' at this master, as a pen value) with `ch`'s own
    diacritic mark(s) appended, taken from Jost's own drawing of `ch`
    and re-centered horizontally over `our_base_pen_value`'s own
    bounding box -- see module docstring."""
    jost_names = jost_source.glyph_names_for_chars(ch)
    jost_pen_value, _ = jost_source.extract(jost_names[ch], wght, wdth, grad)
    contours = _contours_of(jost_pen_value)
    mark_contours = contours[1:]

    jost_base_x0, _, jost_base_x1, _ = _bbox(_points_of(contours[:1]))
    our_x0, _, our_x1, _ = _bbox([pt for cmd, args in our_base_pen_value for pt in args if pt is not None])
    dx = (our_x0 + our_x1) / 2.0 - (jost_base_x0 + jost_base_x1) / 2.0

    mark_pen_value = [cmd_args for contour in mark_contours for cmd_args in contour]
    shifted = [
        (cmd, tuple(None if pt is None else (pt[0] + dx, pt[1]) for pt in args))
        for cmd, args in mark_pen_value
    ]
    return our_base_pen_value + shifted
