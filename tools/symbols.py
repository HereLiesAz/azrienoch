"""Logic and set-theory symbols, drawn per master.

Nothing here is drawn on a fixed grid: each master measures Jost's own `=`,
`−`, `<` and `·` (already at that master's weight, width and grade) and builds
the symbols from them, so a bar is as thick as the minus sign next to it and a
symbol is as wide as the minus is. Shapes are centerline strokes
(`strokes.stroke` / `strokes.ring`); the letter-shaped ones are the finished
letters turned: `∀` is `A` rotated, `∃` is `E` mirrored, `⊤` is `T`, `⊥` is
`T` rotated, and the dots of `∴`/`∵` are Jost's own `·` outline.

Geometry names: `ax` the math axis (centre of `=`), `rk` the half height of
`<` (the ink half height of a mid-size symbol), `t` the stroke, `tc` a thinner
stroke for symbols that stack several strokes, `x0..x1` the ink span of `−`.
"""

from __future__ import annotations

import math

from fontTools.misc.transform import Transform
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.reverseContourPen import ReverseContourPen
from fontTools.pens.transformPen import TransformPen

from . import params, quirks, serifs, strokes
from .strokes import arc, fill, join, line, polyline, reverse, ring, stroke

SLASHED = {
    "∄": "∃", "∉": "∈", "∌": "∋", "⊄": "⊂",
    "⊅": "⊃", "⊈": "⊆", "⊉": "⊇", "⊬": "⊢",
    "⊭": "⊨", "≢": "≡",
}


def _bounds(glyph):
    pen = BoundsPen(None)
    glyph.draw(pen)
    return pen.bounds


class Geo:
    def __init__(self, font, namer):
        x0, y0, x1, y1 = _bounds(font[namer("−")])
        _, ey0, _, ey1 = _bounds(font[namer("=")])
        _, ly0, _, ly1 = _bounds(font[namer("<")])
        self.x0, self.x1 = x0, x1
        self.w = x1 - x0
        self.xm = (x0 + x1) / 2.0
        self.t = ((y1 - y0) + serifs.stem_width(font["l"])) / 2.0
        self.ax = (ey0 + ey1) / 2.0
        self.rk = (ly1 - ly0) / 2.0
        self.tc = min(self.t, 0.4 * self.rk)
        self.r = self.rk - self.t / 2.0          # centerline half height
        self.rc = self.rk - self.tc / 2.0


def build(font, namer, wght: int, wdth: int, grad: int) -> None:
    g = Geo(font, namer)
    sym = _Symbols(font, namer, g)
    for ch in params.LOGIC:
        glyph = font.newGlyph(namer(ch))
        glyph.unicodes = [ord(ch)]
        getattr(sym, f"s_{ord(ch):04X}")(glyph)


