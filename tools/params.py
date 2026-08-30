"""Multiplex axis model.

Three variable axes:

* ``wght`` (100-900) -- registered weight axis. Also drives glyph height
  directly (see "height as weight" below) and stroke thickness/contrast.
* ``wdth`` (75-100)  -- registered width axis. Scales horizontal
  proportions (bowl/counter widths, arm lengths, sidebearings) without
  touching stroke weight, so condensed masters stay legible rather than
  merely squeezed.
* ``SERF`` (0-100)   -- custom axis. Multiplex is sans by default
  (SERF=0); raising it grows slab feet at stem terminals, always cut
  flat/horizontal, matching the terminal rule.

Height as a matter of weight
-----------------------------
Instead of tying cap-height/x-height to point size or line height,
Multiplex ties them to the wght axis itself: heavier masters are
genuinely taller (larger cap-height and, proportionally more, x-height),
independent of unitsPerEm or the type size the reader chooses. Real
grotesques already nudge x-height up at black weights to keep counters
open at speed; Multiplex takes that further and makes it an explicit,
continuous design parameter instead of a per-weight optical correction.

Aesthetic target: an analytical neo-grotesque (Helvetica-like rational
proportions and flat terminals) with Roboto Flex's systematic multi-axis
engineering, and a few barely-noticeable Akzidenz-Grotesk-style
idiosyncrasies applied in ``glyphset.py`` (two-storey 'a', a spurred 'G',
an asymmetric 'R' leg, uneven curve tension in 'S').
"""

from __future__ import annotations

from dataclasses import dataclass

UPM = 1000

# (tag, min, default, max)
WGHT_AXIS = ("wght", 100, 400, 900)
WDTH_AXIS = ("wdth", 75, 100, 100)
SERF_AXIS = ("SERF", 0, 0, 100)

WGHT_MASTERS = (100, 400, 900)
WDTH_MASTERS = (75, 100)
SERF_MASTERS = (0, 100)


def _lerp3(x, xs, ys):
    """Piecewise-linear interpolation across 3 sample points."""
    x0, x1, x2 = xs
    y0, y1, y2 = ys
    if x <= x1:
        t = 0.0 if x1 == x0 else (x - x0) / (x1 - x0)
        return y0 + (y1 - y0) * t
    t = 0.0 if x2 == x1 else (x - x1) / (x2 - x1)
    return y1 + (y2 - y1) * t


@dataclass
class Metrics:
    wght: float
    wdth: float
    serf: float

    stem: float          # main stroke weight
    hair: float           # secondary stroke weight (curves/crossbars)
    cap_height: float
    x_height: float
    ascender: float
    descender: float
    overshoot_cap: float
    overshoot_x: float
    wdth_scale: float
    serif_amount: float


def metrics_for(wght: float, wdth: float, serf: float) -> Metrics:
    wghts = WGHT_MASTERS
    stem = _lerp3(wght, wghts, (46, 100, 210))
    hair = stem * 0.90
    cap_height = _lerp3(wght, wghts, (700, 720, 760))
    x_height = _lerp3(wght, wghts, (500, 524, 560))
    descender = _lerp3(wght, wghts, (-190, -210, -235))
    ascender = cap_height

    w0, w1 = WDTH_MASTERS[0], WDTH_MASTERS[-1]
    t_wd = 0.0 if w1 == w0 else (wdth - w0) / (w1 - w0)
    wdth_scale = 0.78 + 0.22 * t_wd

    return Metrics(
        wght=wght, wdth=wdth, serf=serf,
        stem=stem, hair=hair,
        cap_height=cap_height, x_height=x_height,
        ascender=ascender, descender=descender,
        overshoot_cap=cap_height * 0.012,
        overshoot_x=x_height * 0.014,
        wdth_scale=wdth_scale,
        serif_amount=serf,
    )


def master_grid():
    """All (wght, wdth, serf) master locations to instantiate as UFOs."""
    for wght in WGHT_MASTERS:
        for wdth in WDTH_MASTERS:
            for serf in SERF_MASTERS:
                yield wght, wdth, serf


def master_name(wght, wdth, serf):
    w = {100: "Thin", 400: "Regular", 900: "Black"}[wght]
    d = {75: "Condensed", 100: "Normal"}[wdth]
    s = "Serif" if serf else "Sans"
    return f"{d}{w}{s}"
