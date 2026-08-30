# TODO

Tracked follow-up work for Azrienoch, beyond what's in this repository.
Checked items are done; everything else is open. See `README.md` for the
design rationale these build on.

## Glyph coverage

- [x] ~~Grow `tools/ufo_build.py::CORE_CHARS` past the Core Latin MVP~~
      -- done: uppercase, lowercase, digits, core punctuation, Latin-1
      Supplement and Latin Extended-A (273 glyphs total). Composite
      glyphs (accents, `%`) decompose cleanly against Roboto Flex's own
      glyphset via `_copy_outline`'s `DecomposingRecordingPen`.
- [ ] Numeral sets: Roboto Flex ships one alternate figure style
      (proportional, glyph suffix `.prop`) behind its `pnum` GSUB feature,
      which Azrienoch doesn't import (see "No `GSUB` table" below) -- only
      the default figures come across today.
- [ ] Greek and Cyrillic: Roboto Flex covers both; Azrienoch currently
      only imports Latin.

## Axis space

- [x] ~~A fourth `wght` sample~~ -- done: added 700 (Bold) to
      `tools/roboto_source.py::_HEIGHT_AXES_AT_WGHT`, front-loading height
      growth (most of it by Bold, tapering toward Black) while stroke
      thickness keeps growing roughly proportionally, so the curve
      actually bends there instead of being two straight segments.
- [ ] Consider exposing `GRAD` (grade) as a real Azrienoch axis --
      Roboto Flex supports it natively and it's a natural fit alongside
      `wght`/`wdth`/`SERF`; currently fixed at 0 in `roboto_location()`.
- [ ] Consider an `opsz` (optical size) axis, currently fixed at 24 in
      `roboto_location()`.
- [ ] `slnt` (slant/italic) is fixed at 0 -- Azrienoch has no italic.
      Worth a design decision on whether it ever should.
- [ ] Re-derive the `SERF` foot-sizing formulas
      (`tools/serifs.py::apply_feet`) once real serif specimens have been
      eyeballed at more than a handful of weights -- the 0.9/0.42
      multipliers are a first pass, not measured. (The correctness bug
      here -- feet widening symmetrically into the counter on arch
      letters -- is fixed; what's left is tuning.)
- [ ] The `XTRA` (counter width) values in `_HEIGHT_AXES_AT_WGHT` (420 /
      540 / 565 / 580 across the four `wght` samples) are a deliberate
      design choice -- generous at every weight, most pointedly at Black
      -- but a first pass by eye, not measured against real specimens at
      length.

## Font engineering completeness

- [x] ~~No named instances in `fvar`~~ -- done: 16 named instances (one
      per master) via `tools/designspace_build.py::write_designspace`,
      plus `STAT` axis-value labels (`WGHT_LABELS`/`WDTH_LABELS`/
      `SERF_LABELS`) so design apps show a proper style picker instead of
      raw sliders.
- [ ] **No `GSUB` table** -- confirmed no ligatures, case-sensitive
      punctuation, or figure-style features carried over from Roboto
      Flex, since only kerning (`GPOS`) is extracted today
      (`tools/roboto_source.py::extract_kerning`). Decide which of Roboto
      Flex's features are worth porting.
- [ ] **No hinting.** Fine for modern renderers (browsers, macOS, most of
      Linux); worth a pass if Windows GDI/small-size legacy rendering
      matters for this project.
- [x] ~~Review the auto-generated `STAT` table's axis value records~~ --
      done as part of the named-instances work above: 7 axis-value
      records (3 `wght`, 2 `wdth`, 2 `SERF`), each weight/width/serif
      value labeled and the defaults marked elidable.
- [x] ~~Investigate why raw (pre-filter) kerning pair counts from
      `extract_kerning` vary so much with `wdth` at `wght=100`~~ --
      resolved, not a bug. Sampling intermediate widths shows the
      "vanishing" pairs decrease smoothly and monotonically to exactly
      zero as `wdth` approaches normal (e.g. one pair: 19 -> 15 -> 11 ->
      7 -> 4 -> 0 across wdth 75 -> 100), the signature of correctly
      interpolated data, not a discontinuity. Reproducing the same
      comparison with Roboto Flex's own default parametric axes (instead
      of Azrienoch's thin-weight correlation) at `wght=100` gives
      identical counts either way, so it isn't caused by anything
      Azrienoch adds -- it's Roboto Flex's authentic Thin master having
      several thousand extra, tiny (mostly single-digit-unit) kerning
      corrections that exist only at condensed widths and taper to zero
      at normal width, which makes sense: thinner strokes need more
      micro-adjustment to avoid collisions when condensed.
- [x] ~~SERF axis notches the counter on 'n'/'m'/'p'/'r'/'h'~~ -- fixed:
      `tools/serifs.py::_flat_runs` now checks, for each end of a
      candidate flat run, whether the adjacent contour segment is a long
      straight line (a real stem, safe to grow a foot into) or a short
      run into a curve (the counter side, left alone); `apply_feet` only
      grows a foot on the extendable side(s).
- [x] ~~Compiled TTF carries no copyright/license metadata~~ -- fixed:
      `tools/ufo_build.py::_font_info` sets `copyright`/
      `openTypeNameLicense`/`openTypeNameLicenseURL`, verified present in
      the compiled font's `name` table (IDs 0/13/14).

## Tooling / process

- [x] ~~A repeatable check (script or CI) that asserts the compiled
      font's basics after every build~~ -- done:
      `tools/validate_build.py` checks `fvar` axes/instances against
      `params.py`, matching glyph sets across all masters, and
      contour-count topology compatibility across all masters. Runs
      automatically at the end of `tools/designspace_build.py`.
- [ ] Install the compiled `fonts/variable/Azrienoch-VF.ttf` in a real OS
      / browser / design app and spot-check rendering -- everything so
      far has been verified by instancing + rendering in Python
      (`tools/preview.py`), not through a real font-rendering stack.
- [ ] Consider trimming the vendored
      `third_party/roboto-flex/RobotoFlex[...].ttf` (currently the full
      13-axis, ~1.8MB source) if repo size becomes a concern -- e.g. via
      `fonttools varLib.instancer` to drop axes Azrienoch never uses
      (`GRAD`, `opsz`, `slnt`) before vendoring, once those are settled
      as permanently fixed rather than candidates for exposure above.

## Presentation

- [x] ~~A specimen page~~ -- done: `specimen/index.html`, a
      self-contained (font embedded as a data URI) interactive specimen
      with live `wght`/`wdth`/`SERF` sliders using
      `font-variation-settings`, all 16 named-instance presets, an
      editable hero sample, and a glyph-set showcase.
