"""Build Azrienoch's UFO masters + designspace from Roboto Flex.

For each (wght, wdth, SERF, GRAD) master in ``params.master_grid()``: instance
Roboto Flex at the corresponding location (``roboto_source.py``), copy
over ``CORE_CHARS``' outlines/advances/kerning, and apply the 'G'/'R'
quirks (``quirks.py``). Every master -- SERF=0 included -- gets the same
fixed set of foot contours per glyph (``serifs.py``), sized by that
master's own SERF value; that keeps every master of a glyph
topologically identical, which ``fontmake`` requires to interpolate it
at all. ``fontmake`` then compiles the result into one variable TTF.
"""

from __future__ import annotations

import os
import pathlib
import re
import unicodedata

import ufoLib2
from fontTools.pens.recordingPen import DecomposingRecordingPen

from tools import arch_shape as ASH
from tools import arch_symmetry as AS
from tools import canonical_counter as CC
from tools import counter_shape as CS
from tools import dots as D
from tools import params as P
from tools import quirks as Q
from tools import roboto_source as R
from tools import rotation_align as RA
from tools import round_contrast as RC
from tools import serifs as S
from tools import single_story_a as A
from tools import taper_align as TA

ROUND_CONTRAST_CHARS = {"o", "c", "e"}

# Letters an arch spring-pair (a stem meeting a curve) means the same
# thing 'n'/'h'/'m'/'u' does: a real arch counter that should read as
# round as 'o's own. arch_symmetry.py's find_spring_pairs and
# arch_shape.py's reshape_arch_counters are purely structural -- "two
# stems this long, joined by a curve" -- with no idea which letter
# they're looking at, so calling them unconditionally on every glyph (as
# both were, until this was found) also matches letters that happen to
# share that same stem-and-curve skeleton for an unrelated reason:
# capital 'U' (and its accented forms -- 'Ù'/'Ú'/'Û'/'Ü'/'Ū'/... are two
# stems joined by a curve too, just not an arch's), 'r'/'ŕ'/'ŗ'/'ř', and
# several Greek letters unrelated to the arch family entirely (found via
# a before/after diff of the compiled font: Greek 'μ' came out warped by
# tens of thousands of units at Black weight -- an obviously wrong match,
# not a subtle one). Restricting to the letters this was actually
# designed and verified for -- 'h'/'n'/'m'/'u' and their accented Latin
# forms -- via each character's own NFD base letter (falling back to the
# character itself for the one exception, 'ħ', which doesn't decompose)
# is what keeps the two functions' generic geometry from firing on a
# letter that only coincidentally matches their skeleton.
_ARCH_BASE_LETTERS = {"h", "n", "m", "u"}
_ARCH_EXTRA_CHARS = {"ħ"}


def _is_arch_char(ch: str) -> bool:
    base = unicodedata.normalize("NFD", ch)[:1] or ch
    return base in _ARCH_BASE_LETTERS or ch in _ARCH_EXTRA_CHARS


# Same over-matching risk as arch reshaping, for the same reason:
# canonical_counter.py's reshape_counter is also a purely structural
# detector (a 14-point on/off-curve pattern shared by 'o's own contour),
# with no idea which letter it's looking at -- see that module's own
# docstring, which names exactly 'o'/'d'/'b'/'p'/'q'/'g'/'a' as the
# intended, verified family (task that shipped it: "Build canonical-oval
# counter reshape (o/d/b/p/q/g/a)"). Left unconditional, the same way
# arch reshaping was, it also fires on every OTHER letter that happens to
# have a closed counter for an unrelated reason: capital 'O'/'Q', digits
# ('0'), '%', 'Ø'/'þ'/'đ', and a wide swath of Greek and Cyrillic letters
# (ρ/σ/θ, б/р/й/Ю, ...) whose counters were never designed or verified to
# match 'o's own proportions -- found the same way the arch bug was,
# checking which characters this function actually changes something for
# versus the 7 it was built for. None of these came out as badly broken
# as arch reshaping's Greek 'μ' did, but forcing a Cyrillic 'б' or Greek
# 'σ' through 'o's exact oval is still an unintended, undesigned change,
# not a merely-cosmetic side effect worth keeping by accident.
_COUNTER_BASE_LETTERS = {"o", "d", "b", "p", "q", "g", "a"}


def _is_closed_counter_char(ch: str) -> bool:
    base = unicodedata.normalize("NFD", ch)[:1] or ch
    return base in _COUNTER_BASE_LETTERS


