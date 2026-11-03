"""The SERF axis: adding slab feet to Jost's sans letterforms.

Rather than the point-insertion approach this module tried first:
instead of relocating a stem's own corner points, this detects a flat
terminal run once on a reference instance and, at every
master, APPENDS a separate rectangle contour there -- collapsed to a
hairline at SERF=0, a full slab at SERF=100 -- wound the same direction
as the stem's own contour so it merges as more solid ink rather than
needing any hole/winding logic. This sidesteps the whole class of bug
the point-insertion version had (see git history): appending a same-
wound rectangle can only ever add ink, never accidentally flip a
contour's fill relationship with something else.

Key insight: a flat run's SIDE only gets widened when the *adjacent*
segment is a long, straight, genuine stem side -- not a short connector
leading into a curve (an arch letter's spring, or a stem transitioning
into a bowl). That length threshold is exactly what a first, more
complicated version of this file was missing when it grew a spurious
extra foot on 'n' where its left stem's short run-up to the arch
(~70 units) happens to end flat and close enough to the x-height
ballpark to look like a genuine terminal -- `MIN_STEM_LEN` cleanly
rejects anything that short as "not a real stem", no per-contour-
extreme special-casing needed.

Per the project owner's direction, serifs grow only from RIGHT-ANGLED
terminals -- a flat run whose flaring end meets a long, straight,
vertical stem edge (a diagonal leg, a curve or an arch spring is not a
right angle) -- and there is exactly ONE serif per glyph:

- UPPERCASE (and `LEFT_LOWER` = b, k): the leftmost stem's lower-left
  corner, flaring left only (B D E F H I K L P R T Y ...). All caps use
  the same serif size, measured off that master's own `I` stem.
- Every other lowercase letter (and digits): the rightmost stem's
  bottom-right corner, flaring right only (a d f h i l m n r t u ...).
- `TOP_SIDE` p, q: no foot; one serif at the x-height top of the stem,
  flaring outward (p upper-left, q upper-right).
- Nothing at ascender/cap tops and nothing on descenders; `NO_SERIF`
  (N Q g j y) get none; A, K's/R's legs, X, x, v, w, z have no
  right-angled terminal so none grow.
- `BOTH_SIDES` (M) is the one exception: a serif at each foot, flaring
  outward, even though its legs are slanted.
- '1' is exempt (`detect_feet`/`apply_feet` keep its original
  behavior: a lone stem flares both ways at the baseline).
- '7' gets a crossbar "dash" through the middle of its diagonal
  instead (see `apply_seven_dash`), growing with SERF like a foot.

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
MEASURE_TOLERANCE = 16.0  # units: looser, per-master measurement (thin masters put a stem top ~10 above the guide)
MIN_RUN = 10.0  # units: ignore tiny flat runs (noise, not a real stem)
MAX_RUN = 200.0  # units: ignore wide runs (crossbars/bowls, not a stem) -- Jost's own stems run roughly 75-165 units wide
MIN_FOOT_H = 1.0  # units: SERF=0 foot height -- a hairline, not literally 0
MEASURE_MIN_RUN = 1.0  # units: noise floor when MEASURING an already-detected stem at a master (see `_flat_runs`)
MIN_STEM_LEN = 150.0  # units: how long an adjacent straight run must be to count as a real stem side

STEM_TOP = 460.0  # units: where Jost's FLAT stem tops sit (x-height 470 is the round overshoot)
LEFT_LOWER = set("bk")  # lowercase letters whose one serif flares left (all caps do too)
TOP_SIDE = {"p": -1, "q": 1}  # x-height stem-top serif and the side it flares to
BOTH_SIDES = set("M")  # the one exception: serifs at both feet, even though the legs are slanted
NO_SERIF = set("NQgjy")  # no serif at all -- see module docstring
EXEMPT = {"1"}  # keeps the original both-ways baseline foot
SINGLE_STORY = set("acemnorsuvwxz")  # only used by the '1'-exempt legacy flare logic
DETECT_MAX_RUN = 900.0  # units: corner detection also accepts long runs (B/D/E/L bottoms)
SERIF_W_FRAC = 0.30  # serif extension beyond the stem, as a fraction of the stem width
SERIF_H_FRAC = 0.35  # serif height, as a fraction of the stem width
DEFAULT_STEM = 80.0  # units: fallback stem width if `stem_width` finds nothing


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


def _flat_runs(glyph, right_angled_only: bool = False, min_run: float = MIN_RUN, max_run: float = MAX_RUN):
    """Yields (contour, x0, x1, y, is_top_guide, left_ext, right_ext) for
    every flat stem-terminal candidate (only right-angled ones when
    `right_angled_only`). left_ext/right_ext say whether
    that end connects to a long straight stem (safe to widen a foot
    into) versus a short run into a curve (must not widen -- would
    notch a counter).

    `min_run` defaults to `MIN_RUN`, the noise floor for DETECTING a
    stem on the wght=400 reference instance. Measuring an
    already-detected stem at another master (`_actual_stem_width`)
    passes a much smaller floor instead: a Thin Condensed stem is
    genuinely narrower than `MIN_RUN` (8 units at wght=100/wdth=75),
    and filtering it out there silently dropped every Thin Condensed
    foot onto `apply_feet`'s fallback width -- several times the real
    stem, and off-center."""
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
            if run < min_run or run > max_run:
                continue
            y = (a.y + b.y) / 2
            prev_pt = pts[(i - 1) % n]
            next_pt = pts[(i + 2) % n]
            if right_angled_only:
                # Both adjacent sides must be straight vertical lines: a
                # true right angle at each end of the flat run.
                if a.type != "line" or next_pt.type != "line":
                    continue
                if abs(prev_pt.x - a.x) > 1.5 or abs(next_pt.x - b.x) > 1.5:
                    continue
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


def _vertical_edge(p, q) -> bool:
    return abs(p.x - q.x) <= 1.5 and _seg_len(p, q) >= MIN_STEM_LEN


def _runs(glyph, min_run: float, max_run: float):
    """Yields (contour, x0, x1, y, is_top, left_vertical, right_vertical)
    for every flat horizontal run; `*_vertical` says that end meets a
    long straight vertical edge (a true right angle)."""
    for contour in glyph.contours:
        pts = list(contour.points)
        n = len(pts)
        for i in range(n):
            a, b = pts[i], pts[(i + 1) % n]
            if a.type is None or b.type is None or b.type != "line":
                continue
            if abs(a.y - b.y) > 1.0:
                continue
            if not (min_run <= abs(a.x - b.x) <= max_run):
                continue
            prev_pt, next_pt = pts[(i - 1) % n], pts[(i + 2) % n]
            a_v = a.type == "line" and _vertical_edge(prev_pt, a)
            b_v = next_pt.type == "line" and _vertical_edge(b, next_pt)
            left_v, right_v = (a_v, b_v) if a.x <= b.x else (b_v, a_v)
            yield contour, min(a.x, b.x), max(a.x, b.x), (a.y + b.y) / 2, not (a.x < b.x), left_v, right_v


def _legacy_specs(reference_glyph, guides: dict[str, float], ch: str) -> list[dict]:
    """The pre-rewrite spec list (both-ways baseline foot), kept only for
    the exempt '1'. `side` 0 selects `apply_feet`'s legacy path."""
    width = reference_glyph.width or 1
    specs, seen = [], set()
    for contour, x0, x1, y, is_top, left_ext, right_ext in _flat_runs(reference_glyph):
        guide_name = min(guides, key=lambda k: abs(guides[k] - y))
        if abs(guides[guide_name] - y) > TOLERANCE or not (left_ext or right_ext):
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
            side=0,
        ))
    return _apply_outward_flares(specs, False)


