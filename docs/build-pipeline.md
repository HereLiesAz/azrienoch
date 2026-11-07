# Build pipeline

## Repository layout

```
fonts/variable/Azrienoch-VF.ttf   compiled variable font (build output)
fonts/variable/Azrienoch-VF.woff2 same font, WOFF2 container (build output)
sources/drawn/*.morphont.json    hand-drawn Y and y (Thin, Regular, Black), drawn in Morphont
sources/*.ufo                     the 54 (wght x wdth x SERF x GRAD) UFO masters (build output)
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
  bowl/counter shape actually matches 'o's. Horizontal levels (bar
  top/bottom, lower terminal) come from Jost's own 'e' at the same
  axis location; 'c's terminals share them.
- **`drawn_glyphs.py`** -- places the hand-drawn `Y`/`y` from
  `sources/drawn/` at each master (weight blended between the drawn
  weights, `wdth` through `condense.py`), replacing what the steps above
  derived for them. See [`design.md`](./design.md#drawn-glyphs).
- **`composites.py`** -- Latin letters Jost does not have, composed from
  this master's own finished letters: base letter plus combining marks
  (taken from Jost, or derived/drawn where Jost has none), barred
  letters, digraphs. See [`design.md`](./design.md#composed-letters).
- **`strokes.py`** -- centerline-to-outline stroker (lines and cubic
  arcs, mitered corners, one fixed structure per shape) used by the
  hook-above and horn marks and by the symbols.
- **`symbols.py`** -- the logic and set-theory symbols, measured from
  each master's own `=`, minus and `<`. See
  [`design.md`](./design.md#logic-symbols).
- **`non_jost.py`** -- builds everything above for one master, after
  every Jost-derived glyph is final.
- **`monospace.py`** -- fits a Condensed master into the fixed Mono
  cell (`wdth` 0). See [`axes.md`](./axes.md#width-stops).
- **`stroke_balance.py`** -- one perpendicular stroke thickness for
  V/W/M/v/w (and Ŵ/ŵ/Cyrillic М): outer silhouette kept, inner points
  recomputed; 'M''s middle vertex overshoots the baseline to 'V''s own
  vertex depth.
- **`single_story_a.py`** -- builds 'a' from 'd's own outline (single-
  story, not the double-story convention most grotesques inherit from
  print).
- **`quirks.py`** -- terminal-cut reorientation (true horizontal/
  vertical cuts on 's'/'r'/'f'), canonical round-counter
  reshaping (every round counter becomes an affine-scaled copy of
  'o's own), a couple of micro-notch fixes to defects present in
  Jost's own raw outline, and per-letter redraws derived from other
  letters' own outlines: 'S' rotated 180 degrees; 'J' takes 'g's full
  descender curl (and 'g's advance width); 'q' takes 'j's curl mirrored
  (advance unchanged, the hook overhangs the sidebearing); 'y' is a narrowed 'v' (V_NARROW 0.9, arm
  width kept) with 'g's descender curl hung from the V's right terminal
  at x-height (V outer width = curl width, so the y's top-left and bottom-left corners align at every master), and 'Y' is a full-width V (Y_V_NARROW 1.0) with its tip
  at Y_TIP_DEPTH 0.70 of Jost's junction height with a rectangular stem hanging from the V's right
  outer edge Y_ATTACH (0.8) of the way up (arms as thick, perpendicular, as the stem/tail they carry; `hang_y_from_v`,
  `hang_Y_from_V`; advances unchanged); 'Q's tail is re-angled to
  'R's leg slope. Base letters only -- accented variants of J/j/q/y
  keep Jost's own shapes.
- **`accent_marks.py`** -- re-splices Jost's own diacritic marks onto
  this project's own (ring-derived/Arimo-sourced) 'c'/'e'/'s', since
  those base letters no longer carry Jost's own native shape for Jost's
  own accented glyphs to build on.
- **`package_ufo.py`** -- zips `sources/` into `fonts/ufo/` (all 54 masters
  plus the designspace) at the end of every build; the proof page's UFO downloads fetch these from master.
- **`serifs.py`** -- the `SERF` axis: detects candidate stem feet once
  from a reference instance, then adds the *same* foot contours (by
  fractional position, but sized off each master's own actual stem
  width) to every master. Every master of a glyph gets identical
  topology this way -- collapsed to a hairline at `SERF=0`, grown to a
  proportioned slab at `SERF=100` -- which is what makes the axis
  interpolate at all rather than failing to compile. Each foot only
  grows on the side(s) that border a real stem rather than the
  letter's own counter. Policy: serifs grow only from right-angled
  terminals, exactly one per glyph. Uppercase (and b, k): the leftmost
  stem's lower-left corner, flaring left (B D E F H I K L P R T Y ...),
  all at one size taken from that master's `I` stem. Other lowercase
  and digits: the rightmost stem's bottom-right corner, flaring right
  (a d f h i l m n r t u ...). p and q get one serif at the x-height
  top of the stem, flaring outward (p upper-left, q upper-right); T alone flares lower-right. None
  on N Q g j y (M is the one exception: a serif at each foot), on ascender/cap tops, or on diagonal terminals
  (A, X, x, v, w, z, K/R legs). `1` keeps its original both-ways
  baseline foot. `7` gets a `SERF`-driven dash through its diagonal
  (`serifs.apply_seven_dash`). Each foot is anchored at the stem corner
  measured on that master's own outline (`_corner_x`), so it never
  lands on the wrong stem at Thin/Black or condensed masters.
- **`kerning.py`** -- letter-pair kerning extracted from vendored
  Jost's own GPOS pair-positioning table, covering the full character
  set (donor values; used only outside the base letter set).
- **`kern_derive.py`** -- per-master kerning derived from the finished
  outlines of the 62 base letters/digits (optical gap over height,
  closest-approach floor); accented/Cyrillic glyphs inherit their base
  letter's pairs. Parameters and calibration: `docs/design.md` Kerning.
- **`ufo_build.py`** -- assembles the 54 master UFOs: extracts every
  glyph (routing 's' to Arimo, 'c'/'e' to `ring_derived.py`, 'a' to
  `single_story_a.py`, everything else to Jost), applies `quirks.py`'s
  terminal cuts and round-counter reshaping, splices accent marks, then
  applies `serifs.py`'s feet and the kerning (`kern_derive.py`, with
  `kerning.py` filling the rest).
- **`designspace_build.py`** -- writes the `.designspace` (axes,
  sources, named instances, `STAT` axis-value labels), runs `fontmake`
  to compile the variable TTF, wraps it in a WOFF2 container, then runs
  `validate_build.py` and `update_specimen.py`.
- **`validate_build.py`** -- sanity-checks the build: `fvar`
  axes/instances match `params.py`, every master has the same glyph
  set, and every glyph has identical contour/point topology across all
  54 masters. Runnable on its own: `python3 -m tools.validate_build`.
- **`preview.py`** -- a matplotlib-based text renderer (from the
  compiled variable font, at any axis location) used for visual QA
  during development.
- **`export_ufo.py`** -- builds and saves a single UFO master on
  demand, for opening directly in an external point editor, without
  regenerating the whole grid.
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
- Every glyph has identical contour/point topology across all 54
  masters (the invariant gvar interpolation, and specifically the
  `SERF` axis, depends on).

## Specimen

`specimen/index.html` is a self-contained (font embedded) interactive
page with the named instances, the character set across weight and
width, the accented and logic sets, an axis fader (`wght`/`wdth`/`SERF`/
`GRAD` sliders, presets, editable sample text), a kerning comparison, and a
TTF/WOFF2 download control that always fetches the current
`fonts/variable/` build from `master`. Open it directly in a browser --
no server needed. `.github/workflows/pages.yml`
publishes it to GitHub Pages on every change to `specimen/**` on
`master`.
