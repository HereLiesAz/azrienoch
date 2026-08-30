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
