# Build pipeline

## Repository layout

```
fonts/variable/Azrienoch-VF.ttf   compiled variable font (build output)
fonts/variable/Azrienoch-VF.woff2 same font, WOFF2 container (build output)
sources/*.ufo                     the 36 (wght x wdth x SERF x GRAD) UFO masters (build output)
sources/Azrienoch.designspace     the designspace tying the masters together (build output)
third_party/jost/                 vendored Jost source font + its own OFL.txt
third_party/arimo/                vendored Arimo Regular/Bold + its own OFL.txt
tools/                            the build pipeline (below)
specimen/                         the interactive specimen page (index.html)
docs/                             this documentation
```

`sources/*.ufo`, `sources/Azrienoch.designspace` and
`fonts/variable/Azrienoch-VF.{ttf,woff2}` are build output, checked in
so the compiled font is usable without running Python -- regenerate
them any time `tools/` or `third_party/` changes:

```
pip install -r requirements.txt
python3 -m tools.designspace_build
```

This regenerates the masters, the designspace, the compiled variable
TTF and its WOFF2, validates the result, and re-embeds the font into
`specimen/index.html`.

## `tools/`

In roughly build order:

- **`params.py`** -- the axis model: master grid, axis definitions, and
  the shared character-set constants `ufo_build.py`/`kerning.py` both
  need. Start here to understand what actually varies.
- **`jost_source.py`** -- extracts glyph outlines from the vendored
  Jost variable font at a given `(wght, wdth, grad)`: instances Jost at
  the requested `wght` (`grad` approximated by sampling a nearby `wght`
  for shape while keeping the requested `wght`'s own advance width --
  Jost has no native `GRAD` axis to sample directly), then runs
  `condense.py`'s per-x compression for `wdth != 100`.
- **`condense.py`** -- the `wdth` axis: an ink-density weighted
  horizontal compression (not a flat scale, and not a true optically
  condensed redraw -- no counter is actually reshaped; see
  [`design.md`](./design.md)).
- **`arimo_source.py`** -- extracts 's' from vendored Arimo (an open,
  metric-compatible Helvetica/Arial workalike), interpolated/
  extrapolated along Jost's own weight curve rather than Arimo's own.
- **`ring_derived.py`** -- builds 'c'/'e' directly from that master's
  own 'o' (a cut-open ring plus a crossbar for 'e'), guaranteeing their
  bowl/counter shape actually matches 'o's.
- **`single_story_a.py`** -- builds 'a' from 'd's own outline (single-
  story, not the double-story convention most grotesques inherit from
  print).
- **`quirks.py`** -- terminal-cut reorientation (true horizontal/
  vertical cuts on 'c'/'e'/'s'/'r'/'f'), canonical round-counter
  reshaping (every round counter becomes an affine-scaled copy of
  'o's own), and a couple of micro-notch fixes to defects present in
  Jost's own raw outline.
- **`accent_marks.py`** -- re-splices Jost's own diacritic marks onto
  this project's own (ring-derived/Arimo-sourced) 'c'/'e'/'s', since
  those base letters no longer carry Jost's own native shape for Jost's
  own accented glyphs to build on.
- **`serifs.py`** -- the `SERF` axis: detects candidate stem feet once
  from a reference instance, then adds the *same* foot contours (by
  fractional position, but sized off each master's own actual stem
  width) to every master. Every master of a glyph gets identical
  topology this way -- collapsed to a hairline at `SERF=0`, grown to a
  proportioned slab at `SERF=100` -- which is what makes the axis
  interpolate at all rather than failing to compile. Each foot only
  grows on the side(s) that border a real stem rather than the
  letter's own counter, and per-letter-class rules (single-story
  letters get exactly two feet, an ascender letter's foot lands only at
  the baseline, etc.) follow the shape of handwriting rather than
  "widen wherever there's room."
- **`kerning.py`** -- letter-pair kerning extracted from vendored
  Jost's own GPOS pair-positioning table, covering the full character
  set.
- **`ufo_build.py`** -- assembles the 36 master UFOs: extracts every
  glyph (routing 's' to Arimo, 'c'/'e' to `ring_derived.py`, 'a' to
  `single_story_a.py`, everything else to Jost), applies `quirks.py`'s
  terminal cuts and round-counter reshaping, splices accent marks, then
  applies `serifs.py`'s feet and `kerning.py`'s pairs.
- **`designspace_build.py`** -- writes the `.designspace` (axes,
  sources, named instances, `STAT` axis-value labels), runs `fontmake`
  to compile the variable TTF, wraps it in a WOFF2 container, then runs
  `validate_build.py` and `update_specimen.py`.
- **`validate_build.py`** -- sanity-checks the build: `fvar`
  axes/instances match `params.py`, every master has the same glyph
  set, and every glyph has identical contour/point topology across all
  36 masters. Runnable on its own: `python3 -m tools.validate_build`.
- **`preview.py`** -- a matplotlib-based text renderer (from the
  compiled variable font, at any axis location) used for visual QA
  during development.
- **`export_ufo.py`** -- builds and saves a single UFO master on
  demand, for opening directly in an external point editor, without
  regenerating the whole grid.
- **`point_editor_server.py`** + **`point_editor.html`** -- a local,
  drag-the-points glyph editor that reads and writes UFO master sources
  directly. A hand-editing/demonstration tool for working out what a
  shape should be, not a replacement for the generative `quirks.py`
  pipeline -- a rebuild overwrites any hand edit not also encoded as a
  real rule in `quirks.py`.
- **`next_version.py`** -- computes the release version; see
  [`versioning.md`](./versioning.md).
- **`update_specimen.py`** -- re-embeds the current compiled font into
  `specimen/index.html`.

## Validation

`tools/validate_build.py` runs automatically at the end of
`designspace_build.py`, and gates CI's release workflow (a failed
build or validation never gets released). It checks:

- `fvar` axes and named instances match `params.py`.
- Every master UFO has the same glyph set.
- Every glyph has identical contour/point topology across all 36
  masters (the invariant gvar interpolation, and specifically the
  `SERF` axis, depends on).

## Specimen

`specimen/index.html` is a self-contained (font embedded) interactive
specimen: live `wght`/`wdth`/`SERF`/`GRAD` sliders, all named-instance
presets, an editable hero sample, and a glyph-set showcase. Open it
directly in a browser -- no server needed. `.github/workflows/pages.yml`
publishes it to GitHub Pages on every change to `specimen/**` on
`master`.
