"""The SERF axis: adding slab feet to Jost's sans letterforms.

Ported from the repository root's own `tools/serifs.py` (which does this
for Roboto Flex) rather than the point-insertion approach this module
tried first: instead of relocating a stem's own corner points, this
detects a flat terminal run once on a reference instance and, at every
master, APPENDS a separate rectangle contour there -- collapsed to a
hairline at SERF=0, a full slab at SERF=100 -- wound the same direction
as the stem's own contour so it merges as more solid ink rather than
needing any hole/winding logic. This sidesteps the whole class of bug
the point-insertion version had (see git history): appending a same-
wound rectangle can only ever add ink, never accidentally flip a
contour's fill relationship with something else.

Root's own key insight, reused directly: a flat run's SIDE only gets
widened when the *adjacent* segment is a long, straight, genuine stem
side -- not a short connector leading into a curve (an arch letter's
spring, or a stem transitioning into a bowl). That length threshold is
exactly what a first, more complicated version of this file was missing
when it grew a spurious extra foot on 'n' where its left stem's short
run-up to the arch (~70 units) happens to end flat and close enough to
the x-height ballpark to look like a genuine terminal -- root's
MIN_STEM_LEN cleanly rejects anything that short as "not a real stem",
no per-contour-extreme special-casing needed.

Per the project owner's direction, WHICH guide line(s) a given letter's
feet grow from depends on its own shape:

- A letter confined to the x-height box (`SINGLE_STORY`) gets a foot at
  both the baseline and the x-height top.
- A letter with an ascender (`ASCENDER`) gets a foot only at the
  baseline -- never at the ascender/cap top.
- A letter with a descender (`DESCENDER`) gets a foot only at its own
  descender depth (read per glyph, not a shared constant -- Jost's own
  g/q don't reach exactly the same depth).
- Uppercase and digits get a foot only at the baseline.

Diagonal-only strokes (v/w/x/y, A/V/W/X/Y/K's legs) and curved
terminals (g's own descender hook) have no flat stem run to grow a foot
from at all and are simply left alone -- confirmed by inspection, not
assumed: `detect_feet` finds nothing there because there's nothing
matching its own definition of a stem terminal, not because they're
special-cased out.
"""

from __future__ import annotations

import math

import ufoLib2

from . import params

TOLERANCE = 6.0  # units: how close a flat run's y must be to a guide line
MIN_RUN = 10.0  # units: ignore tiny flat runs (noise, not a real stem)
MAX_RUN = 200.0  # units: ignore wide runs (crossbars/bowls, not a stem) -- Jost's own stems run roughly 75-165 units wide
MIN_FOOT_H = 1.0  # units: SERF=0 foot height -- a hairline, not literally 0
MIN_STEM_LEN = 150.0  # units: how long an adjacent straight run must be to count as a real stem side

SINGLE_STORY = set("acemnorsuvwxz")
ASCENDER = set("bdfhikl") | {"t"}
DESCENDER = set("gjpqy")


def _seg_len(p, q) -> float:
    return math.hypot(p.x - q.x, p.y - q.y)


def _signed_area(points) -> float:
    n = len(points)
    total = 0.0
    for i in range(n):
        x1, y1 = points[i].x, points[i].y
        x2, y2 = points[(i + 1) % n].x, points[(i + 1) % n].y
        total += x1 * y2 - x2 * y1
    return total / 2.0


def _flat_runs(glyph):
    """Yields (contour, x0, x1, y, is_top_guide, left_ext, right_ext) for
    every flat stem-terminal candidate. left_ext/right_ext say whether
    that end connects to a long straight stem (safe to widen a foot
    into) versus a short run into a curve (must not widen -- would
    notch a counter)."""
    for contour in glyph.contours:
        pts = list(contour.points)
        n = len(pts)
        for i in range(n):
            a, b = pts[i], pts[(i + 1) % n]
            if a.type is None or b.type is None:
                continue
            if b.type != "line":
                continue
            if abs(a.y - b.y) > 1.0:
                continue
            run = abs(a.x - b.x)
            if run < MIN_RUN or run > MAX_RUN:
                continue
            y = (a.y + b.y) / 2
            prev_pt = pts[(i - 1) % n]
            next_pt = pts[(i + 2) % n]
            a_ext = a.type == "line" and _seg_len(prev_pt, a) >= MIN_STEM_LEN
            b_ext = _seg_len(b, next_pt) >= MIN_STEM_LEN
            if a.x <= b.x:
                left_ext, right_ext = a_ext, b_ext
            else:
                left_ext, right_ext = b_ext, a_ext
            x0, x1 = sorted((a.x, b.x))
            is_top_guide = not (a.x < b.x)
            yield contour, x0, x1, y, is_top_guide, left_ext, right_ext


