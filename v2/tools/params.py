"""Axis model for Azrienoch v2.

Every glyph is drawn parametrically (see glyphset.py) as a function of
weight and width -- there is no source font being extracted from. This
module is the single place that maps an axis location to the numbers
those drawing functions need (stem thickness, vertical metrics, width
factor), and enumerates the master grid the build compiles from.
"""

from __future__ import annotations

from dataclasses import dataclass

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


@dataclass(frozen=True)
class Metrics:
    wght: int
    wdth: int
    stem: float  # stroke thickness at this wght
    wf: float  # horizontal scale factor from wdth
    cap: float = CAP_HEIGHT
    xh: float = X_HEIGHT
    asc: float = ASCENDER
    desc: float = DESCENDER


def stem_for_wght(wght: float) -> float:
    """Stroke thickness: 60 units at Thin (100) to 220 at Black (900)."""
    t = (wght - WGHT_MIN) / (WGHT_MAX - WGHT_MIN)
    return 60.0 + t * (220.0 - 60.0)


def metrics_for(wght: int, wdth: int) -> Metrics:
    return Metrics(wght=wght, wdth=wdth, stem=stem_for_wght(wght), wf=wdth / 100.0)


def style_name(wght: int, wdth: int) -> str:
    return f"Wght{wght}_Wdth{wdth}"
