"""Writes sources/AzrienochV2.designspace and compiles the variable TTF
via fontmake. Run as `python3 -m v2.tools.designspace_build` from the
repo root."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from fontTools.designspaceLib import (
    AxisDescriptor,
    AxisLabelDescriptor,
    DesignSpaceDocument,
    InstanceDescriptor,
    SourceDescriptor,
)

from . import params
from .ufo_build import SOURCES_DIR, build_all

ROOT = Path(__file__).resolve().parent.parent
DESIGNSPACE_PATH = SOURCES_DIR / "AzrienochV2.designspace"
FONTS_DIR = ROOT / "fonts" / "variable"
OUTPUT_TTF = FONTS_DIR / "AzrienochV2-VF.ttf"

# axis tag -> {axis value: name} for the STAT table's own axis-value
# labels (params.py's WGHT_NAMES/WDTH_NAMES/SERF_NAMES, keyed the same
# way as params.AXES's own tags).
_AXIS_VALUE_NAMES = {
    "wght": params.WGHT_NAMES, "wdth": params.WDTH_NAMES, "SERF": params.SERF_NAMES, "GRAD": params.GRAD_NAMES,
}


def _add_axis_labels(axis: AxisDescriptor, value_names: dict, default, elide_default: bool = True) -> None:
    for value, name in value_names.items():
        if not name:
            # GRAD's own default (see params.GRAD_NAMES): unlike
            # wdth/SERF's own defaults ("Normal"/"Sans", real names that
            # just happen to be elidable), GRAD=0 has no name at all to
            # begin with -- an empty-string STAT AxisValue would be a
            # malformed label, not a correctly-elided one.
            continue
        axis.axisLabels.append(
            AxisLabelDescriptor(name=name, userValue=value, elidable=(elide_default and value == default))
        )


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
        # wght's own default ("Regular") is never elided: fontTools
        # derives each named instance's actual subfamily name from
        # these STAT axis labels' elision rules, not from the
        # InstanceDescriptor.styleName set below -- eliding wght's
        # default the normal way (matching wdth/SERF, where it's
        # correct: "Normal"/"Sans" should drop out of "Thin Condensed",
        # not linger as "Thin Condensed Normal Sans") made "Regular"
        # vanish from EVERY instance that shares its weight, not just
        # the one truly-default instance -- "Condensed"/"Slab" instead
        # of the intended "Condensed Regular"/"Slab Regular" (confirmed
        # by dumping fvar's own instances after the first attempt).
        _add_axis_labels(
            a, _AXIS_VALUE_NAMES[axis["tag"]], axis["default"], elide_default=(axis["tag"] != "wght")
        )
        doc.addAxis(a)

    for path, (wght, wdth, serf, grad) in zip(ufo_paths, params.MASTER_GRID):
        s = SourceDescriptor()
        s.path = str(path)
        s.name = params.style_name(wght, wdth, serf, grad)
        s.styleName = params.style_name(wght, wdth, serf, grad)
        s.familyName = "Azrienoch V2"
        s.location = {"wght": wght, "wdth": wdth, "SERF": serf, "GRAD": grad}
        if (wght, wdth, serf, grad) == params.DEFAULT_LOCATION:
            s.copyLib = True
            s.copyInfo = True
            s.copyGroups = True
            s.copyFeatures = True
        doc.addSource(s)

        # Every master grid point is a real, deliberately-designed style
        # here (unlike the repository root's own v1 designspace, which
        # has an extra wght=250 master that only shortens an
        # interpolation gap and isn't meant to be user-facing) -- so
        # every one of them gets an fvar named instance, not just the
        # default location. Without this, the font's full Thin-to-Black,
        # Normal-to-Condensed, Sans-to-Slab range still interpolates
        # correctly, but no style picker outside a raw axis-slider view
        # can reach any of it except the implicit default ("Regular"),
        # which was v2's actual bug: 12 real masters, one visible style.
        inst = InstanceDescriptor()
        inst.familyName = "Azrienoch V2"
        inst.styleName = params.instance_style_name(wght, wdth, serf, grad)
        inst.location = {"wght": wght, "wdth": wdth, "SERF": serf, "GRAD": grad}
        doc.addInstance(inst)

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
