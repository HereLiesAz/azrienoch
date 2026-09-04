"""Extracts 's' from Arimo (vendored at `third_party/arimo/`, SIL OFL
1.1 -- license copied to `third_party/arimo/OFL.txt`), an open, metric-
compatible Helvetica/Arial workalike -- per the project owner's
direction that 's' reads as Helvetica-derived, without tracing or
extracting actual (proprietary) Helvetica outline data. Same legal
basis as this project's use of Jost and the repository root's use of
Roboto Flex: a freely licensed font, used and modified as its license
explicitly permits.

'c' and 'e' used to be sourced from here too, interpolated the same
way 's' still is below -- but no amount of matching their advance
width or interpolation shape to Jost's own curve could make their
actual bowl/counter PROPORTIONS agree with 'o's, since Arimo is a
different font with different proportions than Jost. They're now built
directly from this master's own 'o' instead (`ring_derived.py`), which
makes the counters agree by construction. 's' stays here: an S-curve
has no ring/counter to derive from 'o' at all.

Arimo ships only as static instances, not a variable font, and Google
Fonts only serves four weights for it (400/500/600/700) -- this module
vendors just Regular (400) and Bold (700), and interpolates/extrapolates
between their point coordinates and advance widths directly, rather
than sampling a real gvar interpolation the source font doesn't have.
Confirmed safe to do this point-for-point (not just plausible): 's' has
IDENTICAL point-command signatures between Regular and Bold (same
command sequence, same argument count per command, checked directly),
so corresponding points can be paired by index with no topology
mismatch.

WEIGHT comes from Jost's own original 's' (the letter this project used
before switching to Arimo for its SHAPE) -- not from treating Arimo's
own Regular/Bold labels as if they meant the same thing as this
project's `wght` 100-900. They don't: a first version of this module
used a raw linear `frac = (wght-400)/300`, extrapolating past Bold for
`wght`=900 and past Regular for `wght`=100 by the SAME rate Arimo's own
designer chose between Regular and Bold specifically -- but Jost's own
weight range is far more extreme than Arimo's own Regular-to-Bold
range (confirmed directly, not assumed, by measuring stroke width both
ways). Naively mapping Azrienoch's `wght` value onto Arimo's own weight
labels made 's' render several times heavier than the surrounding Jost
letters at `wght`=100 (a Glee design-coherence audit caught this
rendering "acorns"/"assess" at Thin -- confirmed the mismatch with a
direct stroke-width measurement, not just a visual impression).

The fix (`_calibrated_alpha`): measure Jost's own original 's' stroke
width at the target `wght` (via `jost_source`, a real instancer sample,
not extrapolated) and at its own 400 reference, take their RATIO, and
solve for the Arimo interpolation parameter `alpha` that would scale
's' own Arimo Regular-to-Bold stroke-width span by that ratio. At
`wght`=400 `alpha` is 0 by construction (unchanged from Arimo's own
Regular); at 100 and 900 it extrapolates past Arimo's own [0, 1] range,
because it's chasing Jost's genuinely wider weight range instead of
Arimo's own -- confirmed by rendering the full wght sweep that this
doesn't reintroduce a self-intersection (the risk `_reorient_cut`'s own
docstring already documents for exactly this kind of large
extrapolation).

Rescaled from Arimo's own metrics (UPM 2048, x-height 1082) to Azrienoch
v2's (UPM 1000, x-height 470) via the x-height ratio, the same shortcut
`roboto_s_source.py` uses and for the same reason: 's' sits entirely
within the x-height box in both fonts.

`wdth` != 100 goes through `condense.condense_x` (a per-x, ink-density
weighted compression, not a flat scale -- see that module's docstring)
applied AFTER the weight interpolation and x-height rescale above, same
as `jost_source.py` does for every other letter.
"""

from __future__ import annotations

from pathlib import Path

from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont

from . import condense, jost_source, params

