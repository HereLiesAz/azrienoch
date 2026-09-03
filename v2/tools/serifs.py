"""A variable SERF axis (0-100, sans by default): grows a slab foot at a
stem's flat terminal, the same way `wght` grows stroke thickness --
collapsed to nothing at SERF=0, a full slab at SERF=100, same technique
the repository root's own `tools/serifs.py` uses on Roboto Flex (detect
a flat run bordering a real stem, add the *same* foot topology to every
master, sized by that master's own SERF value).

Per the project owner's direction, which terminal(s) get a foot depends
on the letter's own shape, not a single fixed rule:

- A letter confined entirely to the x-height box (no ascender or
  descender -- `SINGLE_STORY` below) gets a foot at BOTH ends: the
  baseline and the x-height top are both "free" terminals with nothing
  extending further.
- A letter with an ascender or descender (`TWO_STORY` below) gets a
  foot only at the end that terminates at a baseline or a descender
  depth -- never at an ascender/cap top, which stays a plain cut.
- Every uppercase letter gets a foot only at the baseline, same
  reasoning as the two-story lowercase group.

Only straight, vertical-sided stems are handled -- a flat run is grown
into a foot only when it borders a real stem (a long straight run
perpendicular to it), the same guard the root project's own
`detect_feet` uses to keep a foot from notching into an arch letter's
counter. Diagonal-only strokes (the legs of A/V/W/X/Y/K's diagonals,
v/w/x/y's own diagonals) have no flat stem terminal to grow a foot from
and are left alone -- a cupped serif on a diagonal is a different
construction, not attempted here.
"""

from __future__ import annotations

from . import params

TOLERANCE = 1.0  # units: how close to target_y counts as "at" it, at the baseline/a descender (both exact per-glyph)
TOP_TOLERANCE = 15.0  # x-height varies letter to letter in Jost's own design (o/r/m hit 470, u only 460)
MAX_STEM_RUN = 180.0  # units: how long a flat run can be and still be "a stem edge", not a crossbar

# Letters confined to the x-height box: a foot at both baseline and x-height.
SINGLE_STORY = set("acemnorsuvwxz")
# Letters with an ascender: a foot only at the baseline.
ASCENDER = set("bdfhiklt")
# Letters with a descender: a foot only at the descender depth (the
# glyph's own lowest point, not a fixed constant -- read per glyph).
DESCENDER = set("gjpqy")


def _on_curve_indices(points):
    return [i for i, p in enumerate(points) if p.type is not None]


def find_flat_stem_runs(points, target_y: float, tolerance: float = TOLERANCE, stem_above: bool = True):
    """Finds every straight run of points[i] -> points[i+1] that sits at
    `target_y` (both endpoints, within `tolerance`), short enough to be
    a stem's own edge rather than a crossbar, confirms each endpoint
    continues into a genuine vertical stem (not a curve) on its far
    side -- the guard that keeps this from growing a foot into an arch
    letter's own curved counter -- AND that the run sits at this
    contour's own actual extreme (its true lowest point for a bottom
    foot, highest for a top foot), not just within `tolerance` of the
    target in absolute terms.

    That last check matters on letters like 'n': its left stem's own
    top happens to go flat for one short run at y=460 before curving
    into the arch -- within TOP_TOLERANCE of the x-height ballpark, and
    genuinely bordered by a real vertical stem on one side, so it passes
    every other check here -- but the arch itself reaches 10 units
    higher (470) just a few points later. That flat run is a local
    straightening inside an otherwise curving boundary, not the actual
    top of anything: growing a foot there produced a single lopsided
    spike on one side of 'n' and nothing on the other, caught by
    rendering it and comparing against what a real terminal should look
    like. Requiring the run to match this SAME CONTOUR's own true
    extreme (not the whole glyph's -- 'r's stem is its own separate
    contour from its arm, and the stem's own top is genuinely its
    contour's max even though the arm reaches higher in a different
    contour) rules out exactly this case without needing a much smaller,
    more fragile absolute tolerance.

    Returns a list of (i_left, i_right) on-curve point index pairs,
    i_left always the smaller x. Indices are into the ORIGINAL point
    list, before any insertion.
    """
    n = len(points)
    contour_extreme = max(p.y for p in points) if not stem_above else min(p.y for p in points)
    runs = []
    for i in range(n):
        p, q = points[i], points[(i + 1) % n]
        if p.type is None or q.type is None:
            continue
        if q.type != "line":
            continue
        if abs(p.y - target_y) > tolerance or abs(q.y - target_y) > tolerance:
            continue
        if abs(p.y - contour_extreme) > 3.0:
            continue
        if abs(p.x - q.x) > MAX_STEM_RUN:
            continue
        # Confirm each endpoint's OTHER neighbor is a genuine vertical
        # stem side: a straight line, nearly vertical, of real length.
        prev_p = points[(i - 1) % n]
        next_q = points[(i + 2) % n]
        if not _is_vertical_stem_side(prev_p, p) or not _is_vertical_stem_side(q, next_q):
            continue
        i_left, i_right = (i, (i + 1) % n) if p.x <= q.x else ((i + 1) % n, i)
        runs.append((i_left, i_right))
    return runs