# 'o' isn't the only round, roughly-symmetric shape Roboto Flex's own raw
# extraction mishandles across weight the same way -- confirmed directly
# on the compiled font (a signed-area sweep from wght 100 to 900) that
# capital 'O', digit '0', and digits '6'/'9' all momentarily collapse
# through a degenerate sliver in the same wght~130-150 range 'o' itself
# did, and 'D' does too (its bowl has the same double-oval structure as
# 'O's). Confirmed this is specifically a self-correspondence problem,
# not a borrowed-template one: `stabilize_round_glyph`
# (canonical_counter.py) never copies another glyph's shape, only
# realigns each of these against ITS OWN reference-master self, so
# there's no over-matching risk the way `reshape_counter`/
# `reshape_arch_counters` have (see those two functions' own docstrings)
# -- scoped to this specific letter set anyway, rather than applied
# universally, because for a glyph whose weight-dependent shape genuinely
# isn't just a scaled copy of its reference self (most letters), forcing
# it to become one would be a real, unwanted design change, not a bugfix.
# 'o' is IN this set -- its accented forms (ò/ó/ô/õ/ö/ø, ...) are
# independent extractions with their own points, not a reuse of plain
# 'o's, and were confirmed to have this exact same collapse themselves
# (e.g. 'ø' momentarily solid-black around wght 140, same as an
# unfixed 'o' would be). The literal character 'o' is excluded below,
# not here, because that ONE glyph already gets the equivalent fix
# further down in this same loop iteration (its own outer via
# `reshape_outer_to_reference`, its own inner counter via
# `reshape_counter` + the realignment right after it) -- both needed
# earlier than this call runs, since 'o' also serves as everyone else's
# counter-reshaping template. Stabilizing literal 'o' here too would
# just get overwritten by that more specific handling; every OTHER
# glyph whose NFD base is 'o' still needs this call, since none of them
# get that dedicated treatment.
_ROUND_STABILIZE_BASE_LETTERS = {"o", "O", "0", "D"}
# '6'/'9' used to be in this set too: the collapse it exists to prevent
# (see this function's own docstring, and _split_fused_digit_contour's)
# happened in the wght~130-150 range -- unreachable now that
# params.py::WGHT_AXIS's own floor is 180 (see that axis's own comment
# for why). Kept on for '0'/'O'/'D' (real double-contour glyphs Roboto
# Flex itself extracts that way, unaffected by the digit split below),
# but confirmed directly it now does active HARM on '6'/'9' specifically:
# run on the counter contour _split_fused_digit_contour just created,
# `stabilize_round_glyph`'s own affine-fit-and-rotate machinery picks a
# rotation that scrambles that contour's own point order at the Thin
# master (a real, confirmed self-intersection -- not the harmless
# unflattened-control-point false positive a naive check can also
# produce), where the natural, untouched split order was already clean.
# Removing '6'/'9' from this set leaves that split counter exactly as
# `_split_fused_digit_contour` built it -- which needed no further
# stabilizing in the first place, now that the range this fix was for
# is gone.
_DIGIT_ROUND_STABILIZE_EXCLUDE = {"6", "9"}


def _needs_round_stabilization(ch: str) -> bool:
    if ch == "o" or ch in _DIGIT_ROUND_STABILIZE_EXCLUDE:
        return False
    base = unicodedata.normalize("NFD", ch)[:1] or ch
    return base in _ROUND_STABILIZE_BASE_LETTERS


