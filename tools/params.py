"""Axis model for Azrienoch, plus the shared character-set
constants (below) both ufo_build.py and kerning.py need -- kept here,
not in ufo_build.py itself, so kerning.py (which ufo_build.py imports)
can use the same character set without a circular import.

Glyph outlines come from the vendored Jost variable font (see
jost_source.py). This module is the single place that defines the axis
grid Jost gets sampled at, and the vertical metrics the build asserts
(Jost's own cap-height/x-height already happen to be fixed across its
wght range, confirmed against the vendored font directly -- see
README.md -- so no override is needed there).
"""

from __future__ import annotations

import string
import unicodedata

PUNCT = " .,:;!?'\"()-–—/&@#*+=%·[]"
LATIN1 = (
    "ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞß"
    "àáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ"
    "¡¿°µ"
)
LATIN_EXT_A = (
    "ĀāĂăĄąĆćĈĉĊċČčĎďĐđĒēĔĕĖėĘęĚěĜĝĞğĠġĢģĤĥĦħĨĩĪīĬĭĮįİıĲĳĴĵĶķ"
    "ĹĺĻļĽľŁłŃńŅņŇňŌōŎŏŐőŒœŔŕŖŗŘřŚśŜŝŞşŠšŢţŤťŨũŪūŬŭŮůŰűŲųŴŵŶŷŸŹźŻżŽž"
)
# Greek is only what Jost has (four letters, in JOST_EXTRA); Jost is this
# project's only letterform donor.
CYRILLIC = (
    "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
    "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
)
# Every codepoint Jost has that the sets above don't (symbols, currency,
# math, spacing accents, combining marks, Latin Extended-B/Additional,
# four Greek letters, ten Cyrillic letters), so the font covers all of
# Jost's own character set.
JOST_EXTRA = (
    "\u0000\u000D$<>\\^_`{|}~\u00A0\u00A2\u00A3\u00A4\u00A5\u00A6"
    "\u00A7\u00A8\u00A9\u00AA\u00AB\u00AC\u00AD\u00AE\u00AF\u00B1"
    "\u00B2\u00B3\u00B4\u00B6\u00B8\u00B9\u00BA\u00BB\u00BC\u00BD"
    "\u00BE\u00D7\u00F7\u0138\u013F\u0140\u0149\u014A\u014B\u0166"
    "\u0167\u0192\u0212\u0213\u0218\u0219\u021A\u021B\u0237\u02C6"
    "\u02C7\u02D8\u02D9\u02DA\u02DB\u02DC\u02DD\u0300\u0301\u0302"
    "\u0303\u0304\u0306\u0307\u0308\u030A\u030B\u030C\u0312\u0326"
    "\u0327\u0328\u0394\u03A9\u03BC\u03C0\u0400\u0403\u040C\u040D"
    "\u040E\u0450\u0453\u045C\u045D\u045E\u1E80\u1E81\u1E82\u1E83"
    "\u1E84\u1E85\u1E86\u1E87\u1E88\u1E89\u1E9E\u1EF2\u1EF3\u2010"
    "\u2012\u2018\u2019\u201A\u201C\u201D\u201E\u2020\u2021\u2022"
    "\u2026\u2030\u2031\u2039\u203A\u203D\u2044\u2070\u2074\u2075"
    "\u2076\u2077\u2078\u2079\u2080\u2081\u2082\u2083\u2084\u2085"
    "\u2086\u2087\u2088\u2089\u20AC\u20BD\u2122\u2150\u2151\u2152"
    "\u2153\u2154\u2155\u2156\u2157\u2158\u2159\u215A\u215B\u215C"
    "\u215D\u215E\u2202\u2205\u220F\u2211\u2212\u2215\u2219\u221A"
    "\u221E\u222B\u2248\u2260\u2264\u2265\u25CA\uFF10\uFF11\uFF12"
    "\uFF13\uFF14\uFF15\uFF16\uFF17\uFF18\uFF19"
)
JOST_CHARS = (
    string.ascii_uppercase + string.ascii_lowercase + string.digits
    + PUNCT + LATIN1 + LATIN_EXT_A + CYRILLIC + JOST_EXTRA
)

# Latin letters Jost does not carry, composed from Azrienoch's own letters
# (`composites.py`): every precomposed Latin Extended-B / Additional letter
# that decomposes (NFD) to a plain letter plus marks the build can draw,
# the barred letters, and the compatibility digraphs.
_MARKS_DRAWN = {
    0x300, 0x301, 0x302, 0x303, 0x304, 0x306, 0x307, 0x308, 0x309, 0x30A,
    0x30B, 0x30C, 0x30F, 0x311, 0x31B, 0x323, 0x324, 0x325, 0x326, 0x327,
    0x328, 0x32D, 0x32E, 0x330, 0x331,
}


def _composed() -> str:
    out = []
    for cp in list(range(0xC0, 0x250)) + list(range(0x1E00, 0x1F00)):
        c = chr(cp)
        d = unicodedata.normalize("NFD", c)
        if c in JOST_CHARS or len(d) < 2 or not (d[0].isascii() and d[0].isalpha()):
            continue
        if all(ord(m) in _MARKS_DRAWN for m in d[1:]):
            out.append(c)
    return "".join(out)


