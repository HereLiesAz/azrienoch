"""Zips the UFO sources for download (the proof page's UFO options fetch
these from master), so they are always the current build.

- `fonts/ufo/Azrienoch-UFO-masters.zip`: all 54 master UFOs plus
  `Azrienoch.designspace`, i.e. the whole `sources/` directory.

    python3 -m tools.package_ufo
"""

from __future__ import annotations

import pathlib
import zipfile

HERE = pathlib.Path(__file__).resolve().parent.parent
SOURCES = HERE / "sources"
OUT_DIR = HERE / "fonts" / "ufo"


def _zip(out: pathlib.Path, root: pathlib.Path, top: str) -> None:
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(root.rglob("*")):
            rel = p.relative_to(root)
            if p.is_file():
                z.write(p, f"{top}/{rel}" if top else str(rel))


def package() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _zip(OUT_DIR / "Azrienoch-UFO-masters.zip", SOURCES, "Azrienoch-UFO")
    for p in sorted(OUT_DIR.glob("*.zip")):
        print(f"packaged {p} ({p.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    package()