# '6'/'9' are also in `_ROUND_STABILIZE_BASE_LETTERS` above, but unlike
# every other glyph there (0/O/D), Roboto Flex's own raw extraction
# never gives them a separate counter contour -- it fuses the outer
# silhouette and the inner counter into ONE path: outer boundary, a
# two-point "bridge" cutting IN to trace the counter (in the opposite
# winding direction, so nonzero fill still punches a hole), then another
# two-point bridge back OUT to close the outer. Confirmed this single-
# contour fusion is exactly why `stabilize_round_glyph` -- which reshapes
# each contour independently, fit to THAT SAME contour's own current
# bbox (see canonical_counter.py's own docstring) -- can't preserve 6/9's
# actual stroke-to-counter ratio at a given weight the way it correctly
# does for double-contour glyphs: fused into one path, the counter's own
# bbox is dominated by (and barely shrinks independently of) the outer
# silhouette's, so fitting the Regular-weight reference into that
# barely-shrunk bbox reproduces something close to Regular's own,
# comparatively bold proportions at every weight. Measured directly on
# the compiled Thin master: 6/9 came out with nearly Regular's own
# ink-to-bbox ratio (0.398 either way) while 0/O/D -- whose outer and
# inner contours each fit their own independent bbox -- correctly thinned
# to match.
#
# The fix is structural, not a per-master patch: split Roboto Flex's own
# fused path into two independent contours -- an OUTER (silhouette plus
# stem/ascender) and an INNER (the counter, closed on itself) -- once,
# right after extraction, before any of the reference-fit machinery ever
# sees it. Confirmed by direct comparison that this changes nothing about
# the shape itself: filling the split two ways produces the identical
# result the original fused path did at every weight tested (each
# "bridge" pair simply becomes its own new contour's own closing edge
# instead of a literal cut-and-return) -- this only changes how the ink
# is bookkept across contours, never the ink itself. Never adds or
# removes a point, so the topology invariant every other master-building
# step in this file already depends on stays intact -- this only
# reassigns which of the SAME 36 (or 37) point objects belong to which of
# now two contours instead of one.
#
# Point indices found by direct inspection of Roboto Flex's own raw
# extraction (stable across weight and across the tabular/proportional-
# figure variant pair, confirmed on both): (inner_start, outer_start).
# `points[inner_start:outer_start]` is the counter, closed on itself;
# `points[outer_start:] + points[:inner_start]` is everything else,
# closed on itself the same way.
_DIGIT_SPLIT_POINTS = {"6": (13, 26), "9": (7, 20)}


def _split_fused_digit_contour(glyph, ch: str) -> None:
    split = _DIGIT_SPLIT_POINTS.get(ch)
    if split is None or len(glyph.contours) != 1:
        return
    inner_start, outer_start = split
    pts = glyph.contours[0].points
    if len(pts) <= outer_start:
        return  # not the outline shape this was written against
    inner_pts = pts[inner_start:outer_start]
    outer_pts = pts[outer_start:] + pts[:inner_start]
    glyph.contours[0].points = outer_pts
    glyph.contours.append(ufoLib2.objects.Contour(points=inner_pts))


def _is_e_counter_char(ch: str) -> bool:
    """'e' plus every accented form (é/è/ê/ë/ę/ė/ě/...) -- confirmed each
    is an independent extraction sharing 'e's own 32-point base contour
    (as `glyph.contours[0]`, with the accent as a separate contour after
    it) rather than a reuse of plain 'e's points, and confirmed each has
    the identical flat-top counter defect `reshape_named_span` (see
    arch_shape.py) exists to fix -- the same "accented forms need their
    own call, not just the base letter's" lesson as
    `_ROUND_STABILIZE_BASE_LETTERS` above."""
    base = unicodedata.normalize("NFD", ch)[:1] or ch
    return base == "e"


# v/V/w/W's own diagonal strokes -- the letters confirmed (a direct
# edge-edge crossing sweep across the whole weight range) to have a
# self-intersecting outer contour at some of Azrienoch's own actual
# masters. See taper_align.py::stabilize_diagonal_strokes's own
# docstring for the fix (checked-then-conditionally-fixed, never
# unconditional -- most masters, including most of the heaviest
# weights, need nothing done).
_DIAGONAL_STROKE_CHARS = {"v", "V", "w", "W"}


