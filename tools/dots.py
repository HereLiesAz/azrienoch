"""A deliberate design pass: making dots read as a confident mark.

Not a bug fix (see `roboto_source.py::_HEIGHT_AXES_AT_WGHT`'s `XOPQ`
comment for the actual bug, an oversized exclamation-mark dot at Thin,
fixed there). This is a separate, opt-in design decision: Roboto Flex's
period/colon/semicolon/tittle/exclam/question dots don't grow with
stroke weight the way stems do -- across the whole `wght` range they
stay close to the same small size, which reads as thin and easy to miss
at a glance, especially next to Azrienoch's already-wide counters.

``detect_dot_contours`` finds candidate dot contours once, on one
reference instance, the same way ``serifs.py::detect_feet`` finds
candidate stem feet: a small, roughly square/round closed contour is a
dot (a period's only contour, a colon's or diaeresis's two, a
semicolon/exclam/question mark's dot half -- but not that same
semicolon's comma tail, or an exclam's tall stem, which aren't
square). ``boost_dots`` then scales *only those same contour indices*
up around their own centroid on every master, sized off that master's
own geometry -- never adding or removing a point, which is what keeps
every master of a glyph topologically identical for gvar interpolation.
The boost itself tapers off with weight (``boost_factor_for_wght``):
Roboto Flex's dots read as an easy-to-miss fleck at Thin, but by
Bold/Black they're already a confident size on their own -- boosting
them by the same flat amount there crowds a colon's two dots into each
other.

``reposition_tittle`` is a related but separate fix, for 'i'/'j'
specifically: Roboto Flex's own tittle doesn't just sit low of where
letters like h/d/b/k/l actually top out (not the font's much taller
``hhea.ascender`` metric, which is line-spacing padding, not a glyph
height) -- at Bold and especially Black weight, it sits *close enough to
the stem beneath it that their bounding boxes overlap*, reading as one
fused blob instead of a stem with a dot above it. This is Roboto Flex's
own geometry, present with none of Azrienoch's changes anywhere near it.
Moving the tittle straight up so its top lands exactly on the true
ascender height (measured off a reference letter, not the font metric)
fixes both at once: it now reads level with the rest of the ascenders,
and since that height sits well clear of the stem top at every weight
-- unlike the tittle's original, much lower position -- the overlap is
gone too.
"""

from __future__ import annotations

MAX_DOT_SIZE = 260.0  # units; a dot's bounding box must be under this on both axes
MIN_ASPECT = 0.55  # width/height; keeps genuinely round/square shapes only
MAX_ASPECT = 1.8  # (rules out a comma's curved tail, an exclam's tall stem, ...)

# Boost tapers from a strong lift at Thin (where Roboto Flex's own dots
# are easy to miss) down to none at Bold/Black (where they're already a
# reasonable size, and boosting further starts crowding a colon's two
# dots into each other).
_BOOST_AT_WGHT = {100: 1.3, 400: 1.15, 700: 1.0, 900: 1.0}

TITTLE_CHARS = {"i", "j"}


def _bbox(contour):
    xs = [p.x for p in contour.points]
    ys = [p.y for p in contour.points]
    return min(xs), min(ys), max(xs), max(ys)


def detect_dot_contours(glyph) -> list[int]:
    """Indices of `glyph`'s contours that look like a dot.

    Small and roughly square/round alone isn't quite enough: `Ħ`'s
    crossbar (a small, near-square 4-point rectangle -- a straight-edged
    stroke seen edge-on, not a round mark) would otherwise false-positive.
    A dot is drawn with at least one curve; requiring one rules that out
    without needing a glyph-name denylist.
    """
    indices = []
    for i, contour in enumerate(glyph.contours):
        x0, y0, x1, y1 = _bbox(contour)
        w, h = x1 - x0, y1 - y0
        if w <= 0 or h <= 0 or w > MAX_DOT_SIZE or h > MAX_DOT_SIZE:
            continue
        aspect = w / h
        if not (MIN_ASPECT <= aspect <= MAX_ASPECT):
            continue
        if not any(p.type not in ("line", None) for p in contour.points):
            continue  # an all-straight-line contour is a bar, not a dot
        indices.append(i)
    return indices


def boost_factor_for_wght(wght: float) -> float:
    """How much to grow a dot at this weight -- see module docstring."""
    wghts = sorted(_BOOST_AT_WGHT)
    for i in range(len(wghts) - 1):
        w0, w1 = wghts[i], wghts[i + 1]
        if wght <= w1 or i == len(wghts) - 2:
            t = 0.0 if w1 == w0 else (wght - w0) / (w1 - w0)
            f0, f1 = _BOOST_AT_WGHT[w0], _BOOST_AT_WGHT[w1]
            return f0 + (f1 - f0) * t
    return 1.0


def boost_dots(glyph, dot_indices: list[int], factor: float) -> None:
    """Scale each of `glyph`'s contours named in `dot_indices` up around
    its own centroid by `factor`. Only ever moves existing points."""
    for i in dot_indices:
        if i >= len(glyph.contours):
            continue
        contour = glyph.contours[i]
        x0, y0, x1, y1 = _bbox(contour)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        for p in contour.points:
            p.x = cx + (p.x - cx) * factor
            p.y = cy + (p.y - cy) * factor


def reposition_tittle(glyph, dot_indices: list[int], ascender_height: float) -> None:
    """Move each of `glyph`'s contours named in `dot_indices` straight up
    or down so its top lands exactly on `ascender_height`. A translation,
    not a resize -- only ever moves existing points."""
    for i in dot_indices:
        if i >= len(glyph.contours):
            continue
        contour = glyph.contours[i]
        _, _, _, y1 = _bbox(contour)
        dy = ascender_height - y1
        for p in contour.points:
            p.y += dy