ARIMO_DIR = Path(__file__).resolve().parent.parent / "third_party" / "arimo"
ARIMO_X_HEIGHT = 1082.0
JOST_X_HEIGHT = 470.0
_REGULAR_WGHT, _BOLD_WGHT = 400.0, 700.0
# Scanline height (Jost's own coordinate space, X_HEIGHT=470) for
# measuring 's' own stroke width, clear of its terminal cuts.
_CALIBRATION_JOST_Y = 235.0

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
    shape like 's's, as long as `y` stays clear of its terminal cut."""
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


_masters_cache: tuple | None = None


def _prepared_masters():
    """(reg_value, reg_width, bold_value, bold_width) for 's', cached
    (both masters are the same regardless of `wght`/`wdth`)."""
    global _masters_cache
    if _masters_cache is None:
        _masters_cache = (*_record("s", "regular"), *_record("s", "bold"))
    return _masters_cache


def _interpolate_at(alpha: float):
    """Returns (pen_value, width) for 's' in Arimo's own native
    coordinate space (UPM 2048), blending/extrapolating Regular -> Bold
    by `alpha` (0 = Regular, 1 = Bold) via a plain per-point Cartesian
    blend -- 's' is an S-curve with no single center a "distance from
    here, angle from here" description means anything for, unlike the
    round bowls `ring_derived.py` now builds 'c'/'e' from directly."""
    reg_value, reg_width, bold_value, bold_width = _prepared_masters()
    out = [
        (
            cmd,
            tuple(
                (rx + (bx - rx) * alpha, ry + (by - ry) * alpha)
                for (rx, ry), (bx, by) in zip(reg_args, bold_args)
            ),
        )
        for (cmd, reg_args), (_, bold_args) in zip(reg_value, bold_value)
    ]
    return out, reg_width + (bold_width - reg_width) * alpha


_jost_name_cache: str | None = None


def _jost_name() -> str:
    global _jost_name_cache
    if _jost_name_cache is None:
        _jost_name_cache = jost_source.glyph_names_for_chars("s")["s"]
    return _jost_name_cache


_alpha_cache: dict[int, float] = {}


def _calibrated_alpha(wght: int) -> float:
    """The Arimo interpolation parameter (0 = Regular, 1 = Bold, outside
    that range an extrapolation) that scales Arimo's own 's' stroke
    width by the same ratio Jost's own ORIGINAL 's' stroke width has at
    this `wght` relative to its own 400 reference -- see module
    docstring."""
    if wght in _alpha_cache:
        return _alpha_cache[wght]

    jost_name = _jost_name()
    scan_y = _CALIBRATION_JOST_Y

    jost_ref_value, _ = jost_source.extract(jost_name, int(_REGULAR_WGHT), 100)
    jost_ref_width = _ring_wall_width(jost_ref_value, scan_y)
    jost_target_value, _ = jost_source.extract(jost_name, wght, 100)
    jost_target_width = _ring_wall_width(jost_target_value, scan_y)
    ratio = jost_target_width / jost_ref_width

    arimo_y = scan_y / JOST_X_HEIGHT * ARIMO_X_HEIGHT
    regular_width = _ring_wall_width(_interpolate_at(0.0)[0], arimo_y)
    bold_width = _ring_wall_width(_interpolate_at(1.0)[0], arimo_y)

    desired_width = regular_width * ratio
    alpha = (desired_width - regular_width) / (bold_width - regular_width)
    _alpha_cache[wght] = alpha
    return alpha


def extract(ch: str, wght: int, wdth: int):
    """Returns (pen_value, width) for 's', interpolated/extrapolated
    between Arimo Regular (400) and Bold (700) using `_calibrated_alpha`
    (Jost's own weight curve, not Arimo's own labels -- see module
    docstring) and rescaled into Azrienoch v2's coordinate space -- same
    return shape as `jost_source.extract`. `ch` is always "s"; kept as a
    parameter for a uniform call signature with `jost_source.extract`."""
    alpha = _calibrated_alpha(wght)
    pen_value, width = _interpolate_at(alpha)
    scale = params.X_HEIGHT / ARIMO_X_HEIGHT

    out = [
        (cmd, tuple((x * scale, y * scale) for x, y in args))
        for cmd, args in pen_value
    ]
    width *= scale

    if wdth != 100:
        out, width = condense.condense_x(out, width, wdth / 100.0)
    return out, width