class _Symbols:
    def __init__(self, font, namer, g: Geo):
        self.font, self.namer, self.g = font, namer, g

    # -- plumbing ---------------------------------------------------------
    def _finish(self, glyph, contours, span=None):
        """Draw `contours`. Advance = the minus sign's own (ink span plus its
        side bearings); a symbol wider than that (long arrows) gets its own
        span plus the same side bearings."""
        g = self.g
        width = g.x1 + g.x0
        if span is not None and span[1] - span[0] > g.w:
            dx = g.x0 - span[0]
            contours = [[tuple((p[0] + dx, p[1]) for p in s) for s in c] for c in contours]
            width = span[1] - span[0] + 2 * g.x0
        strokes.draw(glyph.getPen(), contours)
        glyph.width = round(width)

    def _span(self, half):
        g = self.g
        return g.xm - half, g.xm + half

    def _slash(self, cx, cy, sh, width=None):
        g = self.g
        sw = sh * 0.46
        return stroke([line((cx - sw, cy - sh), (cx + sw, cy + sh))], width or g.t)

    def _copy(self, glyph, src, transform=None, mirror=False):
        pen = glyph.getPen()
        if mirror:
            tp = TransformPen(ReverseContourPen(pen), Transform(-1, 0, 0, 1, src.width, 0))
        else:
            tp = pen
        src.draw(tp)
        glyph.width = src.width

    # -- connectives ------------------------------------------------------
    def _vee(self, up: bool, tc=None, half=0.46, h=1.0):
        g = self.g
        t = tc or g.t
        r = g.rk - t / 2.0 if tc is None else g.rc
        r *= h
        hw = g.w * half
        ya, yb = (g.ax - r, g.ax + r)
        pts = [(g.xm - hw, yb), (g.xm, ya), (g.xm + hw, yb)] if not up else [(g.xm - hw, ya), (g.xm, yb), (g.xm + hw, ya)]
        return stroke(polyline(*pts), t)

    def s_2227(self, glyph):   # ∧
        self._finish(glyph, self._vee(True))

    def s_2228(self, glyph):   # ∨
        self._finish(glyph, self._vee(False))

    def _barred_vee(self, glyph, up, bar_top):
        g = self.g
        tc = g.tc
        h = 0.78
        vee = self._vee(up, tc, h=h)
        r = g.rc * h
        top = g.ax + r + tc / 2.0
        bot = g.ax - r - tc / 2.0
        gap = max(tc * 0.9, 45.0)
        y = top + gap + tc / 2.0 if bar_top else bot - gap - tc / 2.0
        hw = g.w * 0.46
        self._finish(glyph, vee + stroke([line((g.xm - hw, y), (g.xm + hw, y))], tc))

    def s_22BC(self, glyph):   # ⊼ nand: ∧ with overbar
        self._barred_vee(glyph, True, True)

    def s_22BD(self, glyph):   # ⊽ nor: ∨ with overbar
        self._barred_vee(glyph, False, True)

    def s_22BB(self, glyph):   # ⊻ xor: ∨ with underbar
        self._barred_vee(glyph, False, False)

    def _circle(self, r, t):
        g = self.g
        return ring(arc(g.xm, g.ax, r, 90, -270), t)

    def s_2295(self, glyph):   # ⊕
        g, tc = self.g, self.g.tc
        r = g.rc
        c = self._circle(r, tc)
        c += stroke([line((g.xm - r, g.ax), (g.xm + r, g.ax))], tc)
        c += stroke([line((g.xm, g.ax - r), (g.xm, g.ax + r))], tc)
        self._finish(glyph, c)

    def s_2297(self, glyph):   # ⊗
        g, tc = self.g, self.g.tc
        r = g.rc
        d = r * math.cos(math.radians(45))
        c = self._circle(r, tc)
        c += stroke([line((g.xm - d, g.ax - d), (g.xm + d, g.ax + d))], tc)
        c += stroke([line((g.xm - d, g.ax + d), (g.xm + d, g.ax - d))], tc)
        self._finish(glyph, c)

    # -- quantifiers: the letters, turned ----------------------------------
    def s_2200(self, glyph):   # ∀ = A rotated
        self._copy(glyph, self.font["A"])
        quirks.rotate_180(glyph)

    def s_2203(self, glyph):   # ∃ = E mirrored
        self._copy(glyph, self.font["E"], mirror=True)

    def s_2204(self, glyph):   # ∄
        self.s_2203(glyph)
        self._add_slash(glyph, params.CAP_HEIGHT / 2.0, params.CAP_HEIGHT * 0.56)

    def _add_slash(self, glyph, cy, sh, cx=None):
        g = self.g
        b = _bounds(glyph)
        cx = (b[0] + b[2]) / 2.0 if cx is None else cx
        strokes.draw(glyph.getPen(), self._slash(cx, cy, sh, g.tc))

    # -- tacks and turnstiles ---------------------------------------------
    def s_22A4(self, glyph):   # ⊤
        self._copy(glyph, self.font["T"])

    def s_22A5(self, glyph):   # ⊥
        self._copy(glyph, self.font["T"])
        quirks.rotate_180(glyph)

    def _stem_arms(self, xs, arms_y, xe, t, top=params.CAP_HEIGHT):
        c = stroke([line((xs, 0), (xs, top))], t)
        for y in arms_y:
            c += stroke([line((xs, y), (xe, y))], t)
        return c

    def _turnstile(self, glyph, double: bool, slash: bool, flip=False):
        g = self.g
        t = g.tc if double else g.t
        xs = g.xm - g.w * 0.40 + t / 2.0
        xe = g.xm + g.w * 0.46
        mid = params.CAP_HEIGHT / 2.0
        sp = (t + max(0.55 * t, 26)) / 2.0
        ys = [mid - sp, mid + sp] if double else [mid]
        c = self._stem_arms(xs, ys, xe, t)
        if flip:
            c = [[tuple((2 * g.xm - p[0], p[1]) for p in s) for s in reverse(ct)] for ct in c]
        self._finish(glyph, c)
        if slash:
            self._add_slash(glyph, mid, params.CAP_HEIGHT * 0.5, cx=g.xm)

    def s_22A2(self, glyph):
        self._turnstile(glyph, False, False)

    def s_22A3(self, glyph):
        self._turnstile(glyph, False, False, flip=True)

    def s_22A8(self, glyph):
        self._turnstile(glyph, True, False)

    def s_22AC(self, glyph):
        self._turnstile(glyph, False, True)

    def s_22AD(self, glyph):
        self._turnstile(glyph, True, True)

    # -- therefore / because ----------------------------------------------
    def _three_dots(self, glyph, up: bool):
        g = self.g
        r = g.r
        pts = [(g.xm, g.ax + r), (g.xm - g.w * 0.30, g.ax - r), (g.xm + g.w * 0.30, g.ax - r)]
        if not up:
            pts = [(g.xm, g.ax - r), (g.xm - g.w * 0.30, g.ax + r), (g.xm + g.w * 0.30, g.ax + r)]
        pen = glyph.getPen()
        d = self.font[self.namer("·")]
        x0, y0, x1, y1 = _bounds(d)
        for cx, cy in pts:
            tp = TransformPen(pen, Transform(1, 0, 0, 1, cx - (x0 + x1) / 2.0, cy - (y0 + y1) / 2.0))
            d.draw(tp)
        glyph.width = round(g.x1 + g.x0)

    def s_2234(self, glyph):
        self._three_dots(glyph, True)

    def s_2235(self, glyph):
        self._three_dots(glyph, False)

    # -- equivalence ------------------------------------------------------
    def _equiv(self, glyph, slash):
        g, tc = self.g, self.g.tc
        sp = tc + max(0.5 * tc, 24)
        hw = g.w * 0.5
        c = []
        for k in (-1, 0, 1):
            y = g.ax + k * sp
            c += stroke([line((g.xm - hw, y), (g.xm + hw, y))], tc)
        self._finish(glyph, c)
        if slash:
            self._add_slash(glyph, g.ax, g.rk * 1.05, cx=g.xm)

    def s_2261(self, glyph):
        self._equiv(glyph, False)

    def s_2262(self, glyph):
        self._equiv(glyph, True)

    # -- membership and subsets -------------------------------------------
    def _cee(self, flip: bool, t, r=None, cy=None, w=0.78):
        """A C-shaped bracket opening right (left if flip): the body of
        ∈ / ⊂."""
        g = self.g
        r = g.r if r is None else r
        cy = g.ax if cy is None else cy
        wd = g.w * w
        xl, xr = g.xm - wd / 2.0, g.xm + wd / 2.0
        rr = min(r, wd * 0.5) - 1.0   # never a zero-length side: same structure at every master
        p = join(
            [line((xr, cy + r), (xl + rr, cy + r))],
            arc(xl + rr, cy + (r - rr), rr, 90, 180),
            [line((xl, cy + (r - rr)), (xl, cy - (r - rr)))],
            arc(xl + rr, cy - (r - rr), rr, 180, 270),
            [line((xl + rr, cy - r), (xr, cy - r))],
        )
        c = stroke(p, t)
        if flip:
            c = [reverse([tuple((2 * g.xm - q[0], q[1]) for q in s) for s in ct]) for ct in c]
        return c, (xl, xr)

    def _member(self, glyph, flip, slash):
        g, tc = self.g, self.g.tc
        c, (xl, xr) = self._cee(flip, tc, r=g.rc)
        bar = stroke([line((xl, g.ax), (xr, g.ax))], tc)
        if flip:
            bar = [reverse([tuple((2 * g.xm - q[0], q[1]) for q in s) for s in ct]) for ct in bar]
        self._finish(glyph, c + bar)
        if slash:
            self._add_slash(glyph, g.ax, g.rk * 1.05, cx=g.xm)

    def s_2208(self, glyph):
        self._member(glyph, False, False)

    def s_2209(self, glyph):
        self._member(glyph, False, True)

    def s_220B(self, glyph):
        self._member(glyph, True, False)

    def s_220C(self, glyph):
        self._member(glyph, True, True)

    def _subset(self, glyph, flip, under, slash):
        g = self.g
        if not under:
            c, _ = self._cee(flip, g.t, w=0.74)
            self._finish(glyph, c)
        else:
            tc = g.tc
            gap = max(0.45 * tc, 28)
            top = g.ax + g.rk - tc / 2.0
            bar_y = g.ax - g.rk * 1.12 + tc / 2.0
            bottom = bar_y + tc + gap
            r = (top - bottom) / 2.0
            c, (xl, xr) = self._cee(flip, tc, r=r, cy=(top + bottom) / 2.0, w=0.74)
            bar = stroke([line((xl, bar_y), (xr, bar_y))], tc)
            if flip:
                bar = [reverse([tuple((2 * g.xm - q[0], q[1]) for q in s) for s in ct]) for ct in bar]
            self._finish(glyph, c + bar)
        if slash:
            self._add_slash(glyph, g.ax, g.rk * 1.05, cx=g.xm)

    def s_2282(self, glyph):
        self._subset(glyph, False, False, False)

    def s_2283(self, glyph):
        self._subset(glyph, True, False, False)

    def s_2284(self, glyph):
        self._subset(glyph, False, False, True)

    def s_2285(self, glyph):
        self._subset(glyph, True, False, True)

    def s_2286(self, glyph):
        self._subset(glyph, False, True, False)

    def s_2287(self, glyph):
        self._subset(glyph, True, True, False)

    def s_2288(self, glyph):
        self._subset(glyph, False, True, True)

    def s_2289(self, glyph):
        self._subset(glyph, True, True, True)

    # -- union, intersection, set minus, compose --------------------------
    def _cup(self, glyph, up):
        g = self.g
        hw = g.w * 0.38
        r = hw
        yt, yb = g.ax + g.r, g.ax - g.r
        if not up:   # ∪: open at the top
            p = join([line((g.xm - hw, yt), (g.xm - hw, yb + r))],
                     arc(g.xm, yb + r, r, 180, 360),
                     [line((g.xm + hw, yb + r), (g.xm + hw, yt))])
        else:        # ∩: open at the bottom
            p = join([line((g.xm - hw, yb), (g.xm - hw, yt - r))],
                     arc(g.xm, yt - r, r, 180, 0),
                     [line((g.xm + hw, yt - r), (g.xm + hw, yb))])
        self._finish(glyph, stroke(p, g.t))

    def s_222A(self, glyph):
        self._cup(glyph, False)

    def s_2229(self, glyph):
        self._cup(glyph, True)

    def s_2216(self, glyph):   # ∖
        g = self.g
        sh = g.r
        sw = sh * 0.6
        self._finish(glyph, stroke([line((g.xm - sw, g.ax + sh), (g.xm + sw, g.ax - sh))], g.t))

    def s_2218(self, glyph):   # ∘
        g = self.g
        self._finish(glyph, self._circle(g.rc * 0.62, g.tc))

    # -- arrows -------------------------------------------------------------
    def _head(self, x, y, h, direction, t):
        """Chevron arrowhead with its tip at (x, y), pointing right (+1) or left (-1)."""
        return stroke(polyline((x - direction * h, y + h), (x, y), (x - direction * h, y - h)), t)

    def _arrow(self, glyph, left=False, right=True, tail=False, double=False, long_=False):
        g = self.g
        t = g.tc
        both = left and right
        half = g.w * (0.72 if long_ else (0.8 if (both and double) else 0.62 if both else 0.5))
        h = (g.r * 0.62) if not double else g.r * 0.7
        tip_in = t * 0.75
        xl, xr = g.xm - half, g.xm + half
        c = []
        sp = (t + max(0.6 * t, 26)) / 2.0 if double else 0.0
        ys = [g.ax - sp, g.ax + sp] if double else [g.ax]
        sl = xl + (tip_in + sp if left else 0.0) + (t / 2.0 if tail else 0.0)
        sr = xr - (tip_in + sp if right else 0.0)
        if double:
            sl = xl + (sp + tip_in if left else 0.0)
            sr = xr - (sp + tip_in if right else 0.0)
        for y in ys:
            c += stroke([line((sl, y), (sr, y))], t)
        if right:
            c += self._head(xr - tip_in, g.ax, h, 1, t)
        if left:
            c += self._head(xl + tip_in, g.ax, h, -1, t)
        if tail:
            c += stroke([line((xl + t / 2.0, g.ax - h), (xl + t / 2.0, g.ax + h))], t)
        self._finish(glyph, c, span=(xl, xr))

    def s_2190(self, glyph):
        self._arrow(glyph, left=True, right=False)

    def s_2192(self, glyph):
        self._arrow(glyph)

    def s_2194(self, glyph):
        self._arrow(glyph, left=True, right=True)

    def s_21A6(self, glyph):
        self._arrow(glyph, tail=True)

    def s_21D0(self, glyph):
        self._arrow(glyph, left=True, right=False, double=True)

    def s_21D2(self, glyph):
        self._arrow(glyph, double=True)

    def s_21D4(self, glyph):
        self._arrow(glyph, left=True, right=True, double=True)

    def s_27F8(self, glyph):
        self._arrow(glyph, left=True, right=False, double=True, long_=True)

    def s_27F9(self, glyph):
        self._arrow(glyph, double=True, long_=True)

    def s_27FA(self, glyph):
        self._arrow(glyph, left=True, right=True, double=True, long_=True)

    # -- modal and proof marks ---------------------------------------------
    def s_25A1(self, glyph):   # □
        g = self.g
        h = g.rc
        self._finish(glyph, ring(polyline((g.xm - h, g.ax + h), (g.xm + h, g.ax + h), (g.xm + h, g.ax - h), (g.xm - h, g.ax - h), closed=True), g.tc))

    def s_25C7(self, glyph):   # ◇
        g = self.g
        h = g.rc * 1.12
        self._finish(glyph, ring(polyline((g.xm, g.ax + h), (g.xm + h, g.ax), (g.xm, g.ax - h), (g.xm - h, g.ax), closed=True), g.tc))

    def s_220E(self, glyph):   # ∎
        g = self.g
        h = g.rk * 0.5
        self._finish(glyph, fill(polyline((g.xm - h, g.ax + h), (g.xm + h, g.ax + h), (g.xm + h, g.ax - h), (g.xm - h, g.ax - h), closed=True)))
