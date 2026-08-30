"""Thin 'o'/'c's round strokes at top and bottom to match the stroke
thickness where a bowl letter's own curve meets its flat stem.

Roboto Flex draws these as two different thicknesses even though they're
the same family of curve: 'o'/'c' read visibly heavier at their vertical
extremes (the "center" of the round shape) than the wall of 'd'/'b'/'p'/
'q's bowl does right where it meets the stem (the "neck"). Confirmed by
measuring both with matplotlib's own curve flattening (via
`preview.py::contour_to_mpl`), not bounding boxes, which are too coarse
for a wall thickness that changes along a curve: at Regular (wght 400),
'd'/'b'/'p'/'q's neck averages ~101 units against 'o's own top/bottom
thickness of 140 -- a ratio of about 0.75.

That ratio, not an absolute target, is what gets applied at every
master: measuring the neck itself turns out to be reliable only near
Regular. At Thin (wght 100) the neck in Roboto Flex's own native
geometry pinches to within a unit of zero -- a genuine feature of that
corner of Roboto Flex's design space (similar in kind to the XOPQ=27
corner `roboto_source.py` already works around for the exclamation
mark), not a measurement bug -- so matching it exactly would pinch
'o'/'c' shut at Thin instead of just reading appropriately thinner.
Applying the same *proportional* thinning (about 3/4 of each master's
own native center thickness) at every weight avoids that corner while
still delivering the requested effect: a center that reads consistently
thinner than the sides, in the same proportion the neck does at the one
weight where the comparison is clean.

``thin_round`` moves only the glyph's *inner* vertical-extreme points --
and never the outer silhouette, which this is trying to match in the
first place. For a glyph with a separate outer and inner contour (e.g.
'o': contour 0 outer, contour 1 the counter), that's straightforward:
the outer's own top/bottom bound the shape, the inner contour's own
top/bottom are the points that move. An earlier version of this instead
pooled every point from every contour and took the second-highest (and
second-lowest) distinct Y level as "the inner plateau" -- which happens
to equal the inner contour's own top/bottom at Regular weight, where it
was tested, but breaks at heavier weights: the *outer* contour grows its
own near-top plateau there too (a corner curve just below the true top),
which can sit higher than the inner contour's actual top and get seized
on and moved instead, dragging the outer silhouette in and squaring it
off -- exactly the defect this module exists to fix, just relocated to
the wrong contour. Fixed by scoping the search to contour 0 (outer,
bounds only) vs. contours 1+ (inner, the points that actually move) --
never mixed. For a one-contour glyph like 'c' (outer and inner edges
share a single open path), the same second-plateau search is still used,
since there's no second contour to scope to instead; it's held to real
letters only (not blindly generalized) for exactly that reason.

Never adds or removes a point, only moves the ones already there, so
every master stays topologically identical.
"""

from __future__ import annotations

import numpy as np
from matplotlib.path import Path

from tools.preview import contour_to_mpl

Y_PLATEAU_TOL = 1.0  # units; points within this share a "level" for grouping

# Measured once at Regular (wght 400, wdth 100): the average of 'd'/'b'/
# 'p'/'q's neck thickness (~101) divided by 'o's own native top/bottom
# thickness (140) -- see module docstring for why this ratio, not an
# absolute target, is what carries across masters.
CENTER_THICKNESS_RATIO = 0.75


def _flatten(contour, n=400):
    verts, codes = contour_to_mpl(contour)
    return Path(verts, codes).interpolated(n).vertices


def _min_dist(pt, poly):
    d = np.hypot(poly[:, 0] - pt[0], poly[:, 1] - pt[1])
    return float(d.min())


def _outer_contour(contours):
    """Whichever contour encloses the others -- not reliably contour 0
    (confirmed at Thin, wght 100, where Roboto Flex's own 'o' has the
    smaller-bbox contour first). The one true test: the outer contour is
    whichever one reaches the glyph's global max Y (an inner/counter
    contour, strictly enclosed, never can)."""
    global_top = max(p.y for c in contours for p in c.points)
    return next(c for c in contours if any(p.y == global_top for p in c.points))


def _inner_extremes(glyph):
    """(outer_top, outer_bottom, inner_top_y, inner_bottom_y), scoped so
    "inner" only ever refers to a real inner contour (or, for a
    one-contour glyph, the second Y-plateau in from the outer edge) --
    never a point actually on the outer silhouette. None if not found."""
    contours = glyph.contours
    if not contours:
        return None
    if len(contours) >= 2:
        outer = _outer_contour(contours)
        inner_points = [p for c in contours if c is not outer for p in c.points]
        outer_points = outer.points
        if not outer_points or not inner_points:
            return None
        outer_top = max(p.y for p in outer_points)
        outer_bottom = min(p.y for p in outer_points)
        inner_top_y = max(p.y for p in inner_points)
        inner_bottom_y = min(p.y for p in inner_points)
        return outer_top, outer_bottom, inner_top_y, inner_bottom_y

    all_points = contours[0].points
    outer_top = max(p.y for p in all_points)
    outer_bottom = min(p.y for p in all_points)
    below_top = sorted({p.y for p in all_points if p.y < outer_top - Y_PLATEAU_TOL}, reverse=True)
    above_bottom = sorted({p.y for p in all_points if p.y > outer_bottom + Y_PLATEAU_TOL})
    if not below_top or not above_bottom:
        return None
    return outer_top, outer_bottom, below_top[0], above_bottom[0]


def measure_center_thickness(glyph) -> float | None:
    """'o'/'c's own current top/bottom wall thickness (the average of
    the two), via curve flattening -- used both to compute the fixed
    ratio once at reference, and to find each master's own starting
    point before `thin_round` scales it down."""
    extremes = _inner_extremes(glyph)
    if extremes is None:
        return None
    outer_top, outer_bottom, inner_top_y, inner_bottom_y = extremes
    return ((outer_top - inner_top_y) + (inner_bottom_y - outer_bottom)) / 2.0


def thin_round(glyph, ratio: float = CENTER_THICKNESS_RATIO) -> None:
    """Move 'o'/'c's inner vertical-extreme points toward the outer
    boundary so the wall thickness there becomes `ratio` times what it
    currently is. Never touches the outer contour itself."""
    extremes = _inner_extremes(glyph)
    if extremes is None:
        return
    outer_top, outer_bottom, inner_top_y, inner_bottom_y = extremes

    top_thickness = outer_top - inner_top_y
    bottom_thickness = inner_bottom_y - outer_bottom
    new_inner_top_y = outer_top - top_thickness * ratio
    new_inner_bottom_y = outer_bottom + bottom_thickness * ratio

    contours = glyph.contours
    if len(contours) >= 2:
        outer = _outer_contour(contours)
        move_points = [p for c in contours if c is not outer for p in c.points]
    else:
        move_points = list(contours[0].points)
    for p in move_points:
        if abs(p.y - inner_top_y) <= Y_PLATEAU_TOL:
            p.y = new_inner_top_y
        elif abs(p.y - inner_bottom_y) <= Y_PLATEAU_TOL:
            p.y = new_inner_bottom_y
