"""Zips the UFO sources for download (the proof page's UFO options fetch
these from master), so they are always the current build.

- `fonts/ufo/Azrienoch-UFO-masters.zip`: all 36 master UFOs plus
  `Azrienoch.designspace`, i.e. the whole `sources/` directory.
- `fonts/ufo/Azrienoch-Regular.ufo.zip`: just the default master
  (wght 400, wdth 100, SERF 0, GRAD 0).

    python3 -m tools.package_ufo
"""

from __future__ import annotations

import pathlib
import zipfile

HERE = pathlib.Path(__file__).resolve().parent.parent
SOURCES = HERE / "sources"
OUT_DIR = HERE / "fonts" / "ufo"
REGULAR = "Azrienoch-Wght400_Wdth100_Serf0_Grad0.ufo"


def _zip(out: pathlib.Path, root: pathlib.Path, top: str, only: str | None = None) -> None:
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(root.rglob("*")):
            rel = p.relative_to(root)
            if p.is_file() and (only is None or rel.parts[0] == only):
                z.write(p, f"{top}/{rel}" if top else str(rel))


def package() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _zip(OUT_DIR / "Azrienoch-UFO-masters.zip", SOURCES, "Azrienoch-UFO")
    _zip(OUT_DIR / "Azrienoch-Regular.ufo.zip", SOURCES, "", REGULAR)
    for p in sorted(OUT_DIR.glob("*.zip")):
        print(f"packaged {p} ({p.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    package()
