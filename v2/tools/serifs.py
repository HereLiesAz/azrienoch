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
feet grow from, and which DIRECTION each foot is allowed to flare,
follows the shape of handwriting rather than "widen wherever there's
room":

- A single-story letter (`SINGLE_STORY`) gets exactly TWO feet, never
  one per stem: the x-height-top of its LEFTMOST stem, flaring only
  left/backward, and the baseline of its RIGHTMOST stem, flaring only
  right/forward -- not a foot on every flat terminal the letter happens
  to have.
- A letter with an ascender (`ASCENDER`) gets a foot only at the
  baseline -- never at the ascender/cap top.
- `g`/`p`/`q` get a foot only at the x-height top instead of the
  baseline/descender (`DESCENDER_TOP`) -- the opposite end from every
  other descender-bearing letter, per the project owner's direction.
- `j`'s own descender hook is curved, not a flat stem (like `g`'s own
  hook -- see below), so it's grouped with `DESCENDER_BOTTOM` mostly for
  documentation; `detect_feet` finds nothing there in practice.
- `y` gets a foot at BOTH the x-height top and its own descender depth.
- Uppercase and digits get a foot only at the baseline, never the top.

For every letter EXCEPT single-story ones, every qualifying stem gets
its own foot, but each one flares only AWAY from the letter's other
stems, never toward them: the leftmost stem at a given guide flares only
left, the rightmost only right, a stem that's the only one at that guide
flares both ways (nothing to protect on either side), and any stem
strictly between two others gets no flare at all. This is what fixes an
early version of this file's own `H`/`R`: both of `H`'s stems used to
flare both ways whenever both sides were geometrically safe to widen,
which included flaring the LEFT stem rightward -- into its own counter,
not away from it.

Diagonal-only strokes (v/w/x, A/V/W/X/K's legs) and curved terminals
(g's own descender hook) have no flat stem run to grow a foot from at
all and are simply left alone -- confirmed by inspection, not assumed:
`detect_feet` finds nothing there because there's nothing matching its
own definition of a stem terminal, not because they're special-cased
out.

The same is true of every fully round letter in `SINGLE_STORY` --
`o`/`c`/`e`/`s` -- even though the class as a whole is documented above
as "gets exactly TWO feet": a round bowl has no flat run anywhere on it
either, at any weight, so `detect_feet` finds nothing to grow a foot
from for these four specifically, the same structural limitation as
g's hook, not a bug (confirmed directly: `o`'s own point count doesn't
change one bit between SERF=0 and SERF=100). A Glee design-coherence
audit flagged `c`/`e`/`s` getting no feet as suspicious since they're
declared SINGLE_STORY; `o` -- never flagged, and never expected to grow
feet either -- has always behaved identically, which is what confirms
this is round letters' own consistent limitation rather than something
introduced by `c`/`e`/`s` being Arimo-sourced.
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
DESCENDER_TOP = set("gpq")  # foot at x-height, not the descender -- see module docstring
DESCENDER_BOTTOM = {"j"}
Y_BOTH = {"y"}


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


def _apply_outward_flares(specs: list[dict], single_story: bool) -> list[dict]:
    """Restricts each spec's flare direction to face away from this
    glyph's OTHER stems at the same guide, per the module docstring:
    the leftmost stem at a guide flares only left, the rightmost only
    right, a lone stem at that guide flares both ways, and (for
    non-single-story letters) anything strictly in between flares
    neither. `left_ext`/`right_ext` already say whether a side is
    geometrically SAFE to widen at all (a genuine long stem there, not a
    short curve connector) -- this only ever narrows that, never
    widens it back past what was already unsafe.

    Single-story letters get a stricter version: only the very leftmost
    x-height-guide stem and the very rightmost baseline-guide stem keep
    a foot at all -- every other candidate is dropped outright, not just
    unflared, since single-story letters get exactly two feet total.
    """
    by_guide: dict[str, list[int]] = {}
    for i, spec in enumerate(specs):
        by_guide.setdefault(spec["guide"], []).append(i)

    keep: list[int] = []
    for guide, idxs in by_guide.items():
        idxs.sort(key=lambda i: specs[i]["x_frac"])
        if single_story:
            if guide == "xheight":
                i = idxs[0]
                specs[i]["right_ext"] = False
                keep.append(i)
            elif guide == "baseline":
                i = idxs[-1]
                specs[i]["left_ext"] = False
                keep.append(i)
            continue
        for pos, i in enumerate(idxs):
            want_left = pos == 0
            want_right = pos == len(idxs) - 1
            specs[i]["left_ext"] = specs[i]["left_ext"] and want_left
            specs[i]["right_ext"] = specs[i]["right_ext"] and want_right
            keep.append(i)
    return [specs[i] for i in sorted(keep)]


def detect_feet(reference_glyph, guides: dict[str, float], ch: str = "") -> list[dict]:
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
    # Same base-letter resolution as `guides_for` -- an accented single-
    # story letter still gets exactly two feet, not one per stem.
    return _apply_outward_flares(specs, params.base_letter(ch) in SINGLE_STORY)


def _rect_points(x0, y0, x1, y1, positive_winding: bool):
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]  # counter-clockwise (positive signed area)
    if not positive_winding:
        pts.reverse()
    return pts


