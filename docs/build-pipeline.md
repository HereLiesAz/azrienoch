# Build pipeline

## Repository layout

```
fonts/variable/Azrienoch-VF.ttf   compiled variable font (build output)
sources/*.ufo                     the 48 (wght x wdth x SERF x GRAD) UFO masters (build output)
sources/Azrienoch.designspace     the designspace tying the masters together (build output)
third_party/roboto-flex/          vendored Roboto Flex source font + its own OFL.txt/AUTHORS.txt
tools/                            the build pipeline (below)
specimen/                         specimen renders + the interactive specimen page (index.html)
docs/                             this documentation
```

`sources/*.ufo`, `sources/Azrienoch.designspace` and
`fonts/variable/Azrienoch-VF.ttf` are build output, checked in so the
compiled font is usable without running Python -- regenerate them any
time `tools/` or `third_party/roboto-flex/` changes:

```
pip install -r requirements.txt
python3 -m tools.designspace_build
```

This regenerates the masters, the designspace, and the compiled
variable TTF, and validates the result.

## `tools/`

In roughly build order:

- **`params.py`** -- the axis model: master grid, and the (registered)
  axis definitions. Start here to understand what actually varies.
- **`roboto_source.py`** -- maps an Azrienoch `(wght, wdth, GRAD)` onto
  a point in Roboto Flex's axis space, instances the vendored variable
  font there with `fontTools.varLib.instancer`, and extracts glyph
  outlines, advance widths and kerning.
- **`serifs.py`** -- detects candidate stem feet once from a reference
  instance, then adds the *same* foot contours (by fractional
  position) to every master, sized by that master's own `SERF` value.
  Every master of a glyph gets identical topology this way -- collapsed
  to a hairline at `SERF=0`, grown to a full slab at `SERF=100` --
  which is what makes the axis interpolate at all rather than failing
  to compile. Each foot only grows on the side(s) that border a real
  stem rather than the letter's own counter (checked via the adjacent
  contour segment's length), which is what keeps it from notching into
  arch letters like 'n'/'m'/'p'/'r'/'h'.
- **`quirks.py`** -- the 'G' spur, 'R' leg kick, 'e'/'g's flat
  terminals, 'v'/'w's sharp baseline point, and the 'A'/'e'
  self-intersection fixes (see [`design.md`](./design.md) and
  [`TODO.md`](./TODO.md)).
- **`dots.py`** -- the weight-tapered dot boost and the 'i'/'j' tittle
  reposition-to-ascender-height fix.
- **`single_story_a.py`** -- builds 'a' from 'd's own outline.
- **`round_contrast.py`** -- thins 'o'/'c'/'e' at top and bottom to
  match a bowl's own neck thickness.
- **`arch_symmetry.py`** -- symmetrizes 'n'/'h'/'m'/'u's arch-spring
  heights.
- **`arch_shape.py`** -- rounds 'n'/'h'/'m'/'u's arch counters to match
  'o's own shape.
- **`counter_shape.py`** -- shrinks the flat "waist" on a counter's
  round sides; mostly superseded by `canonical_counter.py` below for
  the glyphs that structurally match, still applied first as a
  harmless no-op/fallback pass.
- **`canonical_counter.py`** -- reshapes 'o'/'d'/'b'/'p'/'q'/'g'/'a's
  inner counters into true affine-scaled copies of 'o's own outer
  contour.
- **`ufo_build.py`** -- assembles the 48 master UFOs, copying each
  glyph's quadratic outline through unmodified (no curve conversion --
  gvar already guarantees the same point topology across masters, so
  nothing needs re-fitting; only `serifs.py`'s added rectangles are
  new points). Composite glyphs (accents, '%') are decomposed against
  Roboto Flex's own glyphset first, so what lands in the UFO is always
  plain contours. Also ports Roboto Flex's `pnum` (proportional
  figures) `GSUB` feature: each digit's alternate proportional-width
  outline (`uniXXXX.prop`) is imported alongside the default tabular
  one, with a `feature pnum { ... }` block substituting between them,
  subject to the same `SERF`-axis feet as its default counterpart.
- **`designspace_build.py`** -- writes the `.designspace` (axes,
  sources, named instances, `STAT` axis-value labels) and runs
  `fontmake` to compile the variable TTF, then runs `validate_build.py`.
- **`validate_build.py`** -- sanity-checks the build: `fvar`
  axes/instances match `params.py`, every master has the same glyph
  set, and every glyph has identical contour/point topology across all
  48 masters. Runnable on its own: `python3 -m tools.validate_build`.
- **`geometry.py`** -- the rectangle-contour primitive `serifs.py`
  builds feet from.
- **`preview.py`** -- a matplotlib-based text renderer (from the
  compiled variable font, at any axis location) used for visual QA
  during development; also runnable directly:
  `python3 -m tools.preview "text" wght wdth SERF GRAD out.png`.
- **`next_version.py`** -- computes the release version; see
  [`versioning.md`](./versioning.md).
- **`update_specimen.py`** -- regenerates `specimen/index.html`'s
  embedded font and preset data from the current build.

Point-editor-style hand tooling (drawing glyphs at explicit weight/
width extremes and extrapolating the rest) is not part of this
pipeline -- Azrienoch's letterforms come from Roboto Flex, transformed
in code. That approach now lives in a separate project,
[Morphont](https://github.com/HereLiesAz/morphont); see
[`docs/README.md`](./README.md#related-tooling).

## Validation

`tools/validate_build.py` runs automatically at the end of
`designspace_build.py`, and gates CI's release workflow (a failed
build or validation never gets released). It checks:

- `fvar` axes and named instances match `params.py`.
- Every master UFO has the same glyph set.
- Every glyph has identical contour/point topology across all 48
  masters (the invariant gvar interpolation depends on).

## Specimen

`specimen/index.html` is a self-contained (font embedded) interactive
specimen: live `wght`/`wdth`/`SERF` sliders, all named-instance
presets, an editable hero sample, and a glyph-set showcase. Open it
directly in a browser -- no server needed. `.github/workflows/pages.yml`
publishes it to GitHub Pages on every change to `specimen/**` on
`master`.
