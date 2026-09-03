"""Extracts 's' from the repository root's own Azrienoch pipeline
(Roboto Flex, `tools/`) instead of from Jost, per the project owner's
direction ("use the s from version one"): Jost's own 's' proved
impossible to reorient into a clean horizontal Helvetica-style terminal
without a self-intersection at heavy weight (root-caused and fixed once
in `quirks.py::_reorient_cut`, but the underlying curve geometry near
that terminal stayed fragile enough it seemed worth just not fighting).
The root project's own 's' -- Roboto Flex's native shape, already run
through root's own alignment/taper-sign correction -- doesn't have that
problem: its terminal is a real stepped ink-trap notch (a deliberate
sharp vertical cusp cut into the corner, standard practice for a
heavy-weight optical correction, confirmed by inspecting the raw,
untouched Roboto Flex points directly -- not a bug to route around).

Extracted BEFORE root's own `serifs.py::apply_feet` (root's SERF=0 still
inserts a hairline foot contour into every glyph; this module takes the
glyph as it stood right before that step, since Azrienoch v2 applies its
own SERF axis afterward, same as every other letter here) and BEFORE
root's `quirks.py::apply_quirks` (confirmed a no-op for 's' specifically
-- root's quirks.py has no special-case for it at all -- so skipping it
changes nothing).

Uniformly rescaled from Roboto Flex's own metrics (UPM 2048, x-height
1021) to Azrienoch v2's (UPM 1000, x-height `params.X_HEIGHT` = 470):
's' sits entirely within the x-height box in both source and target, so
one scale factor (`params.X_HEIGHT / ROOT_X_HEIGHT`) applied to both
axes, with no separate translation, keeps its baseline-to-x-height
proportions and overshoot intact without needing to reconcile root's cap
height/x-height ratio against Jost's (the two fonts' overall proportions
differ; 's' being a pure x-height glyph is what makes this shortcut
correct here specifically, not a general-purpose technique).

Root's own `wght` axis floor is 180, not v2's 100 -- v2's `wght=100`
sample is clamped to root's 180 (a stand-in, not a real value at that
extreme; the closest available rather than an extrapolation past what
root's own font actually defines).
"""

from __future__ import annotations

from fontTools.pens.recordingPen import RecordingPen

from tools import roboto_source as R
from tools import rotation_align as RA
from tools import taper_align as TA
from tools import ufo_build as U

from . import params

ROOT_X_HEIGHT = 1021.0
_ROOT_WGHT_MIN = 180

_reference_contours_cache = None


def _reference_contours():
    global _reference_contours_cache
    if _reference_contours_cache is None:
        _, _, reference_contours = U.compute_reference_specs()
        _reference_contours_cache = reference_contours
    return _reference_contours_cache


def extract(wght: int, wdth: int):
    """Returns (pen_value, width) for 's', in Azrienoch v2's own
    coordinate space -- same return shape as `jost_source.extract`, so
    `ufo_build.py` can drop it in as a substitute for that one glyph."""
    root_wght = max(wght, _ROOT_WGHT_MIN)
    inst = R.instantiate(root_wght, wdth, 0)
    glyphset = inst.getGlyphSet()
    hmtx = inst["hmtx"]
    cmap = R.cmap_for(root_wght, wdth, 0)
    gname = cmap[ord("s")]

    glyph = U._extract_char_glyph("s", gname, glyphset, hmtx, cmap, ROOT_X_HEIGHT)
    U._split_fused_digit_contour(glyph, "s")
    reference_contours = _reference_contours()
    if gname in reference_contours:
        RA.align_to_reference(glyph, reference_contours[gname])
        TA.align_taper_signs(glyph, reference_contours[gname])

    scale = params.X_HEIGHT / ROOT_X_HEIGHT
    pen = RecordingPen()
    glyph.draw(pen)
    scaled_pen = RecordingPen()
    for cmd, args in pen.value:
        scaled_pen.value.append((cmd, tuple((x * scale, y * scale) for x, y in args)))
    return scaled_pen.value, glyph.width * scale