def _actual_stem_width(glyph, guide_y: float, x_hint: float) -> tuple[float, float] | None:
    """The REAL flat-run width (and center x) at this master, measured
    directly off `glyph`'s own current outline at (guide_y, near
    x_hint) -- not `detect_feet`'s reference-instance fraction rescaled
    by this master's overall advance width.

    Those are NOT the same quantity, and treating them as
    interchangeable was a real, visible bug: a stem's own stroke
    thickness shrinks with `wght` much faster than the glyph's overall
    advance width does (a Thin letter is only modestly narrower
    end-to-end, even though its stems are dramatically thinner), so
    `run_frac * this_master's_width` overshoots the actual Thin stem
    width by a wide margin -- confirmed directly by comparing this
    function's own measurement against that computation at wght=100
    for several stems, off by roughly 2x. The base foot rectangle
    (before any flare) was sized to that overshot width, so even at
    `SERF`=0 (meant to be an invisible hairline) it already sat wider
    than the actual thin stem beneath it, poking out to both sides --
    exactly the visible defect reported directly. Returns None if no
    matching run is found (shouldn't normally happen, since
    `detect_feet` found one here on the reference instance and this
    project's own masters share point topology), letting the caller
    fall back to the old approximation rather than crash.
    """
    best = None
    best_dist = None
    for _contour, x0, x1, y, _is_top, _left_ext, _right_ext in _flat_runs(glyph):
        if abs(y - guide_y) > TOLERANCE:
            continue
        mid = (x0 + x1) / 2.0
        dist = abs(mid - x_hint)
        if best_dist is None or dist < best_dist:
            best_dist = dist
            best = (mid, x1 - x0)
    return best


