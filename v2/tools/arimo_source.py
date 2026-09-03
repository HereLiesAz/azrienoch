"""Extracts 'c'/'e'/'s' from Arimo (vendored at `third_party/arimo/`, SIL
OFL 1.1 -- license copied to `third_party/arimo/OFL.txt`), an open,
metric-compatible Helvetica/Arial workalike -- per the project owner's
direction that these three letters read as Helvetica-derived, without
tracing or extracting actual (proprietary) Helvetica outline data. Same
legal basis as this project's use of Jost and the repository root's use
of Roboto Flex: a freely licensed font, used and modified as its license
explicitly permits.

Arimo ships only as static instances, not a variable font, and Google
Fonts only serves four weights for it (400/500/600/700) -- this module
vendors just Regular (400) and Bold (700), and interpolates/extrapolates
between their point coordinates and advance widths directly, rather
than sampling a real gvar interpolation the source font doesn't have.
Confirmed safe to do this point-for-point (not just plausible): 'c'/'e'/
's' have IDENTICAL point-command signatures between Regular and Bold
(same command sequence, same argument count per command, checked
directly), so corresponding points can be paired by index with no
topology mismatch.

WEIGHT comes from Jost's own original `c`/`e`/`s` (the letters this
project used before switching to Arimo for their SHAPE) -- not from
treating Arimo's own Regular/Bold labels as if they meant the same thing
as this project's `wght` 100-900. They don't: a first version of this
module used a raw linear `frac = (wght-400)/300`, extrapolating past
Bold for `wght`=900 and past Regular for `wght`=100 by the SAME rate
Arimo's own designer chose between Regular and Bold specifically -- but
Jost's own weight range is far more extreme (its 'c' stem, measured by
scanning a horizontal line through the bowl wall, runs 10 units at
wght=100 up to 201 units at wght=900, a ~20x span) than Arimo's own
Regular-to-Bold range (188 to 295 units at the same scan, only ~1.6x) --
confirmed directly, not assumed, by measuring both. Naively mapping
Azrienoch's `wght` value onto Arimo's own weight labels made `c`/`e`/`s`
render 3-4x heavier than the surrounding Jost letters at `wght`=100 (a
Glee design-coherence audit caught this rendering "acorns"/"assess" at
Thin -- confirmed the mismatch with a direct stroke-width measurement,
not just a visual impression).

The fix (`_calibrated_alpha`): measure Jost's own original letter's
stroke width at the target `wght` (via `jost_source`, a real instancer
sample, not extrapolated) and at its own 400 reference, take their
RATIO, and solve for the Arimo interpolation parameter `alpha` that
would scale THAT SAME letter's own Arimo Regular-to-Bold stroke-width
span by that ratio -- calibrated per letter, not shared across `c`/`e`/
`s`: a first version of this fix calibrated once from `c` alone and
reused that single `alpha` for `e`/`s` too, which left them visibly
heavier than `c`/`a`/`o`/`r`/`n` at `wght`=100 anyway, since `e`/`s`
each have their own, different Regular-to-Bold stroke-width delta in
Arimo -- confirmed directly by rendering "acorns" again after the
shared-alpha version and still seeing the mismatch, just on `e`/`s`
instead of all three. At `wght`=400 `alpha` is 0 by construction for
every letter (unchanged from Arimo's own Regular); at 100 and 900 it
extrapolates much farther past Arimo's own [0, 1] range than the old
per-wght fraction did, because it's now chasing Jost's genuinely wider
weight range instead of Arimo's own -- confirmed by rendering the full
wght sweep afterward that this doesn't reintroduce a self-intersection
(the risk `_reorient_cut`'s own docstring already documents for exactly
this kind of large extrapolation; it did surface one, in Arimo's own raw
`e` -- fixed by `_merge_near_duplicate_points` below, not by pulling
back the calibration).

The per-letter scan point (`_CALIBRATION_JOST_Y`) matters as much as the
per-letter alpha: 'e' was first calibrated from a scan through its upper
lobe (above the crossbar), which measures how pinched that lobe's
aperture gets at heavy weight, not the letter's actual stroke width --
Jost's own 'e' aperture there goes from a wide arc at wght=400 to nearly
pinched shut at wght=900, a 4.3x ratio no other scan on 'c'/'e'/'s' comes
close to, and feeding that ratio into Arimo's much gentler Regular-Bold
range demanded alpha=6.8 at wght=900, which broke 'e's counter into two
disconnected slivers (confirmed by rendering it). Rescanning through the
lower bowl instead, clear of both the crossbar and the aperture, gives a
2.4x ratio in line with 'c'/'s' (2.6x/2.1x) and a sane alpha=2.5. A
separate attempt to calibrate the crossbar's own thickness independently
(it has a smaller Regular-Bold delta than the bowl, so the bowl alpha
undershoots how much it should thin at wght=100) was tried and reverted:
moving just the crossbar's own points by a different alpha than their
neighbors created a fold at the junction between them, a worse defect
(visible bowtie) than the mild residual heaviness it was meant to fix.
'e' reads very slightly heavier than 'c'/'o' at wght=100 as a result --
a known, minor residual, not the counter-breaking regression this module
was rewritten to fix.

Rescaled from Arimo's own metrics (UPM 2048, x-height 1082) to Azrienoch
v2's (UPM 1000, x-height 470) via the x-height ratio, the same shortcut
`roboto_s_source.py` uses and for the same reason: all three of these
letters sit entirely within the x-height box in both fonts.
"""

