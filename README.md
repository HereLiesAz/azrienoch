# Azrienoch

A variable font that multiplexes several axes of control into one
typeface: weight, width, grade, and a sans/serif toggle, with cap-height
and x-height themselves tied to the weight axis rather than to point size
or line height.

This repository previously held [Graduate](https://github.com/etunni/Graduate-Variable-Font),
a 12-axis variable font by Eduardo Tunni that served as this project's
model for how far a single variable font's axis system can go. Azrienoch
replaces it: same ambition for axis versatility, a different letterform
foundation and a narrower, more deliberate set of axes.

## Design

Azrienoch's letterforms, spacing and kerning come from
[Roboto Flex](https://github.com/googlefonts/roboto-flex) (SIL OFL 1.1),
not from a from-scratch drawing. Roboto Flex is real, professionally
hinted and kerned type-design engineering, with nine independent
"parametric" axes controlling stroke weight and vertical proportions
separately from its registered `wght`/`wdth` axes. Azrienoch's own work
is in what it does with that space:

- **Height as a matter of weight.** Roboto Flex deliberately keeps
  weight and height independent -- that's the whole point of exposing
  eight parametric axes (`XOPQ`/`YOPQ` stroke weight, `XTRA` counter
  width, `YTUC`/`YTLC`/`YTAS`/`YTDE`/`YTFI` cap/x/ascender/descender/
  figure height) separately from `wght`/`wdth`. Azrienoch deliberately
  does the opposite: its `wght` axis is mapped onto a correlated path
  through that same eight-axis space (see
  `tools/roboto_source.py::_HEIGHT_AXES_AT_WGHT`), so cap-height,
  x-height and stroke weight all grow together. A heavier Azrienoch
  instance is a genuinely *taller* one, independent of the type size or
  line height the reader chooses.
- **A variable serif axis (`SERF`, 0-100).** Roboto Flex has no serifs.
  `tools/serifs.py` scans one reference instance for short, already-flat
  horizontal stem terminals (round strokes never present one, so bowls
  and curves are naturally skipped) and grows a slab foot on each,
  driven by the `SERF` axis. Azrienoch is sans by default.
- **A grade axis (`GRAD`, -50-50) for optical compensation, not
  redesign.** Unlike `wght`, Roboto Flex's `GRAD` changes stroke weight
  without touching advance widths or glyph metrics at all -- it's
  designed to be nudged live (dark text on a light ground can read
  thinner than light text on a dark ground at the same nominal weight)
  without reflowing a single line of text. Azrienoch passes it straight
  through to Roboto Flex's own `GRAD` (see `roboto_source.roboto_location`),
  narrowed to a safer slice of Roboto's full -200..150 range.
- **Automatic, weight/width-aware spacing and kerning.** Advance widths
  and kerning are extracted straight out of Roboto Flex's own `hmtx`
  and (per-master, since it's decompiled from a fully instanced,
  therefore static, `GPOS`) `kern` feature at each of Azrienoch's master
  locations -- see `tools/roboto_source.py::extract_kerning`. That
  inherits Roboto Flex's own tuning: pairs tighten at heavier weights
  and stay legible when condensed, without Azrienoch reimplementing an
  optical-kerning algorithm of its own.
- **A horizontal-terminal design principle.** Roboto Flex's own grotesque
  terminals are already cut flat (horizontal or vertical), not on the
  stroke's own angle -- Azrienoch's slab serifs follow the same rule
  (they're rectangles, by construction), and no reshaping was needed to
  bring the inherited letterforms into line with it.
- **Counters pushed wide at every weight.** Roboto Flex's `XTRA` axis
  controls counter width independently of stroke weight; Azrienoch's
  `wght` mapping deliberately keeps `XTRA` generous even at Black
  (`tools/roboto_source.py::_HEIGHT_AXES_AT_WGHT`), refusing the usual
  trade where the heaviest weight lets its ink crowd the void out. The
  counter is a considered shape, not leftover space.
- **A couple of barely-noticeable Akzidenz-Grotesk quirks.**
  `tools/quirks.py` makes two small, targeted edits on top of the
  imported outline: 'G' gets a proper hanging spur (Roboto Flex's own
  crossbar, extended), and 'R' gets a subtly flared, kicked-out leg,
  instead of a plain conservative one. Both are computed relative to the
  glyph's own local geometry (a multiple of its own bar thickness or leg
  width) so they scale with weight and width instead of needing tuning
  per master, and both only ever move existing points -- never add or
  remove one -- so they don't touch the topology gvar interpolation
  depends on.

The letterform character overall aims for an analytical neo-grotesque:
Roboto Flex's own modern, systematic proportions, read with some of
Helvetica's rational flat-terminal directness.

### Deliberately not axes

Two of Roboto Flex's registered axes are fixed rather than exposed, on
purpose rather than by omission:

- **`opsz` (optical size)** would let letterforms open up at small sizes
  and tighten at large ones -- exactly the kind of size-driven shape
  change "height as a matter of weight, not of font size" (above) exists
  to opt out of. Exposing it would reintroduce, through a side door, the
  coupling between point size and proportions the `wght` axis is built to
  replace. Fixed at Roboto Flex's own default (24).
- **`slnt` (slant)** is fixed at 0 (upright). Roboto Flex's own `slnt`
  axis only reaches -10 degrees at its extreme -- a barely-there lean,
  not a real italic -- and a genuine italic needs redrawn letterforms
  (different 'a'/'e'/'f' constructions, not just a shear), which is out
  of scope here. Azrienoch has no italic.

## Axes

| Axis | Tag | Range | Default |
|---|---|---|---|
| Weight | `wght` | 100-900 | 400 |
| Width | `wdth` | 75-100 | 100 |
| Serif | `SERF` | 0-100 | 0 |
| Grade | `GRAD` | -50-50 | 0 |

## Repository layout

```
fonts/variable/Azrienoch-VF.ttf   compiled variable font (build output)
sources/*.ufo                     the 48 (wght x wdth x SERF x GRAD) UFO masters (build output)
sources/Azrienoch.designspace     the designspace tying the masters together (build output)
third_party/roboto-flex/          vendored Roboto Flex source font + its own OFL.txt/AUTHORS.txt
tools/                            the build pipeline (see below)
specimen/                         specimen renders + the interactive specimen page (index.html)
```

`sources/*.ufo`, `sources/Azrienoch.designspace` and
`fonts/variable/Azrienoch-VF.ttf` are build output, checked in so the
compiled font is usable without running Python -- regenerate them with
the steps below any time `tools/` or `third_party/roboto-flex/` changes.

The vendored Roboto Flex font is itself trimmed from its original
13-axis release: `opsz` and `slnt` are instanced out at their defaults
(`fontTools.varLib.instancer`) and dropped, since Azrienoch never varies
them (see "Deliberately not axes" above) -- this shrinks the vendored
file from ~1.78 MB to ~0.68 MB with no behavior change.

### `tools/`

- `params.py` -- the axis model: master grid, and the (registered) axis
  definitions.
- `roboto_source.py` -- maps an Azrienoch `(wght, wdth, GRAD)` onto a
  point in Roboto Flex's axis space, instances the vendored variable font
  there with `fontTools.varLib.instancer`, and extracts glyph outlines,
  advance widths and kerning.
- `serifs.py` -- detects candidate stem feet once from a reference
  instance, then adds the *same* foot contours (by fractional position)
  to every master, sized by that master's own `SERF` value. Every master
  of a glyph gets identical topology this way -- collapsed to a hairline
  at `SERF=0`, grown to a full slab at `SERF=100` -- which is what makes
  the axis interpolate at all rather than failing to compile. Each foot
  only grows on the side(s) that border a real stem rather than the
  letter's own counter (checked via the adjacent contour segment's
  length), which is what keeps it from notching into arch letters like
  'n'/'m'/'p'/'r'/'h'.
- `quirks.py` -- the 'G' spur and 'R' leg kick (see "Design" above).
- `ufo_build.py` -- assembles the 48 master UFOs, copying each glyph's
  quadratic outline through unmodified (no curve conversion -- gvar
  already guarantees the same point topology across masters, so nothing
  needs re-fitting; only `serifs.py`'s added rectangles are new points).
  Composite glyphs (accents, '%') are decomposed against Roboto Flex's
  own glyphset first, so what lands in the UFO is always plain contours.
  Also ports Roboto Flex's `pnum` (proportional figures) `GSUB` feature:
  each digit's alternate proportional-width outline (`uniXXXX.prop`) is
  imported alongside the default tabular one, with a `feature pnum { ... }`
  block substituting between them, subject to the same `SERF`-axis feet
  as its default counterpart.
- `designspace_build.py` -- writes the `.designspace` (axes, sources,
  named instances, `STAT` axis-value labels) and runs `fontmake` to
  compile the variable TTF, then runs `validate_build.py`.
- `validate_build.py` -- sanity-checks the build: `fvar` axes/instances
  match `params.py`, every master has the same glyph set, and every
  glyph has identical contour/point topology across all 48 masters.
  Runnable on its own: `python3 -m tools.validate_build`.
- `geometry.py` -- the rectangle-contour primitive `serifs.py` builds feet
  from.
- `preview.py` -- a matplotlib-based text renderer (from the compiled
  variable font, at any axis location) used for visual QA during
  development; also runnable directly, `python3 -m tools.preview "text" wght wdth SERF GRAD out.png`.

## Building

```
pip install -r requirements.txt
python3 -m tools.designspace_build
```

This regenerates `sources/*.ufo`, `sources/Azrienoch.designspace` and
`fonts/variable/Azrienoch-VF.ttf`, and validates the result.

## Specimen

`specimen/index.html` is a self-contained (font embedded) interactive
specimen: live `wght`/`wdth`/`SERF` sliders, all named-instance presets,
an editable hero sample, and a glyph-set showcase. Open it directly in a
browser -- no server needed.

## Known limitations

418 glyphs: uppercase, lowercase, digits (default tabular + alternate
proportional via the `pnum` feature), core punctuation, Latin-1
Supplement, Latin Extended-A, Greek and Cyrillic -- not full Unicode
coverage of any of those blocks, no other scripts, and no `GSUB`
features beyond `pnum` and the kerning that is carried over (no
ligatures, no case-sensitive forms). No hinting: TrueType variable-font
hinting is a fundamentally different, largely manual process from
static-font autohinting tools like `ttfautohint` (which don't operate on
`gvar` data at all), and is out of scope here -- modern renderers
(browsers, macOS, most of Linux, and FreeType's autohinter generally)
render an unhinted variable font well; small-size legacy Windows GDI
rendering is the one place this could show. See [TODO.md](./TODO.md) for
the full, itemized list of what's next.

## License

Azrienoch is licensed under the [SIL Open Font License, Version 1.1](./OFL.txt),
as a Modified Version of Roboto Flex. Roboto Flex's own license is in
`third_party/roboto-flex/OFL.txt` and its authors are in
`third_party/roboto-flex/AUTHORS.txt`.