def _diagonal_stroke_candidates(ch, gname, wght, wdth, grad, reference_contours) -> list:
    """This glyph's own outer-contour points at each of Azrienoch's OTHER
    real wght masters (`params.WGHT_MASTERS` -- only six ever get
    built), nearest weight first -- donor shapes for
    `taper_align.stabilize_diagonal_strokes` to borrow from when the
    master actually being built self-intersects. Nearest weight first
    because a donor's own stroke-to-bbox proportions are what actually
    get copied in (a bbox-relative reshape, see that function's own
    docstring): the closer the donor's weight is to the broken master's
    own, the closer its native proportions already are to what that
    master's own correct proportions would have been, which is what
    keeps a fixed-up master from reading heavier/lighter than its own
    neighbors at the same nominal wght -- confirmed this was exactly the
    failure of an earlier version that always borrowed from the fixed
    Regular (400) reference regardless of how far away it was.

    Run through the SAME `align_to_reference` / `align_taper_signs` /
    `apply_quirks` / `round_off_waists` steps the actual target glyph
    already went through before this is ever consulted (everything
    `build_master_ufo`'s own main loop does up to, but not including,
    `stabilize_diagonal_strokes` itself) -- not left raw. Confirmed this
    match matters, not just tidiness: `quirks.py`'s own
    `_sharpen_baseline_notches` measurably moves points in exactly the
    bottom-vertex region this module's whole fix is about, so a donor
    extracted raw is a DIFFERENT shape (in exactly the crossing-prone
    area) than what a neighboring master's own points actually are once
    fully built -- confirmed directly: reshaping strictly from a raw
    donor still left the compiled font self-intersecting across a wide
    band of intermediate (interpolated, not-a-real-master) wght values
    even though every real master's own contour tested clean in
    isolation, because a fixed master's points were then only an affine
    copy of the RAW donor, not of what that donor's OWN real master
    (also carrying its own quirks pass) actually equals -- the two
    differ by exactly quirks' own edit, which is enough to break the
    would-be-simple affine relationship between adjacent masters that
    keeps gvar's own straight-line interpolation between them from ever
    crossing itself."""
    donor_wghts = sorted((w for w in P.WGHT_MASTERS if w != wght), key=lambda w: abs(w - wght))
    candidates = []
    for donor_wght in donor_wghts:
        inst = R.instantiate(donor_wght, wdth, grad)
        glyphset = inst.getGlyphSet()
        hmtx = inst["hmtx"]
        cmap = R.cmap_for(donor_wght, wdth, grad)
        donor_gname = cmap.get(ord(ch))
        if donor_gname is None:
            continue
        donor_glyph = _extract_glyph(donor_gname, glyphset, hmtx, None)
        if gname in reference_contours:
            RA.align_to_reference(donor_glyph, reference_contours[gname])
            TA.align_taper_signs(donor_glyph, reference_contours[gname])
        Q.apply_quirks(ch, donor_glyph)
        CS.round_off_waists(donor_glyph)
        if donor_glyph.contours:
            candidates.append(donor_glyph.contours[0].points)
    return candidates

UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
LOWER = "abcdefghijklmnopqrstuvwxyz"
DIGITS = "0123456789"
PUNCT = " .,:;!?'\"()-–—/&@#*+=%·[]"

# Latin-1 Supplement: Western European accented letters (French, German,
# Spanish, Portuguese, Italian, Scandinavian, ...) plus a few punctuation
# marks (inverted !/?, degree, micro).
LATIN1 = (
    "ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞß"
    "àáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ"
    "¡¿°µ"
)

# Latin Extended-A: Central/Eastern European and Baltic accented letters
# (Polish, Czech, Slovak, Hungarian, Romanian, Turkish, Baltic languages).
LATIN_EXT_A = (
    "ĀāĂăĄąĆćĈĉĊċČčĎďĐđĒēĔĕĖėĘęĚěĜĝĞğĠġĢģĤĥĦħĨĩĪīĬĭĮįİıĲĳĴĵĶķ"
    "ĹĺĻļĽľŁłŃńŅņŇňŌōŎŏŐőŒœŔŕŖŗŘřŚśŜŝŞşŠšŢţŤťŨũŪūŬŭŮůŰűŲųŴŵŶŷŸŹźŻżŽž"
)

# Greek and Coptic: the modern monotonic Greek alphabet, upper- and
# lowercase (including final-form sigma 'ς', distinct from medial 'σ'),
# plus the tonos-accented and dialytika (diaeresis) vowels.
GREEK = (
    "ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ"
    "αβγδεζηθικλμνξοπρστυφχψω"
    "ςΆΈΉΊΌΎΏάέήίόύώΪΫϊϋΐΰ"
)

# Cyrillic: the modern Russian alphabet, upper- and lowercase, including
# 'Ё'/'ё'.
CYRILLIC = (
    "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
    "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
)

CORE_CHARS = UPPER + LOWER + DIGITS + PUNCT + LATIN1 + LATIN_EXT_A + GREEK + CYRILLIC

HERE = pathlib.Path(__file__).resolve().parent.parent
SOURCES_DIR = HERE / "sources"

REFERENCE_WGHT, REFERENCE_WDTH = 400, 100


