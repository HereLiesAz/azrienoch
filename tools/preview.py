"""Quick visual QA: render text with the compiled variable font at a given
axis location, bypassing any installed-font/OS text stack, for fast
iteration and sanity-checking during development."""

from __future__ import annotations

import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch
import ufoLib2
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

HERE = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_TTF = HERE / "fonts" / "variable" / "Azrienoch-VF.ttf"


def _mid(a, b):
    return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)


def contour_to_mpl(contour):
    """Convert a ufoLib2 contour (line/cubic 'curve'/TrueType 'qcurve'
    points) into matplotlib Path vertices+codes."""
    pts = [(p.x, p.y, p.type) for p in contour.points]
    start_idx = next(i for i, p in enumerate(pts) if p[2] is not None)
    pts = pts[start_idx:] + pts[:start_idx]
    verts = [(pts[0][0], pts[0][1])]
    codes = [Path.MOVETO]
    pending = []
    n = len(pts)
    for idx in range(1, n + 1):
        p = pts[idx % n]
        if p[2] is None:
            pending.append((p[0], p[1]))
        elif p[2] == "qcurve":
            # TrueType-style: consecutive off-curves imply on-curve
            # midpoints between them; the final on-curve is p itself.
            onc = (p[0], p[1])
            for i, off in enumerate(pending):
                end = _mid(off, pending[i + 1]) if i + 1 < len(pending) else onc
                verts.extend([off, end])
                codes.extend([Path.CURVE3, Path.CURVE3])
            if not pending:
                verts.append(onc)
                codes.append(Path.LINETO)
            pending = []
        else:
            if pending:
                verts.extend(pending)
                verts.append((p[0], p[1]))
                codes.extend([Path.CURVE4, Path.CURVE4, Path.CURVE4])
                pending = []
            else:
                verts.append((p[0], p[1]))
                codes.append(Path.LINETO)
    verts.append(verts[0])
    codes.append(Path.CLOSEPOLY)
    return verts, codes


def flatten_path(verts, codes, steps=50):
    """Sample `verts`/`codes` (matplotlib Path arrays, as returned by
    `contour_to_mpl`) into a dense array of points that actually lie on
    the curve -- `steps` points per curve/line segment.

    NOT the same as `matplotlib.path.Path.interpolated()`: that method's
    own docstring says codes other than LINETO/MOVETO/CLOSEPOLY "are not
    handled correctly" -- it linearly interpolates the raw vertex array,
    which for a CURVE3/CURVE4 segment means treating the off-curve
    control point as if it were itself a polygon corner. `PathPatch`
    rendering isn't affected (matplotlib's renderer evaluates the actual
    bezier when drawing), only code that calls `.interpolated()` to get
    points back out for measurement is -- confirmed by rendering a pure
    circle's control polygon through `.interpolated()` and getting an
    octagon back, not a circle. This evaluates the real quadratic/cubic
    bezier at each step instead.
    """
    import numpy as np

    points = []
    i = 0
    cur = None
    n = len(codes)
    while i < n:
        code = codes[i]
        if code == Path.MOVETO:
            cur = verts[i]
            points.append(cur)
            i += 1
        elif code == Path.LINETO:
            points.append(verts[i])
            cur = verts[i]
            i += 1
        elif code == Path.CURVE3:
            ctrl, end = verts[i], verts[i + 1]
            for t in np.linspace(0, 1, steps)[1:]:
                x = (1 - t) ** 2 * cur[0] + 2 * (1 - t) * t * ctrl[0] + t**2 * end[0]
                y = (1 - t) ** 2 * cur[1] + 2 * (1 - t) * t * ctrl[1] + t**2 * end[1]
                points.append((x, y))
            cur = end
            i += 2
        elif code == Path.CURVE4:
            c1, c2, end = verts[i], verts[i + 1], verts[i + 2]
            for t in np.linspace(0, 1, steps)[1:]:
                mt = 1 - t
                x = mt**3 * cur[0] + 3 * mt**2 * t * c1[0] + 3 * mt * t**2 * c2[0] + t**3 * end[0]
                y = mt**3 * cur[1] + 3 * mt**2 * t * c1[1] + 3 * mt * t**2 * c2[1] + t**3 * end[1]
                points.append((x, y))
            cur = end
            i += 3
        else:  # CLOSEPOLY or anything else
            i += 1
    return np.array(points)


def glyph_to_path(glyph_shape, ox=0, oy=0):
    all_verts, all_codes = [], []
    for c in glyph_shape.contours:
        v, cd = contour_to_mpl(c)
        all_verts.extend([(x + ox, y + oy) for x, y in v])
        all_codes.extend(cd)
    return Path(all_verts, all_codes)


def render_text(ax, text, location, ttf_path=DEFAULT_TTF, x0=0):
    """Draw `text` onto a matplotlib Axes at the given fvar location
    ({"wght":..,"wdth":..,"SERF":..}). Returns the ending x position."""
    font = TTFont(str(ttf_path))
    inst = instancer.instantiateVariableFont(font, location, inplace=False)
    cmap = inst.getBestCmap()
    glyphset = inst.getGlyphSet()
    hmtx = inst["hmtx"]
    x = x0
    for ch in text:
        gname = cmap.get(ord(ch))
        if gname is None:
            x += 500
            continue
        glyph = ufoLib2.objects.Glyph()
        glyphset[gname].drawPoints(glyph.getPointPen())
        if glyph.contours:
            ax.add_patch(PathPatch(glyph_to_path(glyph, ox=x), facecolor="black"))
        x += hmtx[gname][0]
    return x


if __name__ == "__main__":
    text = sys.argv[1] if len(sys.argv) > 1 else "Azrienoch"
    wght = float(sys.argv[2]) if len(sys.argv) > 2 else 400
    wdth = float(sys.argv[3]) if len(sys.argv) > 3 else 100
    serf = float(sys.argv[4]) if len(sys.argv) > 4 else 0
    grad = float(sys.argv[5]) if len(sys.argv) > 5 else 0
    out = sys.argv[6] if len(sys.argv) > 6 else "/tmp/preview.png"

    fig, ax = plt.subplots(figsize=(len(text) * 0.9, 2.4))
    end_x = render_text(ax, text, {"wght": wght, "wdth": wdth, "SERF": serf, "GRAD": grad})
    ax.set_xlim(-100, end_x + 100)
    ax.set_ylim(-700, 2300)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    print("wrote", out)
