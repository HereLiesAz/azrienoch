"""Letters composed from Azrienoch's own finished glyphs, for the Latin
characters Jost does not carry: a base letter plus combining marks
(Latin Extended-B / Additional: Vietnamese, Pinyin, Welsh, Maltese ...), the
barred letters, and the compatibility digraphs.

A composed glyph copies the finished base letter's contours (this build's own
`c`/`e`/`o`/`Y` ..., not Jost's) and adds mark contours:

- Marks Jost draws (`gravecomb` ... `ogonek`) are taken from Jost at the same
  (wght, wdth, grad), so they carry the weight and width of the master.
- Marks Jost lacks are derived from ones it has: dot/macron/tilde/diaeresis/
  ring below are the above-marks moved under the baseline; circumflex/breve
  below and the inverted breve are the above-marks turned upside down; the
  double grave is two graves. Hook above and horn are drawn here with
  `strokes`.
- Placement: a mark is centered on its base's bounding box, lifted by
  `top - X_HEIGHT` (the base's top: x-height, cap height or ascender) so it
  keeps Jost's own gap, and a second mark stacks above the first. Below-marks
  hang under the baseline (or under a descender). Dotless `ı`/`ȷ` replace
  `i`/`j` under any mark above.

Every master builds the same contours in the same order, so the compiled
variable font interpolates them.
"""

from __future__ import annotations

import unicodedata

from fontTools.misc.transform import Transform
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.reverseContourPen import ReverseContourPen
from fontTools.pens.transformPen import TransformPen

from . import jost_source, params, strokes

ABOVE = {
    0x300, 0x301, 0x302, 0x303, 0x304, 0x306, 0x307, 0x308, 0x309, 0x30A,
    0x30B, 0x30C, 0x30F, 0x311,
}
BELOW = {0x323, 0x324, 0x325, 0x326, 0x327, 0x328, 0x32D, 0x32E, 0x330, 0x331}
HORN = 0x31B

# Marks Jost has, by codepoint.
_JOST_MARKS = (0x300, 0x301, 0x302, 0x303, 0x304, 0x306, 0x307, 0x308, 0x30A, 0x30B, 0x30C, 0x326, 0x327, 0x328)
# Derived marks: codepoint -> (Jost mark, "up" | "down" for flipped / moved, placement).
_DERIVED = {
    0x323: (0x307, "below"),
    0x324: (0x308, "below"),
    0x325: (0x30A, "below"),
    0x330: (0x303, "below"),
    0x331: (0x304, "below"),
    0x32D: (0x302, "below-flip"),
    0x32E: (0x306, "below-flip"),
    0x311: (0x306, "above-flip"),
}

# Gap kept between stacked marks / under the baseline.
STACK_GAP = 55.0
BELOW_GAP = 65.0

# Compatibility digraphs: char -> its two letters.
DIGRAPHS = {
    "Ǆ": "DŽ", "ǅ": "Dž", "ǆ": "dž", "Ǉ": "LJ", "ǈ": "Lj", "ǉ": "lj",
    "Ǌ": "NJ", "ǋ": "Nj", "ǌ": "nj", "Ǳ": "DZ", "ǲ": "Dz", "ǳ": "dz",
}
# Barred letters: char -> (base, bar y as "x"=x-height centre, "c"=cap centre,
# "a"=ascender, "d"=descender, "m"=mid-height of the letter, overshoot).
BARRED = {
    "ƀ": ("b", "a"), "Ƀ": ("B", "c"), "Ȼ": ("C", "c"), "ȼ": ("c", "x"),
    "Ɇ": ("E", "c"), "ɇ": ("e", "x"), "Ɉ": ("J", "c"), "ɉ": ("j", "x"),
    "Ɍ": ("R", "c"), "ɍ": ("r", "x"), "Ɏ": ("Y", "c"), "ɏ": ("y", "x"),
    "Ƶ": ("Z", "c"), "ƶ": ("z", "x"), "Ɨ": ("I", "c"), "ɨ": ("ı", "x"),
    "Ƚ": ("L", "c"), "ƚ": ("l", "a"), "Ǥ": ("G", "c"), "ǥ": ("g", "x"),
}


def _bounds(glyph_or_pen_value) -> tuple[float, float, float, float] | None:
    pen = BoundsPen(None)
    if isinstance(glyph_or_pen_value, list):
        jost_source.replay(pen, glyph_or_pen_value)
    else:
        glyph_or_pen_value.draw(pen)
    return pen.bounds


def _bounds_of_value(value):
    pts = [p for _, args in value for p in args if p is not None]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


