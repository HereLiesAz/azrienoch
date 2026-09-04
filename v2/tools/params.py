"""Axis model for Azrienoch v2.

Glyph outlines come from the vendored Jost variable font (see
jost_source.py). This module is the single place that defines the axis
grid Jost gets sampled at, and the vertical metrics the build asserts
(Jost's own cap-height/x-height already happen to be fixed across its
wght range, confirmed against the vendored font directly -- see
README.md -- so no override is needed there).
"""

from __future__ import annotations

UPM = 1000

# Vertical metrics are fixed across the whole wght range on purpose: a
# heavy and a light line share the same cap-height/x-height/baseline, so
# mixed-weight multi-line layouts (the whole point of this font) align
# without any per-weight size compensation.
#
# These are Jost's own measured values (confirmed directly against the
# vendored font's actual glyph coordinates, not assumed): H's cap is
# exactly 700; o/r/m's x-height is 470 (u's own stem reaches only 460 --
# a ~10-unit letter-to-letter variance Jost's own design already has,
# not something to paper over with a falsely-precise shared constant);
# b/d/l's ascender is 780; g's descender is -230 (q's own is -220 --
# same kind of small per-letter variance, which is why serifs.py reads
# each descender glyph's own lowest point directly rather than using
# this constant to detect anything).
CAP_HEIGHT = 700
X_HEIGHT = 470
ASCENDER = 780
DESCENDER = -230

WGHT_MIN, WGHT_MAX, WGHT_DEFAULT = 100, 900, 400
WDTH_MIN, WDTH_MAX, WDTH_DEFAULT = 75, 100, 100
SERF_MIN, SERF_MAX, SERF_DEFAULT = 0, 100, 0  # sans by default
GRAD_MIN, GRAD_MAX, GRAD_DEFAULT = -50, 50, 0  # same range v1 passes through from Roboto Flex's own

AXES = [
    {"tag": "wght", "name": "Weight", "minimum": WGHT_MIN, "default": WGHT_DEFAULT, "maximum": WGHT_MAX},
    {"tag": "wdth", "name": "Width", "minimum": WDTH_MIN, "default": WDTH_DEFAULT, "maximum": WDTH_MAX},
    {"tag": "SERF", "name": "Serif", "minimum": SERF_MIN, "default": SERF_DEFAULT, "maximum": SERF_MAX},
    {"tag": "GRAD", "name": "Grade", "minimum": GRAD_MIN, "default": GRAD_DEFAULT, "maximum": GRAD_MAX},
]

# One master at every grid corner plus the wght midpoint, so the default
# location (400, 100, 0, 0) is itself a real source -- required for a
# well-formed designspace -- and wght gets a bend partway through its
# range rather than a single straight interpolation.
WGHT_SAMPLES = (WGHT_MIN, WGHT_DEFAULT, WGHT_MAX)
WDTH_SAMPLES = (WDTH_MIN, WDTH_MAX)
SERF_SAMPLES = (SERF_MIN, SERF_MAX)
GRAD_SAMPLES = (GRAD_MIN, GRAD_DEFAULT, GRAD_MAX)

MASTER_GRID = [
    (wght, wdth, serf, grad)
    for wght in WGHT_SAMPLES
    for wdth in WDTH_SAMPLES
    for serf in SERF_SAMPLES
    for grad in GRAD_SAMPLES
]
DEFAULT_LOCATION = (WGHT_DEFAULT, WDTH_DEFAULT, SERF_DEFAULT, GRAD_DEFAULT)

# Human-facing names for each axis stop actually sampled as a master
# (WGHT_SAMPLES/WDTH_SAMPLES/SERF_SAMPLES above) -- feeds both the STAT
# table's axis-value labels (so a design app shows a real "Weight"/
# "Width"/"Serif" style picker instead of a raw numeric slider) and the
# fvar named instance generated at every master grid point below. A
# variable font with no named instances still interpolates its full
# range correctly, but most apps' style pickers list only the named
# instances -- with none defined beyond the implicit default, that's
# "Regular" and nothing else, regardless of how many masters the font
# actually has (confirmed: this was v2's own bug -- MASTER_GRID already
# had 12 real masters spanning Thin-to-Black, Normal-to-Condensed,
# Sans-to-Slab, but `designspace_build.py` never turned any of them
# into an `InstanceDescriptor`, so only Regular ever showed up outside
# a raw axis-slider view).
WGHT_NAMES = {WGHT_MIN: "Thin", WGHT_DEFAULT: "Regular", WGHT_MAX: "Black"}
WDTH_NAMES = {WDTH_MAX: "Normal", WDTH_MIN: "Condensed"}
SERF_NAMES = {SERF_MIN: "Sans", SERF_MAX: "Slab"}
# Same pattern the repository root's own v1 pipeline uses for its own
# (Roboto Flex-native) GRAD axis: the default grade doesn't add a word
# to the instance name at all (not even an elided one -- there's no
# "Grade0" to elide), only the low/high extremes do.
GRAD_NAMES = {GRAD_MIN: "GradeLow", GRAD_DEFAULT: "", GRAD_MAX: "GradeHigh"}


def style_name(wght: int, wdth: int, serf: int, grad: int = GRAD_DEFAULT) -> str:
    return f"Wght{wght}_Wdth{wdth}_Serf{serf}_Grad{grad}"


def instance_style_name(wght: int, wdth: int, serf: int, grad: int = GRAD_DEFAULT) -> str:
    """The public subfamily name for the fvar named instance at this
    master grid point -- e.g. (900, 75, 100, 50) -> 'Condensed Slab
    Black GradeHigh', (400, 100, 0, 0) -> 'Regular'. Width, Serif and
    Grade only appear when they're off their default (Normal/Sans/
    Grade0), same elision rule the STAT table's own axis labels use, so
    the default corner of the grid is still plain 'Regular' rather than
    'Normal Sans Regular Grade0'."""
    parts = []
    if wdth != WDTH_DEFAULT:
        parts.append(WDTH_NAMES[wdth])
    if serf != SERF_DEFAULT:
        parts.append(SERF_NAMES[serf])
    parts.append(WGHT_NAMES[wght])
    if grad != GRAD_DEFAULT:
        parts.append(GRAD_NAMES[grad])
    return " ".join(parts)