def _copy_outline(ufo_glyph, tt_glyph, glyphset):
    """Copy a Roboto Flex (TrueType, quadratic) glyph's outline in as-is.

    Composite glyphs (e.g. '%', built from 'zerosuperior' + 'uni2044'
    components) are decomposed against Roboto Flex's *own* full
    glyphset: those component glyphs exist there even though Azrienoch
    doesn't import them as standalone characters, so drawing straight
    into our UFO's pen would leave a dangling component reference to a
    glyph our font doesn't have. ``DecomposingRecordingPen`` resolves
    that first, so what lands in the UFO is always plain contours.

    Otherwise, no curve conversion: the SERF axis (``serifs.py``) only
    ever adds plain rectangle contours alongside the imported outline --
    it never reshapes the outline itself -- so there's no reason to touch
    the quadratic points Roboto Flex's own gvar already guarantees are
    topologically identical across every master. A conversion step
    (cubic or otherwise) risks picking a different point count on
    different masters if it isn't perfectly deterministic, which silently
    breaks interpolation between them.
    """
    rec = DecomposingRecordingPen(glyphset)
    tt_glyph.draw(rec)
    rec.replay(ufo_glyph.getPen())


def _guides(cap_height, x_height, ascender, descender):
    return {
        "baseline": 0.0,
        "xheight": x_height,
        "capheight": cap_height,
        "ascender": ascender,
        "descender": descender,
    }


COPYRIGHT = (
    "Copyright 2011 The Roboto Flex Project Authors "
    "(https://github.com/googlefonts/roboto-flex). "
    "Copyright 2026 The Azrienoch Project Authors."
)
LICENSE = (
    "This Font Software is licensed under the SIL Open Font License, "
    "Version 1.1. This license is available with a FAQ at: "
    "http://scripts.sil.org/OFL"
)
LICENSE_URL = "http://scripts.sil.org/OFL"

_VERSION_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)")


def _current_version() -> tuple[int, int, int]:
    """The MAJOR/MINOR/PATCH this build embeds -- `AZRIENOCH_VERSION`
    (the release workflow sets this to what `tools/next_version.py`
    computed) takes precedence, so a released build's binary matches its
    release tag exactly; otherwise falls back to the `VERSION` file
    as-is, for a local dev build outside CI. See `tools/next_version.py`
    for how a release's own version is decided; this only reads it."""
    raw = os.environ.get("AZRIENOCH_VERSION")
    if not raw:
        version_file = HERE / "VERSION"
        raw = version_file.read_text().strip() if version_file.exists() else "0.0.0"
    m = _VERSION_RE.fullmatch(raw.strip())
    if not m:
        raise ValueError(f"not a MAJOR.MINOR.PATCH version: {raw!r}")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def _font_info(ufo: ufoLib2.Font, inst, wght, wdth, serf, grad):
    os2 = inst["OS/2"]
    hhea = inst["hhea"]
    fi = ufo.info
    fi.unitsPerEm = R.UPM
    fi.ascender = hhea.ascender
    fi.descender = hhea.descender
    fi.capHeight = os2.sCapHeight
    fi.xHeight = os2.sxHeight
    fi.familyName = "Azrienoch"
    fi.styleName = P.master_name(wght, wdth, serf, grad)
    # `head.fontRevision` (what versionMajor/versionMinor become) is only
    # Major.Minor, a single fixed-point number -- there's no third field
    # for PATCH, so it's folded into the fraction as MINOR*100+PATCH
    # (fine as long as MINOR stays a single digit, true for the
    # foreseeable future). `openTypeNameVersion` carries the real
    # MAJOR.MINOR.PATCH string, unambiguous, in the name table -- see
    # `next_version.py` for how a release's version is decided.
    major, minor, patch = _current_version()
    fi.versionMajor, fi.versionMinor = major, minor * 100 + patch
    fi.openTypeNameVersion = f"Version {major}.{minor}.{patch}"
    # A distributed .ttf carries its own copyright/license -- OFL clause 2
    # requires each copy to include the license, and a copy of the raw
    # binary distributed apart from this repo's OFL.txt would otherwise
    # have nothing machine-readable to point to.
    fi.copyright = COPYRIGHT
    fi.openTypeNameLicense = LICENSE
    fi.openTypeNameLicenseURL = LICENSE_URL
    return fi


def _extract_glyph(gname, glyphset, hmtx, unicode_val):
    glyph = ufoLib2.objects.Glyph(name=gname)
    _copy_outline(glyph, glyphset[gname], glyphset)
    glyph.width = hmtx[gname][0]
    if unicode_val is not None:
        glyph.unicodes = [unicode_val]
    return glyph


def _prop_glyph_name(gname: str, glyphset) -> str | None:
    """Roboto Flex's alternate proportional-figure glyph for a digit, if any."""
    prop = gname + ".prop"
    return prop if prop in glyphset else None