class Marks:
    """The mark outlines at one master, as pen values in raw (Jost) position."""

    def __init__(self, wght: int, wdth: int, grad: int, stem: float):
        self.stem = stem
        names = jost_source.glyph_names_for_chars("".join(chr(c) for c in _JOST_MARKS))
        self.raw = {c: jost_source.extract(names[chr(c)], wght, wdth, grad)[0] for c in _JOST_MARKS}
        self.wdth = wdth
        # The gap Jost leaves above the x-height, measured on its own grave.
        _, self.raw_bottom, _, _ = _bounds_of_value(self.raw[0x300])
        self.mark_h = {c: _bounds_of_value(v) for c, v in self.raw.items()}

    # -- derived/drawn shapes, returned as ("value", pen_value) or ("strokes", contours)

    def hook_above(self):
        cb = self.mark_h[0x30C]
        w = 0.62 * (cb[2] - cb[0])
        h = 1.15 * (cb[3] - cb[1])
        t = min(self.stem, 90.0)
        x0, y0 = 0.0, self.raw_bottom
        s1 = ((x0, y0), (x0, y0 + h * 0.55), (x0 + w * 0.12, y0 + h - t / 2), (x0 + w * 0.5, y0 + h - t / 2))
        s2 = ((x0 + w * 0.5, y0 + h - t / 2), (x0 + w * 0.9, y0 + h - t / 2), (x0 + w, y0 + h * 0.78), (x0 + w * 0.8, y0 + h * 0.46))
        return strokes.stroke([s1, s2], t)

    def horn(self, sx: float, sy: float):
        t = min(self.stem * 0.7, 100.0)
        f = max(self.wdth, 60) / 100.0
        s = ((sx, sy), (sx + 30 * f, sy + 55), (sx + 95 * f, sy + 85), (sx + 150 * f, sy + 85))
        return strokes.stroke([s], t)


def _draw_value(pen, value, dx=0.0, dy=0.0, flip_about=None):
    """Replay a pen value translated by (dx, dy); if `flip_about` is a y,
    mirror vertically about it (reversing the winding back)."""
    if flip_about is None:
        jost_source.replay(TransformPen(pen, Transform(1, 0, 0, 1, dx, dy)), value)
    else:
        t = Transform(1, 0, 0, -1, dx, 2 * flip_about + dy)
        jost_source.replay(TransformPen(ReverseContourPen(pen), t), value)


def _ink_bounds(glyph, min_y=None):
    pen = BoundsPen(None)
    glyph.draw(pen)
    return pen.bounds


def _top_of(base_ch: str, bounds) -> float:
    if base_ch.isupper() or base_ch.isdigit():
        return params.CAP_HEIGHT
    if base_ch in "bdfhklt":
        return params.ASCENDER
    return params.X_HEIGHT


