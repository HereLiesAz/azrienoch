"""Kerning derived from Azrienoch's own outlines, per master.

Why: Jost's donor kerning (`kerning.py`) is static across `wght` and
knows nothing of the redrawn glyphs (serifs, Y/y hung from a narrowed V,
M's feet, J/Q/S/c/e). This module measures each pair's actual shapes at
each master instead.

Method
------
For a pair (L, R) both glyphs are scanned at every `STEP` units of
height. At each height the horizontal gap is
`advance(L) + left_edge(R) - right_edge(L)`; heights where either glyph
has no ink count as the cap `GAP_CAP` (open space), and each gap is
clipped to that cap. The mean over the pair's height band is the pair's
OPTICAL gap: a pair that touches at one point and opens into a wedge
(A-Y, T-o) reads looser than its closest approach, exactly the
perceptual effect the proof's O-Y entry records, so no single-point
distance is used.

Band: 0 to `CAP_HEIGHT` if either side is a capital or digit, else 0 to
`X_HEIGHT`.

Target: the optical gap of H-H for capital pairs, n-n for lowercase
pairs, their mean for mixed pairs -- the font's own straight-stem
rhythm. kern = STRENGTH * (target - optical), clamped to
[`MIN_KERN`, `MAX_KERN`], raised if needed so the pair's closest approach
stays at least `MIN_CLEAR` (x wdth fraction) -- the optical measure alone
lets a pair overlap at one height -- and dropped below `MIN_ABS` units.

Calibration: `GAP_CAP` and `STRENGTH` are fitted (least squares) to the
five pair values the project owner approved in the proof's Kerning
section -- A-W and W-A -100, A-Y -70, T-O -50, O-Y -100 -- at
wght 400 / wdth 100 (worst residual ~40 units: the model cannot give
A-Y -70 while O-Y is -100). `GAP_CAP` scales with the master's `wdth`
fraction; the result is otherwise computed per master, so kerning now
varies with `wght`, `wdth` and `SERF`.

`PAIR_TIGHTEN` holds per-pair owner overrides (A->Y, Y->A, Y->s: x1.67
strength, clearance 20; Y->A can't simply mirror A->Y's -150: Y's stem meets A's apex). Pairs touching a `DIAGONAL` glyph never get a
positive kern (the open wedge reads as space the model would otherwise
close by loosening). J's empty left side above its hook is treated as
filled out to the hook's leftmost point.

Scope: the 62 base letters/digits. Accented/Cyrillic glyphs that
`params.base_letter` maps onto a base letter inherit that pair's value
(applied in `ufo_build`); every other pair keeps the Jost donor value.
"""

from __future__ import annotations

import numpy as np
from fontTools.pens.basePen import BasePen

from . import params

STEP = 10
GAP_CAP = 280.0
STRENGTH = 0.75
MIN_KERN = -250
MAX_KERN = 80
MIN_ABS = 5
PAIR_TIGHTEN = {("A", "Y"): (150.0 / 90.0, 20.0), ("Y", "A"): (150.0 / 90.0, 20.0), ("Y", "s"): (150.0 / 90.0, 20.0)}  # (strength multiplier, MIN_CLEAR) per pair: owner asked A->Y much tighter
DIAGONAL = set("AKMVWXYZkvwxyz")  # glyphs with a diagonal side: derived kerns for pairs touching them never open up (cap at 0)
MIN_CLEAR = 80.0  # units (x wdth fraction): closest approach of any pair never drops below this


class _Flat(BasePen):
    def __init__(self):
        super().__init__(None)
        self.contours, self.cur = [], []

    def _moveTo(self, p):
        self.cur = [p]

    def _lineTo(self, p):
        self.cur.append(p)

    def _curveToOne(self, a, b, c):
        p0 = self.cur[-1]
        for t in np.linspace(0, 1, 13)[1:]:
            u = 1 - t
            self.cur.append((u**3 * p0[0] + 3 * u * u * t * a[0] + 3 * u * t * t * b[0] + t**3 * c[0],
                             u**3 * p0[1] + 3 * u * u * t * a[1] + 3 * u * t * t * b[1] + t**3 * c[1]))

    def _qCurveToOne(self, a, c):
        p0 = self.cur[-1]
        for t in np.linspace(0, 1, 9)[1:]:
            u = 1 - t
            self.cur.append((u * u * p0[0] + 2 * u * t * a[0] + t * t * c[0],
                             u * u * p0[1] + 2 * u * t * a[1] + t * t * c[1]))

    def _closePath(self):
        if len(self.cur) > 2:
            self.contours.append(self.cur)
        self.cur = []

    _endPath = _closePath


