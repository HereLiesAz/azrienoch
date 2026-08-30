"""The SERF axis: adding slab feet to Roboto Flex's sans letterforms.

Rather than hand-picking stem coordinates per glyph, ``detect_feet`` scans
one reference instance's contours for short, already-flat horizontal runs
sitting on a guide line (baseline, x-height, cap-height, ascender,
descender) -- exactly where a sans stem already ends flat. That alone
isn't enough, though: a simple isolated stem (the top of 'I' or 'l') has
open space on *both* sides of its flat cap, but an arch letter's stem cap
(the top of 'n', 'm', 'p', 'r', 'h', where the stem meets the springing
arch) is flat on one side and borders the letter's own counter on the
other -- widening a foot symmetrically there punches a rectangular notch
into the counter instead of adding a serif. So for each end of a flat
run, ``_flat_runs`` also checks whether the adjacent contour segment is a
long straight line (a real stem descending/ascending to the next guide,
safe to grow a foot into) versus a short segment leading into a curve (the
counter side, which must stay put). ``apply_feet`` only ever grows a foot
on the side(s) marked extendable.

Every master then gets the *same* set of feet (by fractional position,
scaled to that master's own glyph width) via ``apply_feet``, which always
adds one rectangle contour per foot -- collapsed to a hairline sliver at
SERF=0, grown to a full slab at SERF=100 -- rather than boolean-unioning
a shape on conditionally. Deciding "does this stem get a foot, and on
which side(s)" once, from a single reference instance, and then only
ever moving those points' *coordinates* afterward, is what keeps every
master's glyph topologically identical (same contour/point count), which
variable-font interpolation requires; detecting stems freshly per
master, or unioning them in only above some threshold, both risk a
different point count on different masters and a font that fails to
compile.
"""

from __future__ import annotations

import math

from tools import geometry as g

TOLERANCE = 6.0  # units; how close a point must be to a guide line
MIN_RUN = 10.0  # units; ignore tiny flat runs (noise, not a real stem)
MAX_RUN = 260.0  # units; ignore wide runs (crossbars/bowls, not a stem)
MIN_FOOT_H = 1.0  # units; SERF=0 foot height -- a hairline, not literally 0
MIN_STEM_LEN = 300.0  # units; how long an adjacent straight run must be to
# count as a real stem side (safe to grow a foot into) rather than a short
# connector leading into a counter -- comfortably between the ~135-unit
# connector segments observed at arch springs and the ~700+-unit stems


def _seg_len(p, q):
    return math.hypot(p.x - q.x, p.y - q.y)


def _flat_runs(glyph):
    """Yield (x0, x1, y, is_top, left_ext, right_ext) for flat stem caps.

    left_ext/right_ext say whether the run's left/right end connects to a
    long straight stem (open space beyond it, safe to widen a foot into)
    versus a short run into a curve (the counter side -- must not widen).
    """
    for contour in glyph.contours:
        pts = list(contour.points)
        n = len(pts)
        for i in range(n):
            a, b = pts[i], pts[(i + 1) % n]
            if a.type is None or b.type is None:
                continue  # only genuine straight (line) edges
            if abs(a.y - b.y) > 1.0:
                continue
            run = abs(a.x - b.x)
            if run < MIN_RUN or run > MAX_RUN:
                continue
            y = (a.y + b.y) / 2
            prev_pt = pts[(i - 1) % n]
            next_pt = pts[(i + 2) % n]
            a_ext = a.type == "line" and _seg_len(prev_pt, a) >= MIN_STEM_LEN
            b_ext = b.type == "line" and _seg_len(b, next_pt) >= MIN_STEM_LEN
            if a.x <= b.x:
                left_ext, right_ext = a_ext, b_ext
            else:
                left_ext, right_ext = b_ext, a_ext
            x0, x1 = sorted((a.x, b.x))
            # CCW outer contours: a left-to-right bottom edge has ink
            # *above* it (a bottom guide); a right-to-left edge is a top
            # guide (ink below).
            is_top_guide = not (a.x < b.x)
            yield x0, x1, y, is_top_guide, left_ext, right_ext


def detect_feet(reference_glyph, guides: dict[str, float]) -> list[dict]:
    """Foot specs (fractional x, guide name, direction, extendable sides)
    from one reference."""
    width = reference_glyph.width or 1
    specs = []
    seen = set()
    for x0, x1, y, is_top, left_ext, right_ext in _flat_runs(reference_glyph):
        guide_name = min(guides, key=lambda k: abs(guides[k] - y))
        if abs(guides[guide_name] - y) > TOLERANCE:
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
        ))
    return specs


def apply_feet(glyph, foot_specs: list[dict], guides: dict[str, float], serif_amount: float):
    """Add one rectangle contour per foot spec, always -- see module docstring."""
    width = glyph.width or 1
    for spec in foot_specs:
        cx = spec["x_frac"] * width
        run_w = max(spec["run_frac"] * width, 4.0)
        y = guides[spec["guide"]]
        extra = serif_amount * (run_w * 0.9) / 100.0
        x0, x1 = cx - run_w / 2, cx + run_w / 2
        left_ext = spec.get("left_ext", True)
        right_ext = spec.get("right_ext", True)
        if left_ext and right_ext:
            x0, x1 = x0 - extra / 2, x1 + extra / 2
        elif left_ext:
            x0 -= extra
        elif right_ext:
            x1 += extra
        # neither side extendable: leave the foot at the run's own width --
        # both neighbours border something other than an open stem side
        foot_h = MIN_FOOT_H + serif_amount * (run_w * 0.42) / 100.0
        if spec["direction"] > 0:
            y0, y1 = y, y + foot_h
        else:
            y0, y1 = y - foot_h, y
        g.append_into(glyph, g.rect(x0, y0, x1, y1))
    return glyph
