"""Azrienoch axis model: the master grid and the (registered) axis definitions.

Four variable axes:

* ``wght`` (180-900) -- registered weight axis. Also drives glyph height
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
exposed -- see docs/axes.md for why.
"""

from __future__ import annotations

# (tag, min, default, max)
WGHT_AXIS = ("wght", 180, 400, 900)
WDTH_AXIS = ("wdth", 75, 100, 100)
SERF_AXIS = ("SERF", 0, 0, 100)
GRAD_AXIS = ("GRAD", -50, 0, 50)

# The axis floor is 180, not Roboto Flex's own 100: every weight below
# that -- confirmed repeatedly, across v/V/w/W and other letters, via a
# direct self-intersection sweep of the compiled font -- renders with
# some contour turned "inside out" (a real edge-edge crossing, not
# merely an aesthetic flatness issue). Rather than keep chasing that
# letter by letter, the axis itself no longer offers a weight where it
# can happen: 180 was confirmed clean (see taper_align.py/quirks.py's
# own v/w fixes, and the general self-intersection sweeps run alongside
# them) and is close enough to Roboto Flex's own floor that the
# lightest instance still reads as a genuine hairline weight, not a
# compromise.
WGHT_MASTERS = (180, 250, 400, 700, 900)
# Which of WGHT_MASTERS get their own full set of named fvar instances
# (crossed with every wdth/SERF/GRAD combo) rather than existing purely
# as an interpolation source. 250 exists only to shorten the Thin-to-
# Regular jump gvar has to interpolate across in one step -- see
# rotation_align.py/taper_align.py's docstrings for why a 300-unit span
# (the original 100-400 gap) was long enough for a few letters' own
# point correspondence to drift out of sync with itself between the two
# ends, badly enough for 'o' and its symmetric relatives to visibly
# flatten to a near-illegible sliver partway through it. With the axis
# floor now at 180 (see WGHT_AXIS's own comment), the remaining 180-400
# gap is under half that original span, comfortably inside what a
# single extra stop at 250 already keeps clean -- confirmed by the same
# sweep that set the floor itself. 250 was never designed as its own
# weight the way Thin/Regular/Bold/Black were, so it doesn't get a
# user-facing style name of its own -- it just cuts the design space's
# own worst remaining interpolation gap in half.
WGHT_INSTANCE_MASTERS = (180, 400, 700, 900)
WDTH_MASTERS = (75, 100)
SERF_MASTERS = (0, 100)
GRAD_MASTERS = (-50, 0, 50)

WGHT_NAMES = {
    180: "Thin",
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
