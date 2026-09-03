"""Export a single UFO master on demand, for opening directly in an
external point editor (Fontra and the like) -- without regenerating all
60 masters and recompiling the variable font the way `designspace_build`
does. Every glyph is still built the same way (`ufo_build.build_master_ufo`,
the same quirks/masters pipeline), just for one (wght, wdth, serf, grad)
location instead of the whole grid, so it's fast enough to run on demand.

    python3 -m tools.export_ufo
    python3 -m tools.export_ufo --wght 700 --wdth 75 --serf 100 --grad 50
    python3 -m tools.export_ufo --out /tmp/Azrienoch-Regular.ufo

Defaults to Regular/Normal/Sans/Grade0 -- the same location the in-browser
point editor showed.
"""

from __future__ import annotations

import argparse
import pathlib

from tools import params as P
from tools import ufo_build as U

HERE = pathlib.Path(__file__).resolve().parent.parent
SOURCES_DIR = HERE / "sources"


def export_ufo(wght: int, wdth: int, serf: int, grad: int, out: pathlib.Path | None = None) -> pathlib.Path:
    if wght not in P.WGHT_MASTERS:
        raise SystemExit(f"wght must be one of {P.WGHT_MASTERS}, got {wght}")
    if wdth not in P.WDTH_MASTERS:
        raise SystemExit(f"wdth must be one of {P.WDTH_MASTERS}, got {wdth}")
    if serf not in P.SERF_MASTERS:
        raise SystemExit(f"serf must be one of {P.SERF_MASTERS}, got {serf}")
    if grad not in P.GRAD_MASTERS:
        raise SystemExit(f"grad must be one of {P.GRAD_MASTERS}, got {grad}")

    feet_by_glyph, dots_by_glyph, reference_contours = U.compute_reference_specs()
    ufo = U.build_master_ufo(wght, wdth, serf, grad, feet_by_glyph, dots_by_glyph, reference_contours)

    if out is None:
        name = P.master_name(wght, wdth, serf, grad)
        out = SOURCES_DIR / f"Azrienoch-{name}.ufo"
    out.parent.mkdir(parents=True, exist_ok=True)
    ufo.save(out, overwrite=True)
    print("wrote", out, "glyphs:", len(ufo), "kerning pairs:", len(ufo.kerning))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--wght", type=int, default=400, choices=P.WGHT_MASTERS)
    parser.add_argument("--wdth", type=int, default=100, choices=P.WDTH_MASTERS)
    parser.add_argument("--serf", type=int, default=0, choices=P.SERF_MASTERS)
    parser.add_argument("--grad", type=int, default=0, choices=P.GRAD_MASTERS)
    parser.add_argument("--out", type=pathlib.Path, default=None, help="output .ufo path (default: sources/)")
    args = parser.parse_args()
    export_ufo(args.wght, args.wdth, args.serf, args.grad, args.out)


if __name__ == "__main__":
    main()