def _extract_char_glyph(ch, gname, glyphset, hmtx, cmap, xheight):
    """The base outline for character `ch` (named `gname`), before
    quirks/dots/feet. Every character reuses Roboto Flex's own glyph
    unmodified except 'a' -- see single_story_a.py."""
    if ch == "a":
        d_gname = cmap.get(ord("d"))
        if d_gname is not None:
            d_glyph = _extract_glyph(d_gname, glyphset, hmtx, None)
            return A.build_from_d(d_glyph, xheight)
    return _extract_glyph(gname, glyphset, hmtx, ord(ch))


def compute_reference_specs() -> tuple[dict[str, list[dict]], dict[str, list[int]], dict[str, list]]:
    """Foot specs (``serifs.py``) and dot-contour indices (``dots.py``) per
    glyph name, both detected once from the (400, 100) instance and
    reapplied identically on every master -- see those modules'
    docstrings for why detecting once and reusing by index/fraction,
    rather than redetecting per master, is what keeps every master of a
    glyph topologically identical.

    Also captures each glyph's own RAW (pre-quirks, pre-everything)
    contours at this same reference instance, for ``rotation_align.py``
    to align every other master's own raw extraction against -- see that
    module's docstring for why a symmetric glyph like 'o' needs this and
    an asymmetric one like 'n' doesn't."""
    inst = R.instantiate(REFERENCE_WGHT, REFERENCE_WDTH)
    glyphset = inst.getGlyphSet()
    hmtx = inst["hmtx"]
    cmap = R.cmap_for(REFERENCE_WGHT, REFERENCE_WDTH)
    os2, hhea = inst["OS/2"], inst["hhea"]
    guides = _guides(os2.sCapHeight, os2.sxHeight, hhea.ascender, hhea.descender)

    o_gname = cmap.get(ord("o"))
    template_contour = None
    if o_gname is not None:
        o_glyph_raw = _extract_glyph(o_gname, glyphset, hmtx, None)
        if o_glyph_raw.contours:
            template_contour = CC.outer_contour(o_glyph_raw.contours)

    feet_by_glyph = {}
    dots_by_glyph = {}
    reference_contours = {}
    for ch in CORE_CHARS:
        gname = cmap.get(ord(ch))
        if gname is None or gname in feet_by_glyph:
            continue
        glyph = _extract_char_glyph(ch, gname, glyphset, hmtx, cmap, guides["xheight"])
        _split_fused_digit_contour(glyph, ch)
        reference_contours[gname] = RA.snapshot(glyph)
        Q.apply_quirks(ch, glyph)
        CS.round_off_waists(glyph)
        if _is_arch_char(ch):
            AS.symmetrize(glyph)
            ASH.reshape_arch_counters(glyph, template_contour)
        if _is_e_counter_char(ch):
            ASH.reshape_named_span(glyph, template_contour, 16, 23, "line", "line")
        if ch in ROUND_CONTRAST_CHARS:
            RC.thin_round(glyph)
        if _is_closed_counter_char(ch):
            CC.reshape_counter(glyph, template_contour)
            RA.align_to_reference(glyph, reference_contours[gname])
        feet_by_glyph[gname] = S.detect_feet(glyph, guides)
        dots_by_glyph[gname] = D.detect_dot_contours(glyph)

        prop_name = _prop_glyph_name(gname, glyphset)
        if prop_name is not None and prop_name not in feet_by_glyph:
            prop_glyph = _extract_glyph(prop_name, glyphset, hmtx, None)
            _split_fused_digit_contour(prop_glyph, ch)
            reference_contours[prop_name] = RA.snapshot(prop_glyph)
            feet_by_glyph[prop_name] = S.detect_feet(prop_glyph, guides)
            dots_by_glyph[prop_name] = D.detect_dot_contours(prop_glyph)
    return feet_by_glyph, dots_by_glyph, reference_contours


