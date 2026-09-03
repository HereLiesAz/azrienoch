"""Quick visual QA: render the proof glyph set at a few axis locations to
a PNG grid, using the compiled variable font's real glyf outlines (via
fontTools.varLib.instancer + a matplotlib PathPatch), not a re-derivation
of the drawing functions. Not part of the build; dev tool only.

Usage: python3 -m v2.tools.preview out.png
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from matplotlib.path import Path as MplPath
from matplotlib.patches import PathPatch

ROOT = Path(__file__).resolve().parent.parent
VF_PATH = ROOT / "fonts" / "variable" / "AzrienochV2-VF.ttf"

GLYPHS = ["H", "O", "o", "n", "v", "T", "l", "one"]
LOCATIONS = [
    ("Thin Normal", {"wght": 100, "wdth": 100}),
    ("Regular Normal", {"wght": 400, "wdth": 100}),
    ("Black Normal", {"wght": 900, "wdth": 100}),
    ("Black Condensed", {"wght": 900, "wdth": 75}),
]


class _MplOutlinePen(BasePen):
    def __init__(self, glyphSet):
        super().__init__(glyphSet)
        self.verts: list[tuple[float, float]] = []
        self.codes: list[int] = []

    def _moveTo(self, pt):
        self.verts.append(pt)
        self.codes.append(MplPath.MOVETO)

    def _lineTo(self, pt):
        self.verts.append(pt)
        self.codes.append(MplPath.LINETO)

    def _curveToOne(self, p1, p2, p3):
        self.verts.extend([p1, p2, p3])
        self.codes.extend([MplPath.CURVE4] * 3)

    def _qCurveToOne(self, p1, p2):
        self.verts.extend([p1, p2])
        self.codes.extend([MplPath.CURVE3] * 2)

    def _closePath(self):
        self.verts.append((0, 0))
        self.codes.append(MplPath.CLOSEPOLY)


def render(out_path: str) -> None:
    fig, axes = plt.subplots(len(LOCATIONS), 1, figsize=(10, 3 * len(LOCATIONS)))
    for ax, (label, loc) in zip(axes, LOCATIONS):
        f = TTFont(VF_PATH)
        instantiateVariableFont(f, loc, inplace=True)
        glyph_set = f.getGlyphSet()
        cursor = 0
        for name in GLYPHS:
            pen = _MplOutlinePen(glyph_set)
            glyph_set[name].draw(pen)
            path = MplPath([(x + cursor, y) for x, y in pen.verts], pen.codes)
            ax.add_patch(PathPatch(path, facecolor="black", edgecolor="none"))
            cursor += glyph_set[name].width + 40
        ax.set_xlim(-40, cursor)
        ax.set_ylim(-300, 800)
        ax.set_aspect("equal")
        ax.set_title(f"{label}  {loc}")
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    render(sys.argv[1] if len(sys.argv) > 1 else "v2_preview.png")
