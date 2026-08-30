# TODO

Tracked follow-up work for Azrienoch, beyond the MVP in this repository.
Checked items are done; everything else is open. See `README.md` for the
design rationale these build on.

## Glyph coverage

- [ ] Grow `tools/ufo_build.py::CORE_CHARS` past the Core Latin MVP
      (~88 glyphs: uppercase, lowercase, digits, core punctuation) to
      Latin-1/Latin Extended-A, so accented characters render instead of
      falling back to `.notdef`. Composite glyphs (accents, and already
      `%`) decompose cleanly against Roboto Flex's own glyphset via
      `_copy_outline`'s `DecomposingRecordingPen` -- this is mainly a
      matter of widening `CORE_CHARS`, not new plumbing.
- [ ] Numeral sets: Roboto Flex ships tabular/proportional and
      lining/oldstyle figure variants (`.tf`/`.pf`/`.lf`/`.osf` suffixes)
      behind GSUB features that Azrienoch doesn't import (see "OpenType
      features" below) -- only the default figures come across today.

## Axis space

- [ ] A fourth `wght` sample between 400 and 900 (or 100 and 400) in
      `tools/roboto_source.py::_HEIGHT_AXES_AT_WGHT`, so the height/stroke
      correlation curve isn't purely two line segments.
- [ ] Consider exposing `GRAD` (grade) as a real Azrienoch axis --
      Roboto Flex supports it natively and it's a natural fit alongside
      `wght`/`wdth`/`SERF`; currently fixed at 0 in `roboto_location()`.
- [ ] Consider an `opsz` (optical size) axis, currently fixed at 24 in
      `roboto_location()`.
- [ ] `slnt` (slant/italic) is fixed at 0 -- Azrienoch has no italic.
      Worth a design decision on whether it ever should.
- [ ] Re-derive the `SERF` foot-sizing formulas
      (`tools/serifs.py::apply_feet`) once real serif specimens have been
      eyeballed at more than the two or three weights checked so far --
      the 0.9/0.42 multipliers are a first pass, not measured.

## Font engineering completeness

- [ ] **No named instances in `fvar`.** `fontmake` didn't generate any
      (confirmed: `len(font['fvar'].instances) == 0`), so apps that pick
      a style by name (rather than dragging axis sliders) currently only
      ever see the default. Add `<instances>` to
      `tools/designspace_build.py::write_designspace` for the 12 corners
      (or a curated subset) with real names ("Thin", "Black Condensed
      Serif", etc).
- [ ] **No `GSUB` table** -- confirmed no ligatures, case-sensitive
      punctuation, or figure-style features carried over from Roboto
      Flex, since only kerning (`GPOS`) is extracted today
      (`tools/roboto_source.py::extract_kerning`). Decide which of Roboto
      Flex's features are worth porting for the Core Latin MVP glyph set.
- [ ] **No hinting.** Fine for modern renderers (browsers, macOS, most of
      Linux); worth a pass if Windows GDI/small-size legacy rendering
      matters for this project.
- [ ] Review the auto-generated `STAT` table's axis value records --
      not audited beyond confirming the table exists.

## Tooling / process

- [ ] A repeatable check (script or CI) that asserts the compiled font's
      basics after every build: expected `fvar` axes and ranges, glyph
      count, and contour-count compatibility across all 12 masters. Right
      now this is verified by hand each time `tools/designspace_build.py`
      runs.
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

- [ ] A specimen page (the old Graduate had one, built with
      Grunt/Sass, removed along with the rest of Graduate) -- an
      interactive `wght`/`wdth`/`SERF` demo using the CSS
      `font-variation-settings` property would suit a variable font
      better than a static image.