from __future__ import annotations

from pathlib import Path

from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont

from . import jost_source, params

ARIMO_DIR = Path(__file__).resolve().parent.parent / "third_party" / "arimo"
ARIMO_X_HEIGHT = 1082.0
JOST_X_HEIGHT = 470.0
_REGULAR_WGHT, _BOLD_WGHT = 400.0, 700.0
# Per-letter scanline height (Jost's own coordinate space, X_HEIGHT=470)
# for measuring stroke width -- clear of each letter's own terminal cut
# and, for 'e' specifically, its crossbar and counter (a scan through
# either of those measures how pinched the counter/aperture gets at
# heavy weight, not the letter's actual stroke weight -- confirmed by
# scanning Jost's own 'e' at a range of heights: 380 (inside the upper
# lobe, above the crossbar) gives a 4.3x 400-to-900 ratio, while 150
# (through the lower bowl, clear of the crossbar) gives 2.4x, in line
# with 'c' and 's' at 2.6x/2.1x -- the 380 scan was measuring counter
# pinch, not stroke width, and calibrating Arimo's alpha against it is
# what broke 'e's counter into two slivers at wght=900).
_CALIBRATION_JOST_Y = {"c": 235.0, "e": 150.0, "s": 235.0}

_glyphsets_cache: dict[str, object] | None = None


def _glyphsets():
    global _glyphsets_cache
    if _glyphsets_cache is None:
        regular = TTFont(ARIMO_DIR / "Arimo-Regular.ttf")
        bold = TTFont(ARIMO_DIR / "Arimo-Bold.ttf")
        _glyphsets_cache = {
            "regular": (regular.getGlyphSet(), regular.getBestCmap()),
            "bold": (bold.getGlyphSet(), bold.getBestCmap()),
        }
    return _glyphsets_cache


def _record(ch: str, key: str):
    glyphset, cmap = _glyphsets()[key]
    gname = cmap[ord(ch)]
    glyph = glyphset[gname]
    pen = RecordingPen()
    glyph.draw(pen)
    return pen.value, glyph.width


def _merge_near_duplicate_points(pen_value, i1: int, i2: int):
    """Collapses the points at flat indices i1/i2 (in the same order a
    ufoLib2 glyph built from this pen_value would number its points --
    the moveTo point followed by every subsequent command's args, in
    order) to their shared midpoint. Returns a new pen_value; doesn't
    mutate the input tuples (RecordingPen's own args are immutable)."""
    mutable = [(cmd, list(args)) for cmd, args in pen_value]
    flat = [(ci, ai) for ci, (cmd, args) in enumerate(mutable) if cmd != "closePath" for ai in range(len(args))]
    (c1, a1), (c2, a2) = flat[i1], flat[i2]
    x1, y1 = mutable[c1][1][a1]
    x2, y2 = mutable[c2][1][a2]
    midpoint = ((x1 + x2) / 2.0, (y1 + y2) / 2.0)
    mutable[c1][1][a1] = midpoint
    mutable[c2][1][a2] = midpoint
    return [(cmd, tuple(args)) for cmd, args in mutable]


# 'e's own points 18/19 (contour 0) sit ~8-24 units apart (Regular/Bold
# respectively) right where the crossbar's right edge meets the outer
# bowl -- a Jost-'six'/'nine'-style near-duplicate defect (see
# quirks.py's own docstring for that family of bug), present in Arimo's
# raw drawing at every weight but only large enough to fold visibly once
# `_calibrated_alpha` extrapolates past what a plain Regular-Bold
# interpolation would ever reach (confirmed: a Glee stability audit
# caught a visible spike at wght=900 after this module started
# calibrating against Jost's own, much wider, weight range). Fixed once
# here, on both raw masters, so it stays clean at every extrapolated
# alpha instead of being amplified by one.
_NEAR_DUPLICATE_POINTS = {
    "e": (18, 19),
}


def _flatten(pen_value, samples_per_segment: int = 8):
    """Flattens a recorded pen value (TrueType on/off-curve commands,
    including multi-off-curve qCurveTo runs with implied on-curve
    midpoints) into per-contour polylines, for a simple scanline
    thickness measurement -- not for final glyph output."""
    contours = []
    current: list[tuple[float, float]] = []
    current_point = None
    start_point = None
    for cmd, args in pen_value:
        if cmd == "moveTo":
            current_point = args[0]
            start_point = current_point
            current = [current_point]
        elif cmd == "lineTo":
            current.append(args[0])
            current_point = args[0]
        elif cmd == "qCurveTo":
            *offs, on = args
            if on is None:
                on = start_point
            if not offs:
                current.append(on)
                current_point = on
                continue
            anchors = [current_point] + [
                ((offs[j][0] + offs[j + 1][0]) / 2.0, (offs[j][1] + offs[j + 1][1]) / 2.0)
                for j in range(len(offs) - 1)
            ] + [on]
            for j in range(len(offs)):
                p0, ctrl, p1 = anchors[j], offs[j], anchors[j + 1]
                for step in range(1, samples_per_segment + 1):
                    t = step / samples_per_segment
                    x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * ctrl[0] + t ** 2 * p1[0]
                    y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * ctrl[1] + t ** 2 * p1[1]
                    current.append((x, y))
            current_point = on
        elif cmd == "closePath":
            contours.append(current)
            current = []
    return contours


