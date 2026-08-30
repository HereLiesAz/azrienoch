"""Sanity-check the compiled variable font and its UFO masters.

Not a full test suite -- a fast, repeatable check of the basics that have
each broken this pipeline at least once during development: the fvar
axes matching what params.py declares, every master having the same
glyph set, and every glyph having identical contour/point topology
across all masters (the invariant gvar interpolation, and specifically
the SERF axis, depends on). Run after every build:

    python3 -m tools.designspace_build && python3 -m tools.validate_build
"""

from __future__ import annotations

import pathlib
import sys

import ufoLib2
from fontTools.ttLib import TTFont

from tools import params as P

HERE = pathlib.Path(__file__).resolve().parent.parent
SOURCES_DIR = HERE / "sources"
COMPILED_TTF = HERE / "fonts" / "variable" / "Azrienoch-VF.ttf"


def _fail(msg, errors):
    errors.append(msg)
    print("FAIL:", msg)


def check_fvar(errors):
    font = TTFont(str(COMPILED_TTF))
    axes = {a.axisTag: (a.minValue, a.defaultValue, a.maxValue) for a in font["fvar"].axes}
    expected = {
        "wght": tuple(P.WGHT_AXIS[1:]),
        "wdth": tuple(P.WDTH_AXIS[1:]),
        "SERF": tuple(P.SERF_AXIS[1:]),
    }
    for tag, exp in expected.items():
        got = axes.get(tag)
        if got != exp:
            _fail(f"fvar axis {tag}: expected {exp}, got {got}", errors)
    expected_instances = len(list(P.master_grid()))
    got_instances = len(font["fvar"].instances)
    if got_instances != expected_instances:
        _fail(
            f"fvar named instances: expected {expected_instances} (one per master), "
            f"got {got_instances}",
            errors,
        )
    return font


def check_glyph_sets_match(ufos, errors):
    glyph_sets = {name: set(ufo.keys()) for name, ufo in ufos.items()}
    reference_name, reference_set = next(iter(glyph_sets.items()))
    for name, glyphs in glyph_sets.items():
        if glyphs != reference_set:
            missing = reference_set - glyphs
            extra = glyphs - reference_set
            _fail(
                f"{name}: glyph set differs from {reference_name} "
                f"(missing {len(missing)}, extra {len(extra)})",
                errors,
            )


def check_topology_compatible(ufos, errors):
    reference_name, reference_ufo = next(iter(ufos.items()))
    for gname in reference_ufo.keys():
        ref_shape = [len(c) for c in reference_ufo[gname].contours]
        for name, ufo in ufos.items():
            if gname not in ufo:
                continue  # already reported by check_glyph_sets_match
            shape = [len(c) for c in ufo[gname].contours]
            if shape != ref_shape:
                _fail(
                    f"glyph {gname!r}: contour topology differs between "
                    f"{reference_name} {ref_shape} and {name} {shape}",
                    errors,
                )


def load_ufos():
    ufos = {}
    for wght, wdth, serf in P.master_grid():
        name = P.master_name(wght, wdth, serf)
        path = SOURCES_DIR / f"Azrienoch-{name}.ufo"
        ufos[name] = ufoLib2.Font.open(path)
    return ufos


def main():
    errors: list[str] = []
    ufos = load_ufos()
    print(f"loaded {len(ufos)} UFO masters")

    check_glyph_sets_match(ufos, errors)
    check_topology_compatible(ufos, errors)

    font = check_fvar(errors)
    print(f"compiled font: {font['maxp'].numGlyphs} glyphs")

    if errors:
        print(f"\n{len(errors)} check(s) failed")
        sys.exit(1)
    print("all checks passed")


if __name__ == "__main__":
    main()
