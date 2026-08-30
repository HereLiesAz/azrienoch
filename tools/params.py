"""Azrienoch axis model: the master grid and the (registered) axis definitions.

Three variable axes:

* ``wght`` (100-900) -- registered weight axis. Also drives glyph height
  (see ``roboto_source.py``'s "height as weight" mapping) and stroke
  thickness/contrast, via correlated Roboto Flex parametric-axis values.
* ``wdth`` (75-100)  -- registered width axis, mapped onto a moderately
  condensed range of Roboto Flex's own `wdth` (see
  ``roboto_source.roboto_location``).
* ``SERF`` (0-100)   -- custom axis. Azrienoch is sans by default
  (SERF=0); raising it grows slab feet at stem terminals (``serifs.py``),
  always cut flat/horizontal, matching the terminal rule.
"""

from __future__ import annotations

# (tag, min, default, max)
WGHT_AXIS = ("wght", 100, 400, 900)
WDTH_AXIS = ("wdth", 75, 100, 100)
SERF_AXIS = ("SERF", 0, 0, 100)

WGHT_MASTERS = (100, 400, 900)
WDTH_MASTERS = (75, 100)
SERF_MASTERS = (0, 100)


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