def apply_feet(glyph, foot_specs: list[dict], guides: dict[str, float], serif_amount: float) -> None:
    """Appends one rectangle contour per foot spec, always (even at
    serif_amount=0 -- a collapsed hairline, not a skipped contour, so
    every master keeps identical topology).

    The foot's own width and height are both sized off THIS master's
    actual stem thickness (`_actual_stem_width`), not the reference
    instance's fraction-of-advance-width approximation -- see that
    function's own docstring for why those diverge badly at weights
    away from the reference. Foot height is additionally hard-capped at
    the stem's own actual width: a serif foot's stroke-perpendicular
    extension should never rival or exceed the stroke it's growing
    from, and the old, uncapped formula (a fixed fraction of the
    wrongly-overshot reference-based width) could and did exceed a
    thin stem's real width entirely, per the project owner's own direct
    observation, not just poke out to the sides.

    Every spec's actual stem width is measured BEFORE any foot is
    appended, all at once -- appending a foot rectangle mutates
    `glyph`'s own contours, and its own flat top/bottom edge sits
    exactly ON the guide line by construction, so measuring stem by
    stem interleaved with appending risks a later spec's measurement
    picking up an EARLIER spec's own just-appended foot as if it were
    a second stem at that guide (confirmed directly: two same-guide
    stems on one letter reproduced exactly this after the first foot
    landed, dodged the same way here).
    """
    width = glyph.width or 1
    measurements = []
    for spec in foot_specs:
        if spec["guide"] not in guides:
            measurements.append(None)
            continue
        y = guides[spec["guide"]]
        cx_hint = spec["x_frac"] * width
        measured = _actual_stem_width(glyph, y, cx_hint)
        if measured is not None:
            cx, run_w = measured
            run_w = max(run_w, 4.0)
        else:
            cx = cx_hint
            run_w = max(spec["run_frac"] * width, 4.0)
        measurements.append((cx, run_w))

    for spec, measurement in zip(foot_specs, measurements):
        if spec["guide"] not in guides:
            continue
        y = guides[spec["guide"]]
        cx, run_w = measurement
        extra = serif_amount * (run_w * 0.3) / 100.0
        x0, x1 = cx - run_w / 2, cx + run_w / 2
        left_ext, right_ext = spec["left_ext"], spec["right_ext"]
        if left_ext and right_ext:
            x0, x1 = x0 - extra / 2, x1 + extra / 2
        elif left_ext:
            x0 -= extra
        elif right_ext:
            x1 += extra
        # A flat "+ MIN_FOOT_H" on top of the proportional term (the old
        # formula) is negligible for a thick stem but NOT for a thin one
        # -- confirmed directly by computing the actual ratio at both
        # extremes: Black's foot came out to 35.5% of its own stem width,
        # Thin's to 42.1%, purely because the same flat +1 unit is ~1% of
        # Black's ~78-unit height but ~17% of Thin's ~6-unit height. That
        # is a real, measurable reason Thin's foot reads disproportionately
        # taller relative to its own (thin) stroke than Black's does
        # relative to its own -- exactly the opposite of decreasing height
        # at the thinnest weight specifically, which is what was asked
        # for. Fixed by interpolating from the hairline (serif_amount=0)
        # straight to the fully-proportional target (serif_amount=100)
        # instead of always adding the hairline as a bonus on top: at full
        # SERF, height is now EXACTLY run_w's own 0.35 fraction at every
        # weight, thin included, matching Black's own already-correct
        # ratio instead of exceeding it there.
        t = serif_amount / 100.0
        foot_h = MIN_FOOT_H * (1 - t) + (run_w * 0.35) * t
        foot_h = min(foot_h, run_w)  # never taller than the stem it grows from
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
    apply_feet both just take "the guides that apply here".

    `ch` is resolved to its plain-Latin base (`params.base_letter`)
    before the class lookup below, so an accented letter (e.g. 'ē')
    gets the same guide set as its base ('e') rather than falling
    through to the uppercase/digit default -- a diacritic doesn't
    change where a letter's own stem terminals sit. Cyrillic and
    unaccented punctuation/digits don't decompose to a Latin base and
    so keep the baseline-only default, same as uppercase."""
    all_guides = {
        "baseline": 0.0,
        "xheight": params.X_HEIGHT,
        "ascender": params.ASCENDER,
        "cap": params.CAP_HEIGHT,
        "descender": glyph_min_y,
    }
    ch = params.base_letter(ch)
    if ch in SINGLE_STORY:
        allowed = {"baseline", "xheight"}
    elif ch in ASCENDER:
        allowed = {"baseline"}
    elif ch in DESCENDER_TOP:
        allowed = {"xheight"}
    elif ch in Y_BOTH:
        allowed = {"xheight", "descender"}
    elif ch in DESCENDER_BOTTOM:
        allowed = {"descender"}
    else:
        allowed = {"baseline"}  # uppercase and digits
    return {name: y for name, y in all_guides.items() if name in allowed}
