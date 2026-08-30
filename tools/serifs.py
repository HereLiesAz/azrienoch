"""The SERF axis: adding slab feet to Roboto Flex's sans letterforms.

Rather than hand-picking stem coordinates per glyph, ``detect_feet`` scans
one reference instance's contours for short, already-flat horizontal runs
sitting on a guide line (baseline, x-height, cap-height, ascender,
descender) -- exactly where a sans stem already ends flat. Round strokes
(bowls, curve terminals) never present a flat run of that kind, so
they're naturally skipped: serifs only ever land on genuine stems, which
keeps this consistent with the horizontal-terminal rule rather than
fighting it -- a serif is just a wider, flatter version of a terminal the
letter already has.

Every master then gets the *same* set of feet (by fractional position,
scaled to that master's own glyph width) via ``apply_feet``, which always
adds one rectangle contour per foot -- collapsed to a hairline sliver at
SERF=0, grown to a full slab at SERF=100 -- rather than boolean-unioning
a shape on conditionally. Deciding "does this stem get a foot" once,
from a single reference instance, and then only ever moving those points'
*coordinates* afterward, is what keeps every master's glyph topologically
identical (same contour/point count), which variable-font interpolation
requires; detecting stems freshly per master, or unioning them in only
above some threshold, both risk a different point count on different
masters and a font that fails to compile.
"""

from __future__ import annotations

from tools import geometry as g

TOLERANCE = 6.0  # units; how close a point must be to a guide line
MIN_RUN = 10.0  # units; ignore tiny flat runs (noise, not a real stem)
MAX_RUN = 260.0  # units; ignore wide runs (crossbars/bowls, not a stem)
MIN_FOOT_H = 1.0  # units; SERF=0 foot height -- a hairline, not literally 0


def _flat_runs(glyph):
    """Yield (x0, x1, y, is_top) for near-horizontal straight point-pairs."""
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
            x0, x1 = sorted((a.x, b.x))
            # CCW outer contours: a left-to-right bottom edge has ink
            # *above* it (a bottom guide); a right-to-left edge is a top
            # guide (ink below).
            is_top_guide = not (a.x < b.x)
            yield x0, x1, y, is_top_guide


def detect_feet(reference_glyph, guides: dict[str, float]) -> list[dict]:
    """Foot specs (fractional x, guide name, direction) from one reference."""
    width = reference_glyph.width or 1
    specs = []
    seen = set()
    for x0, x1, y, is_top in _flat_runs(reference_glyph):
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
        ))
    return specs


def apply_feet(glyph, foot_specs: list[dict], guides: dict[str, float], serif_amount: float):
    """Add one rectangle contour per foot spec, always -- see module docstring."""
    width = glyph.width or 1
    for spec in foot_specs:
        cx = spec["x_frac"] * width
        run_w = max(spec["run_frac"] * width, 4.0)
        y = guides[spec["guide"]]
        foot_w = run_w + serif_amount * (run_w * 0.9) / 100.0
        foot_h = MIN_FOOT_H + serif_amount * (run_w * 0.42) / 100.0
        if spec["direction"] > 0:
            y0, y1 = y, y + foot_h
        else:
            y0, y1 = y - foot_h, y
        g.append_into(glyph, g.rect(cx - foot_w / 2, y0, cx + foot_w / 2, y1))
    return glyph