def _ring_wall_width(pen_value, y: float) -> float:
    """The width of the first solid band a horizontal scanline at `y`
    crosses, left to right -- the ring wall's thickness for a bowl
    shape like 'c's, as long as `y` stays clear of its terminal cut."""
    crossings = []
    for points in _flatten(pen_value):
        n = len(points)
        for i in range(n):
            x1, y1 = points[i]
            x2, y2 = points[(i + 1) % n]
            if (y1 <= y < y2) or (y2 <= y < y1):
                t = (y - y1) / (y2 - y1)
                crossings.append(x1 + t * (x2 - x1))
    crossings.sort()
    if len(crossings) < 2:
        raise ValueError(f"scanline at y={y} did not cross a solid ring wall")
    return crossings[1] - crossings[0]


_jost_names: dict[str, str] = {}
_alpha_cache: dict[tuple[str, int], float] = {}


def _calibrated_alpha(ch: str, wght: int) -> float:
    """The Arimo interpolation parameter (0 = Regular, 1 = Bold, outside
    that range an extrapolation) that scales Arimo's own `ch` stroke
    width by the same ratio Jost's own ORIGINAL `ch` stroke width has at
    this `wght` relative to its own 400 reference -- see module
    docstring. Calibrated per letter, not shared across `c`/`e`/`s`: 'c',
    'e' and 's' each have their own Regular-to-Bold stroke-width delta in
    Arimo, so the same alpha doesn't thin/thicken them by the same
    visual ratio -- confirmed directly (a shared, 'c'-only calibration
    left 'e'/'s' visibly heavier than 'c'/'a'/'o'/'r'/'n' at wght=100 in
    a rendered "acorns", even though 'c' alone matched perfectly)."""
    key = (ch, wght)
    if key in _alpha_cache:
        return _alpha_cache[key]

    if ch not in _jost_names:
        _jost_names[ch] = jost_source.glyph_names_for_chars(ch)[ch]
    jost_name = _jost_names[ch]
    scan_y = _CALIBRATION_JOST_Y[ch]

    jost_ref_value, _ = jost_source.extract(jost_name, int(_REGULAR_WGHT), 100)
    jost_ref_width = _ring_wall_width(jost_ref_value, scan_y)
    jost_target_value, _ = jost_source.extract(jost_name, wght, 100)
    jost_target_width = _ring_wall_width(jost_target_value, scan_y)
    ratio = jost_target_width / jost_ref_width

    arimo_y = scan_y / JOST_X_HEIGHT * ARIMO_X_HEIGHT
    reg_value, _ = _record(ch, "regular")
    bold_value, _ = _record(ch, "bold")
    regular_width = _ring_wall_width(reg_value, arimo_y)
    bold_width = _ring_wall_width(bold_value, arimo_y)

    desired_width = regular_width * ratio
    alpha = (desired_width - regular_width) / (bold_width - regular_width)
    _alpha_cache[key] = alpha
    return alpha


def extract(ch: str, wght: int, wdth: int):
    """Returns (pen_value, width) for `ch` ('c', 'e', or 's'),
    interpolated/extrapolated between Arimo Regular (400) and Bold (700)
    using `_calibrated_alpha` (Jost's own weight curve, not Arimo's own
    labels -- see module docstring) and rescaled into Azrienoch v2's
    coordinate space -- same return shape as `jost_source.extract`."""
    reg_value, reg_width = _record(ch, "regular")
    bold_value, bold_width = _record(ch, "bold")
    if ch in _NEAR_DUPLICATE_POINTS:
        i1, i2 = _NEAR_DUPLICATE_POINTS[ch]
        reg_value = _merge_near_duplicate_points(reg_value, i1, i2)
        bold_value = _merge_near_duplicate_points(bold_value, i1, i2)

    alpha = _calibrated_alpha(ch, wght)
    scale = params.X_HEIGHT / ARIMO_X_HEIGHT
    wdth_scale = wdth / 100.0

    out = []
    for (cmd, reg_args), (_, bold_args) in zip(reg_value, bold_value):
        new_args = tuple(
            (
                (rx + (bx - rx) * alpha) * scale * wdth_scale,
                (ry + (by - ry) * alpha) * scale,
            )
            for (rx, ry), (bx, by) in zip(reg_args, bold_args)
        )
        out.append((cmd, new_args))
    width = (reg_width + (bold_width - reg_width) * alpha) * scale * wdth_scale
    return out, width
