"""Writes sources/AzrienochV2.designspace and compiles the variable TTF
via fontmake. Run as `python3 -m v2.tools.designspace_build` from the
repo root."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from fontTools.designspaceLib import AxisDescriptor, DesignSpaceDocument, SourceDescriptor

from . import params
from .ufo_build import SOURCES_DIR, build_all

ROOT = Path(__file__).resolve().parent.parent
DESIGNSPACE_PATH = SOURCES_DIR / "AzrienochV2.designspace"
FONTS_DIR = ROOT / "fonts" / "variable"
OUTPUT_TTF = FONTS_DIR / "AzrienochV2-VF.ttf"


def write_designspace(ufo_paths: list[Path]) -> Path:
    doc = DesignSpaceDocument()

    for axis in params.AXES:
        a = AxisDescriptor()
        a.tag = axis["tag"]
        a.name = axis["tag"]
        a.labelNames = {"en": axis["name"]}
        a.minimum = axis["minimum"]
        a.default = axis["default"]
        a.maximum = axis["maximum"]
        doc.addAxis(a)

    for path, (wght, wdth, serf) in zip(ufo_paths, params.MASTER_GRID):
        s = SourceDescriptor()
        s.path = str(path)
        s.name = params.style_name(wght, wdth, serf)
        s.styleName = params.style_name(wght, wdth, serf)
        s.familyName = "Azrienoch V2"
        s.location = {"wght": wght, "wdth": wdth, "SERF": serf}
        if (wght, wdth, serf) == params.DEFAULT_LOCATION:
            s.copyLib = True
            s.copyInfo = True
            s.copyGroups = True
            s.copyFeatures = True
        doc.addSource(s)

    doc.write(DESIGNSPACE_PATH)
    return DESIGNSPACE_PATH


def compile_variable_font(designspace_path: Path) -> None:
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            sys.executable, "-m", "fontmake",
            "-m", str(designspace_path),
            "-o", "variable",
            "--output-path", str(OUTPUT_TTF),
        ],
        check=True,
    )


def main() -> None:
    ufo_paths = build_all()
    designspace_path = write_designspace(ufo_paths)
    compile_variable_font(designspace_path)
    print(f"Built {OUTPUT_TTF}")


if __name__ == "__main__":
    main()
