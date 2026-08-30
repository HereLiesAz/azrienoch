"""Write Azrienoch's .designspace and compile the variable font with fontmake."""

from __future__ import annotations

import pathlib
import subprocess
import sys

from fontTools.designspaceLib import (
    AxisDescriptor,
    AxisLabelDescriptor,
    DesignSpaceDocument,
    InstanceDescriptor,
    SourceDescriptor,
)

from tools import params as P
from tools import ufo_build as U

HERE = pathlib.Path(__file__).resolve().parent.parent
DESIGNSPACE_PATH = HERE / "sources" / "Azrienoch.designspace"
OUTPUT_TTF = HERE / "fonts" / "variable" / "Azrienoch-VF.ttf"

# STAT axis-value stops for each axis, keyed by the same values used in the
# master grid -- feeds both the STAT table (so design apps show a proper
# "Weight"/"Width"/"Serif" style picker instead of raw axis sliders) and
# the family-name half of each named instance below.
WGHT_LABELS = {100: "Thin", 400: "Regular", 900: "Black"}
WDTH_LABELS = {75: "Condensed", 100: "Normal"}
SERF_LABELS = {0: "Sans", 100: "Serif"}


def _add_axis_labels(axis, value_labels: dict, default):
    for value, name in value_labels.items():
        axis.axisLabels.append(
            AxisLabelDescriptor(name=name, userValue=value, elidable=(value == default))
        )


def write_designspace(ufo_paths: dict) -> pathlib.Path:
    doc = DesignSpaceDocument()

    for tag, minimum, default, maximum, label, value_labels in (
        ("wght", *P.WGHT_AXIS[1:], "Weight", WGHT_LABELS),
        ("wdth", *P.WDTH_AXIS[1:], "Width", WDTH_LABELS),
        ("SERF", *P.SERF_AXIS[1:], "Serif", SERF_LABELS),
    ):
        axis = AxisDescriptor()
        axis.tag = tag
        axis.name = tag
        axis.minimum = minimum
        axis.default = default
        axis.maximum = maximum
        axis.labelNames = {"en": label}
        _add_axis_labels(axis, value_labels, default)
        doc.addAxis(axis)

    for (wght, wdth, serf), path in ufo_paths.items():
        src = SourceDescriptor()
        src.path = str(path)
        src.name = f"source.{P.master_name(wght, wdth, serf)}"
        src.familyName = "Azrienoch"
        src.styleName = P.master_name(wght, wdth, serf)
        src.location = {"wght": wght, "wdth": wdth, "SERF": serf}
        if (wght, wdth, serf) == (400, 100, 0):
            src.copyLib = True
            src.copyInfo = True
            src.copyGroups = True
            src.copyFeatures = True
        doc.addSource(src)

        inst = InstanceDescriptor()
        inst.familyName = "Azrienoch"
        inst.styleName = P.master_name(wght, wdth, serf)
        inst.location = {"wght": wght, "wdth": wdth, "SERF": serf}
        doc.addInstance(inst)

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

    from tools import validate_build

    validate_build.main()