def _is_vertical_stem_side(a, b) -> bool:
    if a.type is None or b.type is None:
        return False
    dx, dy = abs(a.x - b.x), abs(a.y - b.y)
    return dy > 30 and dx < dy * 0.35


def insert_foot(contour, i_left: int, i_right: int, target_y: float, stem_above: bool, flare: float, height: float) -> int:
    """Grows one foot at the flat run points[i_left]-points[i_right]
    (both at `target_y`), by relocating those two points outward and
    inserting one new point on each side at the kink height -- a
    trapezoid flare, not a bracketed/curved traditional serif. At
    flare=height=0 every new/moved point lands exactly on the original
    corner, so SERF=0 reproduces the unmodified terminal exactly.

    `stem_above` is True for a bottom foot (the stem rises up from this
    flat run, so the flare's kink sits ABOVE target_y) and False for a
    top foot (the stem descends to this run from above, kink BELOW).

    Mutates `contour` in place (relocates 2 points, inserts 2 new
    ones). Returns how many points were inserted (2), so callers
    processing multiple runs in the same contour can keep later
    indices valid by processing runs in descending index order.
    """
    points = contour.points
    left, right = points[i_left], points[i_right]
    sign = 1.0 if stem_above else -1.0
    kink_y = target_y + sign * height

    # New outer corners (the flared foot's own bottom-most/top-most
    # extent), replacing the original flat-run endpoints.
    left.x -= flare
    right.x += flare

    # New kink points, one per side, at the original (pre-flare) x and
    # the kink height -- inserted so the contour now reads corner ->
    # kink -> (unchanged stem side continues from there).
    PointClass = type(left)
    kink_left = PointClass(left.x + flare, kink_y, type="line")
    kink_right = PointClass(right.x - flare, kink_y, type="line")

    # Insert after i_right (kink_right, between right and its outward
    # stem neighbor) and after i_left (kink_left) -- highest index first
    # so the lower insertion doesn't shift it.
    if i_right > i_left:
        points.insert(i_right + 1, kink_right)
        points.insert(i_left, kink_left)
    else:
        points.insert(i_left + 1, kink_left)
        points.insert(i_right, kink_right)
    return 2


def classify_positions(ch: str, glyph_min_y: float) -> list[tuple[float, bool, float]]:
    """Returns [(target_y, stem_above, tolerance), ...] -- the
    terminal(s) that should get a foot for character `ch`, given this
    glyph's own lowest point (needed for descender letters, whose foot
    sits at their own descender depth, not a shared constant). x-height
    uses TOP_TOLERANCE, not the strict default, since Jost's own letters
    don't all reach the exact same x-height (see params.X_HEIGHT)."""
    if ch in SINGLE_STORY:
        return [(0.0, True, TOLERANCE), (params.X_HEIGHT, False, TOP_TOLERANCE)]
    if ch in ASCENDER:
        return [(0.0, True, TOLERANCE)]
    if ch in DESCENDER:
        return [(glyph_min_y, True, TOLERANCE)]
    return [(0.0, True, TOLERANCE)]  # uppercase and digits: baseline only


def apply_serif(glyph, ch: str, serf: float) -> None:
    """Grows every applicable foot on `glyph` for character `ch`, sized
    by `serf` (0-100). Safe to call at serf=0 -- every insertion
    collapses to the original corner, a no-op shape (still inserts the
    same extra points, though, which is required: every master needs
    identical topology for this glyph, including the SERF=0 ones)."""
    flare = serf / 100.0 * 26.0
    height = serf / 100.0 * 70.0
    min_y = min(p.y for c in glyph.contours for p in c.points)
    for target_y, stem_above, tolerance in classify_positions(ch, min_y):
        for contour in glyph.contours:
            runs = find_flat_stem_runs(contour.points, target_y, tolerance)
            for i_left, i_right in sorted(runs, key=lambda pair: -max(pair)):
                insert_foot(contour, i_left, i_right, target_y, stem_above, flare, height)