COMPOSED = _composed()
BARRED = "ƀɃȻȼɆɇɈɉɌɍɎɏƵƶƗɨȽƚǤǥ"
DIGRAPHS = "ǄǅǆǇǈǉǊǋǌǱǲǳ"

# Logic and set-theory symbols (`symbols.py`), stroked from the master's own
# minus-sign weight.
LOGIC = (
    "\u2200\u2203\u2204\u2227\u2228\u22BB\u22BC\u22BD\u2295\u2297"   # forall exists nexists and or xor nand nor oplus otimes
    "\u22A2\u22A3\u22A4\u22A5\u22A8\u22AC\u22AD"                       # turnstiles, top, bottom
    "\u2234\u2235\u2261\u2262"                                           # therefore because equiv nequiv
    "\u2208\u2209\u220B\u220C\u2282\u2283\u2284\u2285\u2286\u2287\u2288\u2289"
    "\u222A\u2229\u2216\u2218"                                           # cup cap setminus compose
    "\u2190\u2192\u2194\u21A6\u21D0\u21D2\u21D4\u27F8\u27F9\u27FA"   # arrows
    "\u25A1\u25C7\u220E"                                                 # box diamond qed
)

NON_JOST = COMPOSED + BARRED + DIGRAPHS + LOGIC
CHARS = JOST_CHARS + NON_JOST

# Lowercase Cyrillic letters confirmed, by direct rendering (not
# assumed from the character's name), to share a plain Latin letter's
# structural class -- same stem/bowl layout, not just a visual
# resemblance in passing:
#   а single-story bowl (a), е identical aperture-cut shape (e), э the
#   same shape mirrored (e), о a pure round bowl (o), с a pure round
#   open form (c), м a three-legged bridge (m), р a bowl-plus-descender
#   (p), у a v-bowl-plus-descender-tail (y), х pure diagonal crossing
#   strokes (x, which grows no feet at all regardless -- see
#   serifs.py's own module docstring on diagonal-only letters).
# Every other Cyrillic lowercase letter (б, в, г, д, ж, з, и, й, к, л,
# н, п, т, ф, ц, ч, ш, щ, ъ, ы, ь, ю, я) was rendered and checked too,
# but has no clean single-Latin-letter structural analog (bridge/ladder
# shapes like н/п already get the right generic treatment from the
# unclassified default -- see `serifs.py::guides_for`'s own docstring
# on the else branch -- rather than a forced, wrong mapping), so they're
# deliberately left out rather than guessed at.
_CYRILLIC_ANALOG = {
    "а": "a", "е": "e", "э": "e", "о": "o", "с": "c",
    "м": "m", "р": "p", "у": "y", "х": "x",
}


def base_letter(ch: str) -> str:
    """The plain Latin letter `ch` is a diacritic variant of, via Unicode
    NFD decomposition (e.g. 'é'/'ē'/'ě' -> 'e', 'Ł' -> 'L' -- stroke-
    through letters don't decompose this way and fall through to
    themselves, same as any character with no accent to strip), or the
    Latin letter a lowercase Cyrillic letter structurally resembles
    (`_CYRILLIC_ANALOG` above, checked first since NFD doesn't relate
    Cyrillic to Latin at all). Used to extend per-letter-class logic
    (`serifs.py`'s guide selection, `quirks.py`'s round-counter
    reshaping) from the original 62 ASCII letters to their accented
    Latin-1/Latin Extended-A counterparts and select Cyrillic ones
    without hardcoding a lookup table for all ~130 accented letters: a
    'ē' should grow serif feet exactly where a plain 'e' does, and its
    counter should get reshaped to match 'o's the same way 'e' does,
    since it's the same base letterform with a mark added, not a
    different design -- and a Cyrillic 'о' should get the same
    treatment as Latin 'o' for the same reason: it's the same round
    bowl shape, not a different design needing its own rule."""
    if ch in _CYRILLIC_ANALOG:
        return _CYRILLIC_ANALOG[ch]
    decomposed = unicodedata.normalize("NFD", ch)
    return decomposed[0] if decomposed else ch


UPM = 1000

# Vertical metrics are fixed across the whole wght range on purpose: a
# heavy and a light line share the same cap-height/x-height/baseline, so
# mixed-weight multi-line layouts (the whole point of this font) align
# without any per-weight size compensation.
#
# These are Jost's own measured values (confirmed directly against the
# vendored font's actual glyph coordinates, not assumed): H's cap is
# exactly 700; o/r/m's x-height is 470 (u's own stem reaches only 460 --
# a ~10-unit letter-to-letter variance Jost's own design already has,
# not something to paper over with a falsely-precise shared constant);
# b/d/l's ascender is 780; g's descender is -230 (q's own is -220 --
# same kind of small per-letter variance, which is why serifs.py reads
# each descender glyph's own lowest point directly rather than using
# this constant to detect anything).
CAP_HEIGHT = 700
X_HEIGHT = 470
ASCENDER = 780
DESCENDER = -230

