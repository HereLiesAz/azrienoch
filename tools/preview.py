"""Quick visual QA: render a row of glyphs straight from glyphset.py,
bypassing the UFO/compile pipeline, for fast iteration on letterforms."""

from __future__ import annotations

import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch

sys.path.insert(0, ".")
from tools import glyphset as G
from tools import params as P


def _mid(a, b):
    return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)


def contour_to_mpl(contour):
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


def render_row(names, wght, wdth, serf, out_path, gap=60):
    m = P.metrics_for(wght, wdth, serf)
    fig, ax = plt.subplots(figsize=(len(names) * 1.1, 2.2))
    x = 0
    for name in names:
        fn = getattr(G, f"cap_{name}", None) or getattr(G, f"low_{name}", None) or getattr(G, f"dig_{name}", None)
        if fn is None:
            x += 400
            continue
        shape, w = fn(m)
        path = glyph_to_path(shape, ox=x)
        ax.add_patch(PathPatch(path, facecolor="black", edgecolor="none"))
        ax.axhline(0, color="#ccc", lw=0.5, zorder=-1)
        ax.axhline(m.cap_height, color="#ccc", lw=0.5, zorder=-1)
        ax.axhline(m.x_height, color="#e0e0e0", lw=0.5, zorder=-1)
        x += w + gap
    ax.set_xlim(-40, x)
    ax.set_ylim(m.descender - 60, m.ascender + 100)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)
    print("wrote", out_path)


if __name__ == "__main__":
    names = list(sys.argv[1]) if len(sys.argv) > 1 else list("IHEFLTNMUVAWXYZKOQDCGSBPRJ")
    wght = float(sys.argv[2]) if len(sys.argv) > 2 else 400
    wdth = float(sys.argv[3]) if len(sys.argv) > 3 else 100
    serf = float(sys.argv[4]) if len(sys.argv) > 4 else 0
    out = sys.argv[5] if len(sys.argv) > 5 else "/tmp/preview.png"
    render_row(names, wght, wdth, serf, out)