def build_master_ufo(wght, wdth, serf, grad, feet_by_glyph, dots_by_glyph, reference_contours) -> ufoLib2.Font:
    inst = R.instantiate(wght, wdth, grad)
    glyphset = inst.getGlyphSet()
    hmtx = inst["hmtx"]
    cmap = R.cmap_for(wght, wdth, grad)

    ufo = ufoLib2.Font()
    _font_info(ufo, inst, wght, wdth, serf, grad)
    guides = _guides(ufo.info.capHeight, ufo.info.xHeight, ufo.info.ascender, ufo.info.descender)
    dot_factor = D.boost_factor_for_wght(wght)

    # The true height ascender letters (h/d/b/k/l) actually reach -- not
    # `guides["ascender"]` (`hhea.ascender`), which is line-spacing
    # padding, well above any real glyph -- measured off 'h' itself so
    # `reposition_tittle` can align 'i'/'j' to it (see dots.py).
    h_gname = cmap.get(ord("h"))
    ascender_height = None
    if h_gname is not None:
        h_glyph = _extract_glyph(h_gname, glyphset, hmtx, None)
        ascender_height = max(p.y for c in h_glyph.contours for p in c.points)

    # 'o's own outer contour is the reference "genuinely round" shape
    # every other counter gets reshaped to match -- see
    # canonical_counter.py. Extracted fresh per master, then reshaped
    # into an affine-scaled copy of the SAME fixed reference-master
    # outer used everywhere else in this pipeline (reference_contours):
    # Roboto Flex's own raw extraction doesn't keep 'o's outer contour's
    # corner/waist point roles consistent across weight (confirmed: even
    # rotation_align.py's own rotation-based fix can't fully reconcile
    # wght=100's raw points against the reference, since the mismatch
    # isn't a rotation/reversal of the same roles, the roles themselves
    # differ), so leaving this contour as a fresh, un-reshaped per-master
    # extraction would carry that inconsistency into every closed
    # counter that templates off of it -- see
    # canonical_counter.py::reshape_outer_to_reference's own docstring.
    o_gname = cmap.get(ord("o"))
    template_contour = None
    ref_outer_pts = None
    if o_gname is not None:
        o_glyph_raw = _extract_glyph(o_gname, glyphset, hmtx, None)
        if o_gname in reference_contours:
            RA.align_to_reference(o_glyph_raw, reference_contours[o_gname])
            ref_outer_pts = max(reference_contours[o_gname], key=RA._bbox_area)
            CC.reshape_outer_to_reference(o_glyph_raw, ref_outer_pts)
        if o_glyph_raw.contours:
            template_contour = CC.outer_contour(o_glyph_raw.contours)

    imported_names = set()

    notdef = _extract_glyph(".notdef", glyphset, hmtx, None)
    ufo[".notdef"] = notdef
    imported_names.add(".notdef")

    prop_subs: dict[str, str] = {}
    for ch in CORE_CHARS:
        gname = cmap.get(ord(ch))
        if gname is None:
            continue
        glyph = _extract_char_glyph(ch, gname, glyphset, hmtx, cmap, guides["xheight"])
        _split_fused_digit_contour(glyph, ch)
        if gname in reference_contours:
            RA.align_to_reference(glyph, reference_contours[gname])
            TA.align_taper_signs(glyph, reference_contours[gname])
            if _needs_round_stabilization(ch):
                CC.stabilize_round_glyph(glyph, reference_contours[gname])
        Q.apply_quirks(ch, glyph)
        CS.round_off_waists(glyph)
        if ch in _DIAGONAL_STROKE_CHARS and gname in reference_contours:
            candidates = _diagonal_stroke_candidates(ch, gname, wght, wdth, grad, reference_contours)
            TA.stabilize_diagonal_strokes(glyph, candidates)
        if _is_arch_char(ch):
            AS.symmetrize(glyph)
            ASH.reshape_arch_counters(glyph, template_contour)
        if _is_e_counter_char(ch):
            # 'e's upper counter has the identical Roboto-Flex-flattens-
            # the-curve problem the arch letters have, for the identical
            # reason -- see arch_shape.py's own module docstring for why
            # this goes through `reshape_named_span` with hardcoded
            # indices instead of `reshape_arch_counters`'s structural
            # spring-pair search.
            ASH.reshape_named_span(glyph, template_contour, 16, 23, "line", "line")
        if ch in ROUND_CONTRAST_CHARS:
            RC.thin_round(glyph)
        if ch == "o" and ref_outer_pts is not None:
            # 'o's own OUTPUT glyph is a separate extraction from
            # `o_glyph_raw` above (which exists purely to serve as
            # everyone else's template) -- fixing that template's own
            # outer contour doesn't touch this one. Reshape THIS glyph's
            # outer the same way, against the same fixed reference, or
            # 'o' itself keeps momentarily collapsing through a
            # degenerate sliver around wght 135 even though every letter
            # that templates off of it no longer does. See
            # canonical_counter.py::reshape_outer_to_reference.
            CC.reshape_outer_to_reference(glyph, ref_outer_pts)
        if _is_closed_counter_char(ch):
            CC.reshape_counter(glyph, template_contour)
            # `reshape_counter` copies the counter's own points fresh from
            # 'o's own outer contour (see canonical_counter.py), found by
            # matching each point's on/off-curve TYPE independently at
            # every master -- a search that's blind to which of several
            # type-valid readings is the geometrically-right one whenever
            # 'o's own raw extraction (a Roboto Flex quirk, not something
            # under Azrienoch's control) doesn't keep the same corner/waist
            # role at the same point index across weight. Confirmed on 'g'
            # and 'p': that per-master-independent search picked a
            # genuinely different correspondence at wght=100 than at every
            # other master, and gvar naively lerping between two
            # differently-labeled point orders collapsed the counter to
            # under 1% of its own area partway through -- exactly the
            # species of bug `align_to_reference` exists to fix, just
            # freshly reintroduced by this reshape. Re-running it here,
            # against this same glyph's own (already-proven-consistent,
            # confirmed directly) reference layout, re-normalizes whatever
            # rotation the reshape happened to land on back to the one
            # every other master uses.
            RA.align_to_reference(glyph, reference_contours[gname])
        D.boost_dots(glyph, dots_by_glyph.get(gname, []), dot_factor)
        if ch in D.TITTLE_CHARS and ascender_height is not None:
            D.reposition_tittle(glyph, dots_by_glyph.get(gname, []), ascender_height)
        S.apply_feet(glyph, feet_by_glyph.get(gname, []), guides, serf)
        ufo[gname] = glyph
        imported_names.add(gname)

        prop_name = _prop_glyph_name(gname, glyphset)
        if prop_name is not None:
            prop_glyph = _extract_glyph(prop_name, glyphset, hmtx, None)
            _split_fused_digit_contour(prop_glyph, ch)
            if prop_name in reference_contours:
                RA.align_to_reference(prop_glyph, reference_contours[prop_name])
            Q.apply_quirks(ch, prop_glyph)
            D.boost_dots(prop_glyph, dots_by_glyph.get(prop_name, []), dot_factor)
            S.apply_feet(prop_glyph, feet_by_glyph.get(prop_name, []), guides, serf)
            ufo[prop_name] = prop_glyph
            imported_names.add(prop_name)
            prop_subs[gname] = prop_name

    if prop_subs:
        # Roboto Flex's own `pnum` (proportional figures) GSUB feature:
        # default figures are tabular (fixed-width, for columns of numbers),
        # this substitutes in Roboto Flex's alternate proportional-width
        # digit outlines when the feature is enabled.
        subs = "\n".join(f"    sub {a} by {b};" for a, b in sorted(prop_subs.items()))
        ufo.features.text = f"feature pnum {{\n{subs}\n}} pnum;\n"

    raw_kerning = R.extract_kerning(inst)

    # 'a' is now built from 'd's own outline (single_story_a.py) -- its
    # left edge (the bowl) and right edge (the stem, up to x-height) are
    # geometrically identical to 'd's, so its kerning should be too.
    # Roboto Flex's own pairs for 'a' were tuned for the old double-story
    # shape; overwrite them with 'd's pairs in both positions rather than
    # keep pairs tuned for a shape 'a' no longer has.
    a_gname, d_gname = cmap.get(ord("a")), cmap.get(ord("d"))
    if a_gname is not None and d_gname is not None:
        for (left, right), value in list(raw_kerning.items()):
            if left == d_gname:
                raw_kerning[(a_gname, right)] = value
            if right == d_gname:
                raw_kerning[(left, a_gname)] = value
        if (d_gname, d_gname) in raw_kerning:
            raw_kerning[(a_gname, a_gname)] = raw_kerning[(d_gname, d_gname)]

    kerning = {
        pair: value
        for pair, value in raw_kerning.items()
        if pair[0] in imported_names and pair[1] in imported_names
    }
    ufo.kerning.update(kerning)

    return ufo


def build_all():
    SOURCES_DIR.mkdir(exist_ok=True)
    feet_by_glyph, dots_by_glyph, reference_contours = compute_reference_specs()
    paths = {}
    for wght, wdth, serf, grad in P.master_grid():
        ufo = build_master_ufo(wght, wdth, serf, grad, feet_by_glyph, dots_by_glyph, reference_contours)
        name = P.master_name(wght, wdth, serf, grad)
        path = SOURCES_DIR / f"Azrienoch-{name}.ufo"
        ufo.save(path, overwrite=True)
        paths[(wght, wdth, serf, grad)] = path
        print("wrote", path, "glyphs:", len(ufo), "kerning pairs:", len(ufo.kerning))
    return paths


if __name__ == "__main__":
    build_all()
