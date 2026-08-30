"""Realign a glyph's own contour point order to a reference master's, so
gvar interpolates "the same point" between weights instead of two points
that only coincidentally share an index.

Point count and on/off-curve type sequence being identical across every
master (Roboto Flex's own gvar already guarantees this, and
`validate_build` checks it) is necessary for interpolation to work at
all, but it's not sufficient for interpolation to look right: nothing
guarantees that point index *i* denotes the same geometric point --
"the compass-north corner", say -- at every master. For most letters it
does, self-evidently: an asymmetric shape like 'n' or 'H' would look
visibly wrong in Roboto Flex's own single-instance rendering if its own
point order were rotated relative to another of its own masters, so nothing
in Roboto Flex's authoring process would ever produce that by accident.

A shape with real geometric symmetry doesn't have that self-correcting
property. Confirmed directly on 'o': Roboto Flex's own Thin-weight outer
contour has its point index 3 at the shape's own topmost vertex; at
Regular weight, that same index 3 is at the *bottom* -- a clean half-turn
rotation of the point sequence relative to itself, invisible in either
single instance (a symmetric oval looks identical no matter which of its
own points you call "first"), but fatal to interpolation: gvar lerps
point 3 at Thin straight toward point 3 at Regular, i.e. from the top of
the letter to the bottom, collapsing the whole contour through a
zero-height sliver around the interpolation's midpoint before it
re-inflates on the far side. Confirmed this is the actual mechanism (not
self-intersection in the usual bowtie sense) by sweeping for edge-edge
crossings at the collapse weight and finding none -- the contour stays
simple throughout, it just flattens to a degenerate sliver and comes back
"upside down" relative to where it started.

`align_to_reference` finds, for one contour, which rotation offset of its
own points best matches a reference contour's own point order -- checked
by ANGLE from each contour's own centroid (scale-invariant, so it's a
fair comparison between a small Thin instance and a much larger Regular
one), restricted to rotations that preserve the on/off-curve type
sequence (anything else isn't a valid correspondence at all, not just a
worse one). For the overwhelming majority of glyphs the identity rotation
already wins by a wide margin -- this is a no-op for anything not
genuinely ambiguous -- but for a symmetric shape like 'o' it finds and
corrects exactly the kind of offset described above.
"""

from __future__ import annotations

import math
from collections import namedtuple

_Point = namedtuple("_Point", ["x", "y", "type"])


def snapshot(glyph):
    """An immutable copy of `glyph`'s own current contours -- (x, y,
    type) only, detached from the glyph's live Point objects -- so it
    keeps working as a reference after the glyph it was taken from goes
    on to be mutated by quirks/reshaping/etc. Use this (not a plain
    `list(contour.points)`, which only copies the list, not the Point
    objects it holds) whenever a snapshot needs to outlive further edits
    to its source glyph."""
    return [[_Point(p.x, p.y, p.type) for p in c.points] for c in glyph.contours]


def _centroid(points):
    return (sum(p.x for p in points) / len(points), sum(p.y for p in points) / len(points))


def _angles(points):
    cx, cy = _centroid(points)
    return [math.atan2(p.y - cy, p.x - cx) for p in points]


def _angle_diff(a: float, b: float) -> float:
    d = a - b
    return (d + math.pi) % (2 * math.pi) - math.pi


def _best_rotation(target_points, ref_points) -> int:
    """The rotation offset r (0..n-1) such that target_points[(i+r) % n]
    best corresponds to ref_points[i], among rotations that preserve the
    on/off-curve type sequence. 0 (identity) if nothing else is even a
    valid candidate, which is the common case."""
    n = len(target_points)
    target_types = [p.type for p in target_points]
    ref_types = [p.type for p in ref_points]
    t_angles = _angles(target_points)
    r_angles = _angles(ref_points)

    best_r, best_cost = 0, None
    for r in range(n):
        if not all(target_types[(i + r) % n] == ref_types[i] for i in range(n)):
            continue
        cost = sum(_angle_diff(t_angles[(i + r) % n], r_angles[i]) ** 2 for i in range(n))
        if best_cost is None or cost < best_cost:
            best_r, best_cost = r, cost
    return best_r


def _bbox_area(points) -> float:
    xs = [p.x for p in points]
    ys = [p.y for p in points]
    return (max(xs) - min(xs)) * (max(ys) - min(ys))


def _group_by_point_count(contour_point_lists):
    groups: dict[int, list[int]] = {}
    for i, pts in enumerate(contour_point_lists):
        groups.setdefault(len(pts), []).append(i)
    return groups


def align_to_reference(glyph, reference_contours) -> None:
    """Realign `glyph`'s own contours -- both which list position each
    one sits at, and each one's own point rotation -- to match
    `reference_contours` (a `snapshot()` of the same glyph at the
    reference master), in place. Contour count must already match (the
    topology invariant every master already satisfies).

    Both levels of reordering matter because gvar interpolation (and the
    naive per-point lerp this module exists to make safe for) flattens a
    glyph down to one single global point sequence -- every contour's
    points, back to back, in `glyph.contours`' own list order -- and
    interpolates that whole sequence by index. Fixing a contour's own
    internal point rotation but leaving it at the wrong LIST POSITION is
    just as broken as leaving the rotation wrong: confirmed directly on
    'o', whose outer contour sits at `glyph.contours[1]` at Thin but
    `glyph.contours[0]` at Regular -- with only point rotation fixed, the
    global sequence still lerps Thin's inner counter into Regular's outer
    silhouette.

    Contours are paired by their own point count first -- a hard
    requirement, since two contours with different point counts can
    never really correspond -- and only ranked by descending bounding-box
    area (largest paired with largest) to disambiguate among same-count
    candidates. Bounding-box rank on its own turned out not to be a safe
    enough signal: several Cyrillic composites (confirmed on 'ж'/'ы'/
    'ю'/'я') have multiple contours whose relative sizes aren't fixed
    across weight, so ranking by area alone paired, e.g., a 4-point
    contour at one master with a 9-point contour at another -- not a
    reordering, an outright topology break that failed fontmake's own
    compatibility check outright. If the glyph's contours don't group
    into point-count buckets of matching size between target and
    reference (there's no way to pair them up cleanly), this leaves the
    glyph's contour order untouched rather than guess."""
    contours = glyph.contours
    if len(contours) != len(reference_contours):
        return

    target_groups = _group_by_point_count([c.points for c in contours])
    ref_groups = _group_by_point_count(reference_contours)
    if sorted((count, len(idxs)) for count, idxs in target_groups.items()) != sorted(
        (count, len(idxs)) for count, idxs in ref_groups.items()
    ):
        return

    reordered_contours = list(contours)
    for count, target_idxs in target_groups.items():
        ref_idxs = ref_groups[count]
        target_ranked = sorted(target_idxs, key=lambda i: _bbox_area(contours[i].points), reverse=True)
        ref_ranked = sorted(ref_idxs, key=lambda i: _bbox_area(reference_contours[i]), reverse=True)
        for ti, ri in zip(target_ranked, ref_ranked):
            reordered_contours[ri] = contours[ti]
    contours[:] = reordered_contours

    for contour, ref_points in zip(contours, reference_contours):
        points = contour.points
        if len(points) != len(ref_points) or len(points) < 3:
            continue
        r = _best_rotation(points, ref_points)
        if r == 0:
            continue
        n = len(points)
        reordered = [points[(i + r) % n] for i in range(n)]
        points[:] = reordered