def detect_feet(reference_glyph, guides: dict[str, float], ch: str = "") -> list[dict]:
    """At most ONE foot spec per glyph (fractional corner x, guide name,
    direction, flare side and the stem contour's own winding sign) from
    one reference instance -- reused as-is (only re-scaled) at every
    master, so every master's glyph gets identical topology."""
    if not guides:
        return []
    base = params.base_letter(ch)
    if base in EXEMPT:
        return _legacy_specs(reference_glyph, guides, ch)
    sides = (-1, 1) if base in BOTH_SIDES else (TOP_SIDE.get(base, -1 if (base.isupper() or base in LEFT_LOWER) else 1),)
    width = reference_glyph.width or 1
    found = []
    for side in sides:
        best = None
        for contour, x0, x1, y, is_top, left_v, right_v in _runs(reference_glyph, MIN_RUN, DETECT_MAX_RUN):
            guide_name = min(guides, key=lambda k: abs(guides[k] - y))
            if abs(guides[guide_name] - y) > TOLERANCE:
                continue
            if base not in BOTH_SIDES and not (left_v if side < 0 else right_v):
                continue
            cx = x0 if side < 0 else x1
            if best is None or (cx < best["cx"] if side < 0 else cx > best["cx"]):
                best = dict(
                    cx=cx,
                    x_frac=cx / width,
                    run_frac=(x1 - x0) / width,
                    guide=guide_name,
                    direction=-1 if is_top else 1,
                    side=side,
                    positive_winding=_signed_area(contour.points) >= 0,
                )
        if best is not None:
            best.pop("cx")
            found.append(best)
    return found


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
    # Wider/narrower limits than detection's: at Black a stem is ~205 units
    # (over MAX_RUN) and at Thin-Condensed ~9 (under MIN_RUN). With the
    # detection limits the measurement skipped the right stem at those
    # masters and snapped to the wrong stem -- the interpolated foot then
    # swept across the whole counter between masters (the 'n' bug).
    for _contour, x0, x1, y, _is_top, _left_ext, _right_ext in _flat_runs(glyph, min_run=3.0, max_run=320.0):
        if abs(y - guide_y) > MEASURE_TOLERANCE:
            continue
        mid = (x0 + x1) / 2.0
        dist = abs(mid - x_hint)
        if best_dist is None or dist < best_dist:
            best_dist = dist
            best = (mid, x1 - x0)
    return best


