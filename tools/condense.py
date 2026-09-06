"""Stem-width-preserving horizontal compression for the `wdth` axis.

Both `jost_source.py` and `arimo_source.py` used to realize `wdth` as a
uniform `x *= wdth/100` on every point -- cheap, but it compresses a
vertical stem's actual ink width by the same factor it compresses a
counter's open space, so at heavy weight (where stems are already close
to a stroke's worth of the glyph's total width) the stem visibly thins
out relative to the horizontal strokes that don't get thinned by a
horizontal squish at all (a crossbar's or crossbar-adjacent curve's
thickness is a Y-extent, untouched by scaling X) -- confirmed by
rendering the full alphabet at wght=900/wdth=75 and comparing stroke
weights directly: every stem reads visibly thinner than the horizontal
strokes on the same letter, the tell of a plain squish rather than a
real condensed cut.

The fix: instead of one compression factor for the whole glyph, derive a
per-x compression profile from where the glyph actually has ink. Sample
a vertical "ink density" (the fraction of sampled heights where that x
falls inside some contour) across the glyph's own advance width, then
solve for a compression function that leaves fully-inked x (stem
regions) essentially uncompressed and pushes the required narrowing
into x with little or no ink (counters, sidebearings) instead. This
isn't a real optically-redrawn condensed cut -- no counters are
reshaped, no strokes are individually identified -- it's a global,
per-x warp applied uniformly regardless of height, so a diagonal
stroke's x position (which moves with y) only gets partial credit
proportional to how much of the glyph's height it occupies at each x.
Still a meaningfully closer approximation to real condensed type than a
flat scale, which is all the previous version did.

The same profile generalizes to EXPANSION (`wf` > 1), used by
`arimo_source.py` to rescale `c`/`e`/`s` to Jost's own `ch`-to-'o' width
ratio (see that module's own docstring): stems stay close to unchanged
while the extra width goes into counters/sidebearings, for the same
reason compression concentrates its narrowing there. A plain uniform
`x *= wf` expansion was tried there first and rejected the same way the
flat `wdth` scale was: at Thin, `c`'s own target width needed a 33%
horizontal stretch, and applying that uniformly fattened its already-
flattened terminal cut -- purely a horizontal-direction structure, so a
horizontal-only scale multiplies its thickness by `wf` directly -- into
a visibly thick club relative to the rest of the ring, whose wall
thickness at top/bottom is mostly a Y-extent and so barely responded to
the same scale. Confirmed directly: rendering `o`/`c`/`e`/`s` together
at Thin showed exactly that mismatch, gone once the width-matching
scale went through this same ink-density profile instead of a flat one.
"""

from __future__ import annotations


def _flatten(pen_value, samples_per_segment: int = 6):
    """Flattens TrueType pen commands (on/off-curve qCurveTo runs,
    including the implied-on-curve-at-start convention marked by a
    trailing `None`) into per-contour polylines, for ink-density
    sampling only -- not for final glyph output."""
    contours = []
    current: list[tuple[float, float]] = []
    current_point = None
    start_point = None
    for cmd, args in pen_value:
        if cmd == "moveTo":
            current_point = args[0]
            start_point = current_point
            current = [current_point]
        elif cmd == "lineTo":
            current.append(args[0])
            current_point = args[0]
        elif cmd == "qCurveTo":
            *offs, on = args
            if on is None:
                on = start_point
            if not offs:
                current.append(on)
                current_point = on
                continue
            anchors = (
                [current_point]
                + [
                    ((offs[j][0] + offs[j + 1][0]) / 2.0, (offs[j][1] + offs[j + 1][1]) / 2.0)
                    for j in range(len(offs) - 1)
                ]
                + [on]
            )
            for j in range(len(offs)):
                p0, ctrl, p1 = anchors[j], offs[j], anchors[j + 1]
                for step in range(1, samples_per_segment + 1):
                    t = step / samples_per_segment
                    x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * ctrl[0] + t ** 2 * p1[0]
                    y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * ctrl[1] + t ** 2 * p1[1]
                    current.append((x, y))
            current_point = on
        elif cmd in ("closePath", "endPath"):
            if current:
                contours.append(current)
            current = []
    if current:
        contours.append(current)
    return contours


def _point_in_contours(contours, x: float, y: float) -> bool:
    """Even-odd ray-casting test across every contour combined -- a
    heuristic density probe, not a rendering-accurate fill rule, but
    letterforms with simple nested contours (the only kind here) give
    the same answer either way."""
    inside = False
    for points in contours:
        n = len(points)
        for i in range(n):
            x1, y1 = points[i]
            x2, y2 = points[(i + 1) % n]
            if (y1 > y) != (y2 > y):
                x_at_y = x1 + (y - y1) / (y2 - y1) * (x2 - x1)
                if x < x_at_y:
                    inside = not inside
    return inside


def condense_x(pen_value, width: float, wf: float, x_buckets: int = 48, y_samples: int = 20):
    """Returns (new_pen_value, new_width): `pen_value` rescaled toward
    `width * wf` on the X axis only, `wf` <1 (compress) or >1 (expand),
    using more of the change where the glyph has less ink at that X and
    closer to none where it has the most -- see module docstring. Falls
    back to a plain uniform scale when there's no ink to sample (e.g.
    `space`) or nothing to redistribute the change into."""
    if wf == 1.0 or width <= 0:
        return pen_value, width

    def uniform():
        scaled = [
            (cmd, tuple(None if pt is None else (pt[0] * wf, pt[1]) for pt in args))
            for cmd, args in pen_value
        ]
        return scaled, width * wf

    contours = _flatten(pen_value)
    all_points = [p for c in contours for p in c]
    if not all_points:
        return uniform()

    ys = [p[1] for p in all_points]
    ymin, ymax = min(ys), max(ys)
    if ymax - ymin < 1e-6:
        return uniform()

    bucket_w = width / x_buckets
    y_coords = [ymin + (j + 0.5) / y_samples * (ymax - ymin) for j in range(y_samples)]
    density = []
    for i in range(x_buckets):
        xc = (i + 0.5) * bucket_w
        hits = sum(1 for y in y_coords if _point_in_contours(contours, xc, y))
        density.append(hits / y_samples)

    stem_mass = sum(d * bucket_w for d in density)
    counter_mass = width - stem_mass
    if counter_mass < width * 1e-3:
        k = 0.0
    else:
        k = abs(wf - 1.0) * width / counter_mass
        if wf < 1.0:
            k = max(0.0, min(1.0, k))

    sign = 1.0 if wf > 1.0 else -1.0
    f = [max(0.0, 1.0 + sign * k * (1.0 - d)) for d in density]

    cum = [0.0] * (x_buckets + 1)
    for i in range(x_buckets):
        cum[i + 1] = cum[i] + f[i] * bucket_w

    def warp(x: float) -> float:
        if x <= 0:
            return 0.0
        if x >= width:
            return cum[-1]
        idx = min(int(x / bucket_w), x_buckets - 1)
        frac = (x - idx * bucket_w) / bucket_w
        return cum[idx] + frac * f[idx] * bucket_w

    new_pen_value = [
        (cmd, tuple(None if pt is None else (warp(pt[0]), pt[1]) for pt in args))
        for cmd, args in pen_value
    ]
    return new_pen_value, cum[-1]
