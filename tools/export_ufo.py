"""Export a single UFO master on demand, for opening directly in an
external point editor (Fontra and the like) -- without regenerating
every master and recompiling the variable font the way
`designspace_build` does. Every glyph is still built the same way
(`ufo_build.build_master_ufo`, the same quirks/masters pipeline), just
for one (wght, wdth, serf, grad) location instead of the whole grid, so
it's fast enough to run on demand.

    python3 -m tools.export_ufo
    python3 -m tools.export_ufo --wght 700 --wdth 75 --serf 100 --grad 50
    python3 -m tools.export_ufo --out /tmp/Azrienoch-Regular.ufo

Defaults to Regular/Normal/Sans/Grade0 -- the same location the in-browser
point editor showed.
"""

from __future__ import annotations

import argparse
import pathlib
import shutil

from tools import params as P
from tools import ufo_build as U


def export_ufo(wght: int, wdth: int, serf: int, grad: int, out: pathlib.Path | None = None) -> pathlib.Path:
    if wght not in P.WGHT_SAMPLES:
        raise SystemExit(f"wght must be one of {P.WGHT_SAMPLES}, got {wght}")
    if wdth not in P.WDTH_SAMPLES:
        raise SystemExit(f"wdth must be one of {P.WDTH_SAMPLES}, got {wdth}")
    if serf not in P.SERF_SAMPLES:
        raise SystemExit(f"serf must be one of {P.SERF_SAMPLES}, got {serf}")
    if grad not in P.GRAD_SAMPLES:
        raise SystemExit(f"grad must be one of {P.GRAD_SAMPLES}, got {grad}")

    path = U.build_master_ufo(wght, wdth, serf, grad)
    if out is not None and out != path:
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.exists():
            shutil.rmtree(out)
        shutil.move(str(path), str(out))
        path = out
    print("wrote", path)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--wght", type=int, default=P.WGHT_DEFAULT, choices=P.WGHT_SAMPLES)
    parser.add_argument("--wdth", type=int, default=P.WDTH_DEFAULT, choices=P.WDTH_SAMPLES)
    parser.add_argument("--serf", type=int, default=P.SERF_DEFAULT, choices=P.SERF_SAMPLES)
    parser.add_argument("--grad", type=int, default=P.GRAD_DEFAULT, choices=P.GRAD_SAMPLES)
    parser.add_argument("--out", type=pathlib.Path, default=None, help="output .ufo path (default: sources/)")
    args = parser.parse_args()
    export_ufo(args.wght, args.wdth, args.serf, args.grad, args.out)


if __name__ == "__main__":
    main()
