"""Write Multiplex's .designspace and compile the variable font with fontmake."""

from __future__ import annotations

import pathlib
import subprocess
import sys

from fontTools.designspaceLib import AxisDescriptor, DesignSpaceDocument, SourceDescriptor

from tools import params as P
from tools import ufo_build as U

HERE = pathlib.Path(__file__).resolve().parent.parent
DESIGNSPACE_PATH = HERE / "sources" / "Multiplex.designspace"
OUTPUT_TTF = HERE / "fonts" / "variable" / "Multiplex-VF.ttf"


def write_designspace(ufo_paths: dict) -> pathlib.Path:
    doc = DesignSpaceDocument()

    for tag, minimum, default, maximum, label in (
        ("wght", *P.WGHT_AXIS[1:], "Weight"),
        ("wdth", *P.WDTH_AXIS[1:], "Width"),
        ("SERF", *P.SERF_AXIS[1:], "Serif"),
    ):
        axis = AxisDescriptor()
        axis.tag = tag
        axis.name = tag
        axis.minimum = minimum
        axis.default = default
        axis.maximum = maximum
        axis.labelNames = {"en": label}
        doc.addAxis(axis)

    for (wght, wdth, serf), path in ufo_paths.items():
        src = SourceDescriptor()
        src.path = str(path)
        src.name = f"source.{P.master_name(wght, wdth, serf)}"
        src.familyName = "Multiplex"
        src.styleName = P.master_name(wght, wdth, serf)
        src.location = {"wght": wght, "wdth": wdth, "SERF": serf}
        if (wght, wdth, serf) == (400, 100, 0):
            src.copyLib = True
            src.copyInfo = True
            src.copyGroups = True
            src.copyFeatures = True
        doc.addSource(src)

    doc.write(str(DESIGNSPACE_PATH))
    return DESIGNSPACE_PATH


def compile_variable_font():
    OUTPUT_TTF.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable, "-m", "fontmake",
        "-m", str(DESIGNSPACE_PATH),
        "-o", "variable",
        "--output-path", str(OUTPUT_TTF),
        "--verbose", "WARNING",
    ]
    subprocess.run(cmd, check=True, cwd=str(HERE))
    print("compiled", OUTPUT_TTF)


if __name__ == "__main__":
    paths = U.build_all()
    ds_path = write_designspace(paths)
    print("wrote", ds_path)
    compile_variable_font()