def detect_feet(reference_glyph, guides: dict[str, float]) -> list[dict]:
    """Foot specs (fractional x/width, guide name, direction, extendable
    sides, and the stem contour's own winding sign) from one reference
    instance -- reused as-is (only re-scaled) at every master, so every
    master's glyph gets identical topology."""
    width = reference_glyph.width or 1
    specs = []
    seen = set()
    for contour, x0, x1, y, is_top, left_ext, right_ext in _flat_runs(reference_glyph):
        if not guides:
            continue
        guide_name = min(guides, key=lambda k: abs(guides[k] - y))
        if abs(guides[guide_name] - y) > TOLERANCE:
            continue
        if not (left_ext or right_ext):
            continue
        key = (round(x0), round(x1), guide_name)
        if key in seen:
            continue
        seen.add(key)
        specs.append(dict(
            x_frac=((x0 + x1) / 2) / width,
            run_frac=(x1 - x0) / width,
            guide=guide_name,
            direction=-1 if is_top else 1,
            left_ext=left_ext,
            right_ext=right_ext,
            positive_winding=_signed_area(contour.points) >= 0,
        ))
    return specs


def _rect_points(x0, y0, x1, y1, positive_winding: bool):
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]  # counter-clockwise (positive signed area)
    if not positive_winding:
        pts.reverse()
    return pts


def apply_feet(glyph, foot_specs: list[dict], guides: dict[str, float], serif_amount: float) -> None:
    """Appends one rectangle contour per foot spec, always (even at
    serif_amount=0 -- a collapsed hairline, not a skipped contour, so
    every master keeps identical topology)."""
    width = glyph.width or 1
    for spec in foot_specs:
        if spec["guide"] not in guides:
            continue
        cx = spec["x_frac"] * width
        run_w = max(spec["run_frac"] * width, 4.0)
        y = guides[spec["guide"]]
        extra = serif_amount * (run_w * 0.9) / 100.0
        x0, x1 = cx - run_w / 2, cx + run_w / 2
        left_ext, right_ext = spec["left_ext"], spec["right_ext"]
        if left_ext and right_ext:
            x0, x1 = x0 - extra / 2, x1 + extra / 2
        elif left_ext:
            x0 -= extra
        elif right_ext:
            x1 += extra
        foot_h = MIN_FOOT_H + serif_amount * (run_w * 0.42) / 100.0
        y0, y1 = (y, y + foot_h) if spec["direction"] > 0 else (y - foot_h, y)

        pen = glyph.getPointPen()
        pen.beginPath()
        for x, y_ in _rect_points(x0, y0, x1, y1, spec["positive_winding"]):
            pen.addPoint((round(x, 2), round(y_, 2)), segmentType="line")
        pen.endPath()


def guides_for(ch: str, glyph_min_y: float) -> dict[str, float]:
    """The full set of guide lines to search for flat runs against
    (detect_feet picks the closest one per run), and separately, which
    of those guide NAMES this letter is actually allowed to grow a foot
    at -- see module docstring for the per-letter-class rule. Returns
    only the allowed subset, already filtered, since detect_feet and
    apply_feet both just take "the guides that apply here"."""
    all_guides = {
        "baseline": 0.0,
        "xheight": params.X_HEIGHT,
        "ascender": params.ASCENDER,
        "cap": params.CAP_HEIGHT,
        "descender": glyph_min_y,
    }
    if ch in SINGLE_STORY:
        allowed = {"baseline", "xheight"}
    elif ch in ASCENDER:
        allowed = {"baseline"}
    elif ch in DESCENDER:
        allowed = {"descender"}
    else:
        allowed = {"baseline"}  # uppercase and digits
    return {name: y for name, y in all_guides.items() if name in allowed}
