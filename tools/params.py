"""Azrienoch axis model: the master grid and the (registered) axis definitions.

Four variable axes:

* ``wght`` (100-900) -- registered weight axis. Also drives glyph height
  (see ``roboto_source.py``'s "height as weight" mapping) and stroke
  thickness/contrast, via correlated Roboto Flex parametric-axis values.
* ``wdth`` (75-100)  -- registered width axis, mapped onto a moderately
  condensed range of Roboto Flex's own `wdth` (see
  ``roboto_source.roboto_location``).
* ``SERF`` (0-100)   -- custom axis. Azrienoch is sans by default
  (SERF=0); raising it grows slab feet at stem terminals (``serifs.py``),
  always cut flat/horizontal, matching the terminal rule.
* ``GRAD`` (-50-50)  -- registered grade axis, passed straight through to
  Roboto Flex's own `GRAD` (see ``roboto_source.roboto_location``). Unlike
  `wght`, grade changes stroke weight without changing advance widths or
  glyph metrics, so it's safe to nudge for optical compensation (e.g.
  dark-on-light vs. light-on-dark) without reflowing text. Three samples,
  not two: `fontmake` requires an actual source at a designspace's default
  location on every axis, so 0 (neutral grade) has to be a real master
  alongside the -50/50 extremes, not just their interpolated midpoint.

``opsz`` (optical size) and ``slnt`` (slant) are deliberately not
exposed -- see README.md's "Design" section and TODO.md for why.
"""

from __future__ import annotations

# (tag, min, default, max)
WGHT_AXIS = ("wght", 100, 400, 900)
WDTH_AXIS = ("wdth", 75, 100, 100)
SERF_AXIS = ("SERF", 0, 0, 100)
GRAD_AXIS = ("GRAD", -50, 0, 50)

WGHT_MASTERS = (100, 175, 250, 400, 700, 900)
# Which of WGHT_MASTERS get their own full set of named fvar instances
# (crossed with every wdth/SERF/GRAD combo) rather than existing purely
# as an interpolation source. 175 and 250 are here only to shorten the
# Thin-to-Regular jump gvar has to interpolate across in one step -- see
# rotation_align.py/taper_align.py's docstrings for why that 300-unit
# span was long enough for a few letters' own point correspondence to
# drift out of sync with itself between the two ends, badly enough for
# 'o' and its symmetric relatives to visibly flatten to a near-illegible
# sliver partway through it. One extra stop at 250 fixed the worse half
# of that range (roughly wght 200-310) but left a smaller version of the
# same problem in the now-shorter 100-250 gap; 175 (that gap's own
# midpoint) fixed what was left. Neither was designed as its own weight
# the way Thin/Regular/Bold/Black were, so neither gets a user-facing
# style name of its own -- they just cut the design space's own worst
# interpolation gap down first in half, then in quarters.
WGHT_INSTANCE_MASTERS = (100, 400, 700, 900)
WDTH_MASTERS = (75, 100)
SERF_MASTERS = (0, 100)
GRAD_MASTERS = (-50, 0, 50)

WGHT_NAMES = {
    100: "Thin",
    175: "ThinLight",
    250: "ExtraLight",
    400: "Regular",
    700: "Bold",
    900: "Black",
}
GRAD_NAMES = {-50: "GradeLow", 0: "", 50: "GradeHigh"}


def master_grid():
    """All (wght, wdth, serf, grad) master locations to instantiate as UFOs."""
    for wght in WGHT_MASTERS:
        for wdth in WDTH_MASTERS:
            for serf in SERF_MASTERS:
                for grad in GRAD_MASTERS:
                    yield wght, wdth, serf, grad


def master_name(wght, wdth, serf, grad):
    w = WGHT_NAMES[wght]
    d = {75: "Condensed", 100: "Normal"}[wdth]
    s = "Serif" if serf else "Sans"
    g = GRAD_NAMES[grad]
    return f"{d}{w}{s}{g}"