def stem_width(glyph) -> float:
    """Baseline stem width of a plain stem glyph (`I` or `l`) at this
    master: the width of its leftmost flat baseline run."""
    runs = [(x0, x1 - x0) for _c, x0, x1, y, _t, _l, _r in _runs(glyph, 3.0, 400.0) if abs(y) <= MEASURE_TOLERANCE]
    return min(runs)[1] if runs else DEFAULT_STEM


def _corner_x(glyph, guide_y: float, side: int, x_hint: float):
    """(corner x, run length) of the flat run at `guide_y` whose `side`
    end (left for -1, right for +1) is nearest `x_hint`, measured off
    THIS master's own outline -- never another stem's."""
    best = None
    for _c, x0, x1, y, _t, _l, _r in _runs(glyph, 3.0, 2000.0):
        if abs(y - guide_y) > MEASURE_TOLERANCE:
            continue
        cx = x0 if side < 0 else x1
        d = abs(cx - x_hint)
        if best is None or d < best[0]:
            best = (d, cx, x1 - x0)
    return None if best is None else (best[1], best[2])


def apply_feet(glyph, foot_specs: list[dict], guides: dict[str, float], serif_amount: float,
               stem_w: float | None = None) -> None:
    """Appends one rectangle contour per foot spec, always (even at
    serif_amount=0 -- a collapsed hairline inside the stem, not a
    skipped contour, so every master keeps identical topology).

    One-sided specs (`side` +-1) anchor at the stem's own corner as
    measured at THIS master: the rectangle spans from `overlap` inside
    the stem to `extra` beyond the corner, and its size is a fixed
    fraction of `stem_w` (the master's own `I`/`l` stem width), so every
    glyph of a case gets the identical serif. `side` 0 (the exempt '1')
    keeps the legacy run-wide, both-ways foot.

    Every spec is measured BEFORE any rectangle is appended: appending
    mutates `glyph`, and a new rectangle's edge sits exactly on the guide,
    so interleaving could measure an earlier spec's own foot.
    """
    width = glyph.width or 1
    measurements = []
    for spec in foot_specs:
        if spec["guide"] not in guides:
            measurements.append(None)
            continue
        y = guides[spec["guide"]]
        hint = spec["x_frac"] * width
        if spec["side"] == 0:
            measured = _actual_stem_width(glyph, y, hint)
            if measured is None:
                measured = (hint, max(spec["run_frac"] * width, 4.0))
            else:
                measured = (measured[0], max(measured[1], 4.0))
        else:
            measured = _corner_x(glyph, y, spec["side"], hint)
            if measured is None:
                measured = (hint, max(spec["run_frac"] * width, 4.0))
        measurements.append(measured)

    t = serif_amount / 100.0
    for spec, measurement in zip(foot_specs, measurements):
        if measurement is None:
            continue
        y = guides[spec["guide"]]
        if spec["side"] == 0:
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
            foot_h = min(MIN_FOOT_H * (1 - t) + (run_w * 0.35) * t, run_w)
        else:
            corner, run_len = measurement
            w = max(stem_w or run_len, 4.0)
            overlap = min(run_len, w)
            extra = t * SERIF_W_FRAC * w
            if spec["side"] < 0:
                x0, x1 = corner - extra, corner + overlap
            else:
                x0, x1 = corner - overlap, corner + extra
            foot_h = min(MIN_FOOT_H * (1 - t) + SERIF_H_FRAC * w * t, w)
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
        "stemtop": STEM_TOP,
    }
    ch = params.base_letter(ch)
    if ch in NO_SERIF:
        return {}
    allowed = {"xheight", "stemtop"} if ch in TOP_SIDE else {"baseline"}
    return {name: y for name, y in all_guides.items() if name in allowed}