WGHT_MIN, WGHT_MAX, WGHT_DEFAULT = 100, 900, 400
# `wdth` runs from 0 (Mono: one fixed advance for every glyph, see
# monospace.py) through 75 (Condensed) to 100 (Normal).
WDTH_MIN, WDTH_MAX, WDTH_DEFAULT = 0, 100, 100
WDTH_MONO, WDTH_CONDENSED = 0, 75
MONO_ADVANCE = 620
MONO_MIN_SIDEBEARING = 40
SERF_MIN, SERF_MAX, SERF_DEFAULT = 0, 100, 0  # sans by default
GRAD_MIN, GRAD_MAX, GRAD_DEFAULT = -50, 50, 0  # a modest, safe compensation swing, not an extreme one

AXES = [
    {"tag": "wght", "name": "Weight", "minimum": WGHT_MIN, "default": WGHT_DEFAULT, "maximum": WGHT_MAX},
    {"tag": "wdth", "name": "Width", "minimum": WDTH_MIN, "default": WDTH_DEFAULT, "maximum": WDTH_MAX},
    {"tag": "SERF", "name": "Serif", "minimum": SERF_MIN, "default": SERF_DEFAULT, "maximum": SERF_MAX},
    {"tag": "GRAD", "name": "Grade", "minimum": GRAD_MIN, "default": GRAD_DEFAULT, "maximum": GRAD_MAX},
]

# One master at every grid corner plus the wght midpoint, so the default
# location (400, 100, 0, 0) is itself a real source -- required for a
# well-formed designspace -- and wght gets a bend partway through its
# range rather than a single straight interpolation.
WGHT_SAMPLES = (WGHT_MIN, WGHT_DEFAULT, WGHT_MAX)
WDTH_SAMPLES = (WDTH_MONO, WDTH_CONDENSED, WDTH_MAX)
SERF_SAMPLES = (SERF_MIN, SERF_MAX)
GRAD_SAMPLES = (GRAD_MIN, GRAD_DEFAULT, GRAD_MAX)

MASTER_GRID = [
    (wght, wdth, serf, grad)
    for wght in WGHT_SAMPLES
    for wdth in WDTH_SAMPLES
    for serf in SERF_SAMPLES
    for grad in GRAD_SAMPLES
]
DEFAULT_LOCATION = (WGHT_DEFAULT, WDTH_DEFAULT, SERF_DEFAULT, GRAD_DEFAULT)

# Human-facing names for each axis stop actually sampled as a master
# (WGHT_SAMPLES/WDTH_SAMPLES/SERF_SAMPLES above) -- feeds both the STAT
# table's axis-value labels (so a design app shows a real "Weight"/
# "Width"/"Serif" style picker instead of a raw numeric slider) and the
# fvar named instance generated at every master grid point below. A
# variable font with no named instances still interpolates its full
# range correctly, but most apps' style pickers list only the named
# instances -- with none defined beyond the implicit default, that's
# "Regular" and nothing else, regardless of how many masters the font
# actually has (confirmed: a real early bug -- MASTER_GRID already had
# 12 real masters spanning Thin-to-Black, Normal-to-Condensed,
# Sans-to-Slab, but `designspace_build.py` never turned any of them
# into an `InstanceDescriptor`, so only Regular ever showed up outside
# a raw axis-slider view).
WGHT_NAMES = {WGHT_MIN: "Thin", WGHT_DEFAULT: "Regular", WGHT_MAX: "Black"}
WDTH_NAMES = {WDTH_MAX: "Normal", WDTH_CONDENSED: "Condensed", WDTH_MONO: "Mono"}
SERF_NAMES = {SERF_MIN: "Sans", SERF_MAX: "Slab"}
# The default grade doesn't add a word to the instance name at all (not
# even an elided one -- there's no "Grade0" to elide), only the
# low/high extremes do.
GRAD_NAMES = {GRAD_MIN: "GradeLow", GRAD_DEFAULT: "", GRAD_MAX: "GradeHigh"}


def style_name(wght: int, wdth: int, serf: int, grad: int = GRAD_DEFAULT) -> str:
    return f"Wght{wght}_Wdth{wdth}_Serf{serf}_Grad{grad}"


def instance_style_name(wght: int, wdth: int, serf: int, grad: int = GRAD_DEFAULT) -> str:
    """The public subfamily name for the fvar named instance at this
    master grid point -- e.g. (900, 75, 100, 50) -> 'Condensed Slab
    Black GradeHigh', (400, 100, 0, 0) -> 'Regular'. Width, Serif and
    Grade only appear when they're off their default (Normal/Sans/
    Grade0), same elision rule the STAT table's own axis labels use, so
    the default corner of the grid is still plain 'Regular' rather than
    'Normal Sans Regular Grade0'."""
    parts = []
    if wdth != WDTH_DEFAULT:
        parts.append(WDTH_NAMES[wdth])
    if serf != SERF_DEFAULT:
        parts.append(SERF_NAMES[serf])
    parts.append(WGHT_NAMES[wght])
    if grad != GRAD_DEFAULT:
        parts.append(GRAD_NAMES[grad])
    return " ".join(parts)
