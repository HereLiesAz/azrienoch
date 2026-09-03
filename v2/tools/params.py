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
CAP_HEIGHT = 700
X_HEIGHT = 500
ASCENDER = 750
DESCENDER = -250

WGHT_MIN, WGHT_MAX, WGHT_DEFAULT = 100, 900, 400
WDTH_MIN, WDTH_MAX, WDTH_DEFAULT = 75, 100, 100

AXES = [
    {"tag": "wght", "name": "Weight", "minimum": WGHT_MIN, "default": WGHT_DEFAULT, "maximum": WGHT_MAX},
    {"tag": "wdth", "name": "Width", "minimum": WDTH_MIN, "default": WDTH_DEFAULT, "maximum": WDTH_MAX},
]

# One master at every grid corner plus the wght midpoint, so the default
# location (400, 100) is itself a real source -- required for a
# well-formed designspace -- and wght gets a bend partway through its
# range rather than a single straight interpolation.
WGHT_SAMPLES = (WGHT_MIN, WGHT_DEFAULT, WGHT_MAX)
WDTH_SAMPLES = (WDTH_MIN, WDTH_MAX)

MASTER_GRID = [(wght, wdth) for wght in WGHT_SAMPLES for wdth in WDTH_SAMPLES]
DEFAULT_LOCATION = (WGHT_DEFAULT, WDTH_DEFAULT)


def style_name(wght: int, wdth: int) -> str:
    return f"Wght{wght}_Wdth{wdth}"