def apply_seven_dash(glyph, serif_amount: float) -> None:
    """A horizontal dash through the middle of '7's diagonal (like a
    backwards f's crossbar). Always appends one rectangle -- at SERF=0 a
    1-unit hairline inset inside the diagonal's own band (invisible), at
    SERF=100 as thick as 7's own top bar and reaching that same
    thickness past both sides of the diagonal -- so every master keeps
    identical topology. Uses seven's own 6-point contour: points 0/1 the
    top bar's underside, 2/3 the diagonal's bottom-left/bottom-right, 4
    the top-right tip (checked at wght 100/400/900)."""
    pts = glyph.contours[0].points
    top_bar_bottom = pts[0].y
    thickness = pts[5].y - top_bar_bottom
    yc = top_bar_bottom / 2.0
    # Diagonal band edges at height yc: left edge runs pts[2] -> pts[1],
    # right edge runs pts[3] -> pts[4].
    left = pts[2].x + (pts[1].x - pts[2].x) * (yc - pts[2].y) / (pts[1].y - pts[2].y)
    right = pts[3].x + (pts[4].x - pts[3].x) * (yc - pts[3].y) / (pts[4].y - pts[3].y)
    t = serif_amount / 100.0
    ext = thickness * t
    inset = 1.0 * (1 - t)
    h = MIN_FOOT_H * (1 - t) + thickness * t
    x0, x1 = left - ext + inset, right + ext - inset
    y0, y1 = yc - h / 2.0, yc + h / 2.0
    pen = glyph.getPointPen()
    pen.beginPath()
    for x, y_ in _rect_points(x0, y0, x1, y1, _signed_area(pts) >= 0):
        pen.addPoint((round(x, 2), round(y_, 2)), segmentType="line")
    pen.endPath()