def profile(glyph, ys):
    """(left_edge, right_edge) arrays over `ys`; NaN where no ink."""
    pen = _Flat()
    glyph.draw(pen)
    left = np.full(len(ys), np.nan)
    right = np.full(len(ys), np.nan)
    for c in pen.contours:
        n = len(c)
        for i in range(n):
            (x0, y0), (x1, y1) = c[i], c[(i + 1) % n]
            if y0 == y1:
                continue
            lo, hi = (y0, y1) if y0 < y1 else (y1, y0)
            idx = np.where((ys >= lo) & (ys < hi))[0]
            if not len(idx):
                continue
            x = x0 + (ys[idx] - y0) * (x1 - x0) / (y1 - y0)
            left[idx] = np.fmin(left[idx], x)
            right[idx] = np.fmax(right[idx], x)
    return left, right


def _name(ch: str) -> str:
    from .kerning import _glyph_name
    return _glyph_name(ch)


def base_chars() -> list[str]:
    return [c for c in params.CHARS if len(c) == 1 and c.isascii() and c.isalnum()]


def derive(font, wdth: int) -> dict[tuple[str, str], int]:
    """{(glyph_name, glyph_name): kern} for every pair of base glyphs."""
    cap = GAP_CAP * wdth / 100.0
    top = params.CAP_HEIGHT
    ys = np.arange(0, top, STEP) + STEP / 2.0
    xh_n = int(np.searchsorted(ys, params.X_HEIGHT))
    chars = base_chars()
    prof = {c: profile(font[_name(c)], ys) for c in chars}
    # J's hook hangs below the baseline and its stem sits far right in the
    # advance, so above the baseline its left edge is empty space. Treat
    # that as stem-adjacent: its left edge is the hook's own leftmost point
    # (scanned over the full height incl. the descender) at every row it has ink.
    deep = np.arange(-300, top, STEP) + STEP / 2.0
    j_left = np.nanmin(profile(font[_name("J")], deep)[0])
    jl, jr = prof["J"]
    prof["J"] = (np.where(np.isnan(jl), np.nan, j_left), jr)
    adv = {c: font[_name(c)].width for c in chars}

    def optical(l, r, n):
        d = (adv[l] + prof[r][0][:n]) - prof[l][1][:n]
        return float(np.where(np.isnan(d), cap, np.minimum(d, cap)).mean())

    def closest(l, r):
        d = (adv[l] + prof[r][0]) - prof[l][1]
        return float(np.nanmin(d)) if np.isfinite(d).any() else None

    cap_ref = optical("H", "H", len(ys))
    low_ref = optical("n", "n", xh_n)
    out = {}
    for l in chars:
        for r in chars:
            lu = l.isupper() or l.isdigit()
            ru = r.isupper() or r.isdigit()
            n = len(ys) if (lu or ru) else xh_n
            tgt = cap_ref if (lu and ru) else low_ref if not (lu or ru) else (cap_ref + low_ref) / 2.0
            mult, clear = PAIR_TIGHTEN.get((l, r), (1.0, MIN_CLEAR))
            k = int(round(STRENGTH * mult * (tgt - optical(l, r, n))))
            k = max(MIN_KERN, min(MAX_KERN, k))
            near = closest(l, r)
            if near is not None:
                k = max(k, int(round(clear * wdth / 100.0 - near)))
            if k > 0 and (l in DIAGONAL or r in DIAGONAL):
                k = 0
            out[(_name(l), _name(r))] = k if abs(k) >= MIN_ABS else 0
    return out


def inherit(derived: dict, donor: dict) -> dict:
    """Final pair table: every base-base pair from `derived`; any other
    pair whose two glyphs both map (via `params.base_letter`) onto base
    letters takes that base pair's derived value; the rest keep `donor`."""
    chars = base_chars()
    base_names = {_name(c) for c in chars}
    to_base = {}
    for c in params.CHARS:
        b = params.base_letter(c)
        if len(b) == 1 and b in chars:
            to_base[_name(c)] = _name(b)
    out = dict(derived)
    for (a, b), v in donor.items():
        if a in base_names and b in base_names:
            continue
        ba, bb = to_base.get(a), to_base.get(b)
        out[(a, b)] = derived[(ba, bb)] if ba and bb else v
    return {p: v for p, v in out.items() if v}