def compose_marked(font, glyph, ch: str, marks: Marks, ogonek_dx: float, namer) -> None:
    """Build `glyph` (character `ch`) from `font`'s base glyph and marks."""
    nfd = unicodedata.normalize("NFD", ch)
    base_ch, mks = nfd[0], [ord(m) for m in nfd[1:]]
    has_above = any(m in ABOVE or m == HORN for m in mks)
    use = {"i": "ı", "j": "ȷ"}.get(base_ch) if any(m in ABOVE for m in mks) else None
    base = font[namer(use or base_ch)]
    pen = glyph.getPen()
    base.draw(pen)
    glyph.width = base.width
    bx0, by0, bx1, by1 = _ink_bounds(base)
    top = _top_of(base_ch, (bx0, by0, bx1, by1))
    cx = (bx0 + bx1) / 2.0
    if base_ch == "j" or use == "ȷ":
        # The hook sweeps left under the stem; centre on the stem.
        cx = bx1 - (marks.stem / 2.0) - 0.0
        cx = (bx1 + max(bx0, bx1 - marks.stem * 1.2)) / 2.0
    lift_next = top - params.X_HEIGHT       # lift for the first mark above
    stack_top = None                        # top of the highest mark so far
    below_y = by0 if by0 < -40 else 0.0     # where below-marks hang from
    below_y = min(below_y, 0.0)
    for m in mks:
        if m == HORN:
            hy = by1 - 0.14 * (by1 - by0)
            hx = bx1 - max(marks.stem / 2.0, 0.14 * (bx1 - bx0))
            strokes.draw(pen, marks.horn(hx, hy))
            continue
        if m == 0x309:
            contours = marks.hook_above()
            cb = _contour_bounds(contours)
            lift = (lift_next if stack_top is None else stack_top + STACK_GAP - marks.raw_bottom)
            dx, dy = cx - (cb[0] + cb[2]) / 2.0, lift
            strokes.draw(pen, _shift(contours, dx, dy))
            stack_top = cb[3] + dy
            continue
        if m == 0x30F:
            v = marks.raw[0x300]
            vb = marks.mark_h[0x300]
            width = vb[2] - vb[0]
            lift = (lift_next if stack_top is None else stack_top + STACK_GAP - marks.raw_bottom)
            gap = width * 0.35
            for k in (-1, 1):
                dx = cx + k * (width + gap) / 2.0 - (vb[0] + vb[2]) / 2.0
                _draw_value(pen, v, dx, lift)
            stack_top = vb[3] + lift
            continue
        if m in _DERIVED:
            src, kind = _DERIVED[m]
            v, vb = marks.raw[src], marks.mark_h[src]
        else:
            src, kind = m, "above"
            v, vb = marks.raw[m], marks.mark_h[m]
        mx = (vb[0] + vb[2]) / 2.0
        if kind == "above":
            if m == 0x328:   # ogonek: hangs from the base's right foot
                _draw_value(pen, v, bx1 + ogonek_dx - vb[0], 0.0)
                continue
            if m in (0x326, 0x327):
                _draw_value(pen, v, cx - mx, 0.0)
                continue
            lift = (lift_next if stack_top is None else stack_top + STACK_GAP - marks.raw_bottom)
            _draw_value(pen, v, cx - mx, lift)
            stack_top = vb[3] + lift
        elif kind == "above-flip":
            lift = (lift_next if stack_top is None else stack_top + STACK_GAP - marks.raw_bottom)
            _draw_value(pen, v, cx - mx, lift, flip_about=(vb[1] + vb[3]) / 2.0)
            stack_top = vb[3] + lift
        elif kind == "below":
            dy = below_y - BELOW_GAP - vb[3]
            _draw_value(pen, v, cx - mx, dy)
            below_y = vb[1] + dy
        else:  # below-flip
            dy = below_y - BELOW_GAP - vb[3]
            _draw_value(pen, v, cx - mx, dy, flip_about=(vb[1] + vb[3]) / 2.0)
            below_y = vb[1] + dy


def _contour_bounds(contours):
    pts = [p for c in contours for s in c for p in s]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def _shift(contours, dx, dy):
    return [[tuple((p[0] + dx, p[1] + dy) for p in s) for s in c] for c in contours]


def compose_barred(font, glyph, ch: str, stem_h: float, namer) -> None:
    base_ch, where = BARRED[ch]
    base = font[namer(base_ch)]
    pen = glyph.getPen()
    base.draw(pen)
    glyph.width = base.width
    bx0, by0, bx1, by1 = _ink_bounds(base)
    if where == "c":
        y = params.CAP_HEIGHT * 0.5
    elif where == "x":
        y = params.X_HEIGHT * 0.5
    else:   # ascender letters: through the stem at a bit over x-height
        y = params.X_HEIGHT * 0.78
    ext = max(40.0, (bx1 - bx0) * 0.14)
    x0, x1 = bx0 - ext, bx1 + ext
    if base_ch in "ıl":
        x0, x1 = bx0 - ext * 1.3, bx1 + ext * 1.3
    strokes.draw(pen, strokes.stroke([strokes.line((x0, y), (x1, y))], stem_h))


def compose_digraph(font, glyph, ch: str, namer) -> None:
    a, b = DIGRAPHS[ch]
    ga, gb = font[namer(a)], font[namer(b)]
    pen = glyph.getPen()
    ga.draw(pen)
    tp = TransformPen(pen, Transform(1, 0, 0, 1, ga.width, 0))
    gb.draw(tp)
    glyph.width = ga.width + gb.width



def ogonek_offset(font, namer, wght: int, wdth: int, grad: int) -> float:
    """How far Jost's ogonek starts from the right edge of its base: measured
    on Jost's own `eogonek` (contour 0 is the letter, the rest the mark)."""
    name = jost_source.glyph_names_for_chars("ę")["ę"]
    value, _ = jost_source.extract(name, wght, wdth, grad)
    contours, cur = [], []
    for cmd, args in value:
        cur.append((cmd, args))
        if cmd == "closePath":
            contours.append(cur)
            cur = []
    base = _bounds_of_value([c for c in contours[0]])
    mark = _bounds_of_value([c for ct in contours[1:] for c in ct])
    return mark[0] - base[2]
