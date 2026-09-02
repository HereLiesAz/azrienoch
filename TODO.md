# TODO

Tracked follow-up work for Azrienoch, beyond what's in this repository.
Checked items are done (built, or a deliberate decision with reasoning);
everything else is open. See `README.md` for the design rationale these
build on.

## Glyph coverage

- [x] ~~Grow `tools/ufo_build.py::CORE_CHARS` past the Core Latin MVP~~
      -- done: uppercase, lowercase, digits, core punctuation, Latin-1
      Supplement and Latin Extended-A (273 glyphs total). Composite
      glyphs (accents, `%`) decompose cleanly against Roboto Flex's own
      glyphset via `_copy_outline`'s `DecomposingRecordingPen`.
- [x] ~~Numeral sets: Roboto Flex's alternate proportional-figure style
      (`.prop`, behind its `pnum` GSUB feature)~~ -- done:
      `tools/ufo_build.py` now imports each digit's `.prop` variant
      alongside the default tabular one and emits a `feature pnum { ... }`
      block per master substituting between them, with the same
      `SERF`-axis feet applied to both. Verified in the compiled font:
      `GSUB` carries a `pnum` feature whose mapping substitutes each
      `uniXXXX` for `uniXXXX.prop`, and the `.prop` glyphs carry distinct
      (narrower, variable-width) advance widths from their tabular
      counterparts.
- [x] ~~Greek and Cyrillic: Roboto Flex covers both~~ -- done: added the
      modern monotonic Greek alphabet (upper/lowercase, final-form sigma,
      tonos-accented and dialytika vowels) and the modern Russian
      Cyrillic alphabet (upper/lowercase, including Ё/ё) to `CORE_CHARS`.
      All 133 added characters verified present in Roboto Flex's cmap
      with no gaps before importing. Glyph total: 273 -> 407 characters
      (418 glyphs including `.notdef` and the 10 `.prop` digit variants).

## Axis space

- [x] ~~A fourth `wght` sample~~ -- done: added 700 (Bold) to
      `tools/roboto_source.py::_HEIGHT_AXES_AT_WGHT`, front-loading height
      growth (most of it by Bold, tapering toward Black) while stroke
      thickness keeps growing roughly proportionally, so the curve
      actually bends there instead of being two straight segments.
- [x] ~~Consider exposing `GRAD` (grade) as a real Azrienoch axis~~ --
      done: `GRAD` (-50-50, default 0) is now a real registered axis.
      Unlike `wght` it changes stroke weight without touching metrics or
      advance widths, so it's safe for live optical compensation. Three
      masters (-50/0/50), not two -- `fontmake` requires an actual source
      at a designspace's default location on every axis, so 0 has to be a
      real master alongside the extremes, not just their interpolated
      midpoint. Verified: rendering the same text at GRAD=-50 vs. GRAD=50
      shows visibly heavier strokes at the same advance widths.
      Master grid grew from 16 to 48 (4 wght x 2 wdth x 2 SERF x 3 GRAD).
- [x] ~~Consider an `opsz` (optical size) axis~~ -- decided against:
      exposing it would reintroduce a size-driven proportion change,
      which directly contradicts "height as a matter of weight, not of
      font size" (README's "Design" section). Fixed at Roboto Flex's own
      default (24) and, since it's now permanently fixed, trimmed out of
      the vendored font entirely (see "Font engineering completeness"
      below).
- [x] ~~`slnt` (slant/italic)~~ -- decided against: Roboto Flex's own
      `slnt` axis only reaches -10 degrees, a barely-there lean rather
      than a real italic, and an actual italic needs redrawn letterforms
      (different 'a'/'e'/'f' constructions), not a shear -- out of scope.
      Fixed at 0 (upright) and trimmed out of the vendored font.
- [x] ~~Re-derive the `SERF` foot-sizing formulas
      (`tools/serifs.py::apply_feet`) once real serif specimens have been
      eyeballed at more than a handful of weights~~ -- done: rendered
      'Ilnmh' at SERF=100 through an actual browser text-rendering stack
      (Chromium/Skia/HarfBuzz via `@font-face`, not the matplotlib
      preview) at Thin/Regular/Bold/Black and Condensed, zoomed in on
      each. The 0.9/0.42 multipliers hold up: foot thickness scales with
      stroke weight the way a serif's should (a thin hairline slab at
      Thin, a substantial one at Black), staying proportionate rather
      than over- or under-sized at either extreme. No change made --
      verified, not just asserted. (One unrelated thing found in the
      process, and ruled out as ours: Roboto Flex's own Thin 'h'/'n'/'m'
      shows a faint anti-aliasing artifact at the arch spring, present
      even at `SERF=0` with no Azrienoch modification anywhere near it --
      upstream Roboto Flex Thin-weight rendering, not a `serifs.py` bug.)
- [x] ~~The `XTRA` (counter width) values in `_HEIGHT_AXES_AT_WGHT` (420 /
      540 / 565 / 580 across the four `wght` samples)~~ -- done, same
      real-rendering pass: 'oedbBOG' at Thin/Regular/Black shows the
      counters staying genuinely open at every weight, Black included --
      the design goal ("counters pushed wide... refusing the trade where
      ink crowds out the void", README) holds up under an actual
      rendering stack, not just in theory. No change made.

## Font engineering completeness

- [x] ~~No named instances in `fvar`~~ -- done: one named instance per
      master (48, after the `GRAD` axis addition) via
      `tools/designspace_build.py::write_designspace`, plus `STAT`
      axis-value labels (`WGHT_LABELS`/`WDTH_LABELS`/`SERF_LABELS`/
      `GRAD_LABELS`) so design apps show a proper style picker instead of
      raw sliders.
- [x] ~~No `GSUB` table~~ -- partially addressed: `pnum` (proportional
      figures) is now ported (see "Glyph coverage" above). Ligatures and
      case-sensitive punctuation forms remain unported -- Roboto Flex's
      own use of them is minimal enough (mostly `liga`/`locl` for
      non-Latin shaping Azrienoch doesn't import) that it wasn't judged
      worth the added build complexity yet; revisit if a concrete need
      comes up.
- [x] ~~No hinting~~ -- decided against, not merely deferred: TrueType
      hinting for a *variable* font (hinting that has to stay correct
      across the whole `gvar` design space) is not what tools like
      `ttfautohint` do -- they hint one static instance at a time and
      have no concept of interpolatable hint programs at all. Real
      variable-font hinting uses specialized, largely manual tooling
      (e.g. Microsoft's VTT) that's a project of its own, and many
      production variable fonts (including several of Google Fonts' own)
      ship unhinted for exactly this reason, relying on FreeType/
      DirectWrite/CoreText's own rendering-time hinting/antialiasing.
      Worth revisiting only if Windows GDI or another legacy small-size
      rendering path turns out to matter for this project.
- [x] ~~Review the auto-generated `STAT` table's axis value records~~ --
      done as part of the named-instances work above, and re-verified
      after the `wght`-Bold and `GRAD` additions: one axis-value record
      per label (`WGHT_LABELS`/`WDTH_LABELS`/`SERF_LABELS`/`GRAD_LABELS`),
      each value labeled and each axis's default marked elidable.
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
- [x] ~~Install the compiled `fonts/variable/Azrienoch-VF.ttf` in a real
      OS / browser / design app and spot-check rendering~~ -- done, as
      far as this sandboxed environment allows: loaded the compiled
      variable font via `@font-face` (`format('truetype-variations')`)
      into headless Chromium and rendered through its real text stack
      (Skia + HarfBuzz for shaping/kerning, not the matplotlib renderer
      `tools/preview.py` uses for quick dev-time QA). Confirmed correct
      rendering, `wght`/`wdth`/`SERF`/`GRAD` variation, kerning, and
      Greek/Cyrillic shaping with no tofu or shaping errors. What this
      doesn't cover: an actual design app (Illustrator, Figma, InDesign)
      or a non-Chromium engine (DirectWrite, CoreText) -- no such
      software is available in this environment. Worth a manual spot
      check outside it if that class of bug is a concern.
- [x] ~~Consider trimming the vendored
      `third_party/roboto-flex/RobotoFlex[...].ttf`~~ -- done, now that
      `opsz`/`slnt` are settled as permanently fixed (see "Axis space"
      above): `fontTools.varLib.instancer` instances both out at their
      defaults, shrinking the vendored file from ~1.78 MB to ~0.68 MB
      with no behavior change (`roboto_location()` always requested those
      same fixed values from the untrimmed font).

## Presentation

- [x] ~~A specimen page~~ -- done: `specimen/index.html`, a
      self-contained (font embedded as a data URI) interactive specimen
      with live `wght`/`wdth`/`SERF` sliders using
      `font-variation-settings`, all named-instance presets, an editable
      hero sample, and a glyph-set showcase.
- [x] ~~The specimen page's `NAMED_INSTANCES` preset list and embedded
      font predate the `GRAD` axis and the Greek/Cyrillic/`pnum` glyph
      growth~~ -- done: regenerated against the current 48-master build
      (new `GRAD` slider, tabular/proportional figure comparison,
      Greek/Cyrillic in the glyph grid, updated counts). Also fixed a
      real bug found in the process -- the page had no
      `<meta charset="utf-8">` or any doctype/head/body at all, so
      opening it via `file://` let the browser guess the wrong encoding
      and mangled every accented/Greek/Cyrillic character into mojibake.
      Re-verified with a headless-browser render after the fix.

## Known issues

- [x] Capital 'A' had a genuine, pre-existing self-intersection at
      Thin/ExtraLight (`wght` 180-245ish), confirmed present even in the
      already-merged build with no Azrienoch-specific quirk touching the
      glyph at all -- a same-master bug in Roboto Flex's own low-weight
      extraction near where the counter met the outer silhouette. Fixed
      for real with the topology change flagged below as needed: both
      of 'A's apexes are now genuinely sharp, single points --
      `tools/quirks.py::_sharpen_A_apex` for the outer (visible) apex, a
      plain full collapse; `_rebuild_A_counter_apex` for the counter's
      own inner apex, a real topology exception (2 points become
      `2 * _A_COUNTER_SAMPLE_COUNT + 1`) that builds a genuinely
      constant-width, parallel edge alongside the apex-approach curve,
      sized to match the terminal's own inner/outer gap wherever the
      apex angle allows it (`_largest_safe_width`), instead of moving
      the old flat notch's two points and hoping. Verified both ways:
      a self-intersection sweep (flattened curves, every 5 units of
      `wght`, 180-900) is clean at every weight, and the new edge
      measures as genuinely constant-width against the apex-approach
      curve, not just non-crossing.
- [ ] Capital 'M' has the same species of pre-existing self-intersection
      'A' had, at the same weight range (`wght` 180-240ish), for the
      same reason -- a same-master bug in Roboto Flex's own low-weight
      extraction, not introduced by any quirk here. Not yet fixed:
      `tools/quirks.py::_sharpen_M_vertex` remains a deliberate no-op;
      its own docstring works through why a plain point-position
      collapse doesn't work here either, for the same reason 'A's
      didn't. 'A's own fix above proves the right general technique
      (a genuinely constant-width topology exception, not a
      point-position guess) -- extending it to 'M's three vertices is
      the next step, tracked separately.
- [x] Capital 'A's own crossbar overhung the legs' own outer edge at
      every weight (Roboto Flex's own raw crossbar is simply wider than
      the legs at both of its own heights), and the counter-apex
      construction above wasn't actually scaling its own width with
      weight the way the terminal's own gap does (an earlier version of
      `_largest_safe_width` searched only the short apex-adjacent curve,
      which silently capped the width far below the terminal's own
      target at Regular and heavier). Both fixed:
      `tools/quirks.py::_fit_A_crossbar` pulls the crossbar's own
      corners flush with the legs; `_largest_safe_width` now searches
      all the way down to the real foot corners, so the width tracks
      the terminal's own gap at every weight it geometrically can.
      Fixing the crossbar also surfaced (and fixed) a real regression in
      `serifs.py::detect_feet`'s own "does this foot border a counter"
      heuristic: the new counter-apex construction's own last point,
      right before wrapping to the foot corner, is close to that same
      foot by construction (not far up near the apex the way Roboto
      Flex's own original notch was), which flipped the heuristic and
      grew the serif foot on only one side -- `tools/ufo_build.py::_fix_diagonal_apex_foot_extendability`
      forces it back to symmetric. Separately, `detect_feet`'s own
      fractional-width reproduction (one reference master's own run
      length, scaled by each master's own overall glyph width) undershot
      'A's own real foot span by nearly 90 units at Black, since the
      legs splay outward with weight much faster than the advance width
      grows -- `tools/quirks.py::fit_A_serif_feet` recomputes the foot
      rectangles from this master's own real `p0`-`p1`/`p10`-`p11` span
      instead of the inherited fraction.

      What was previously written off here as a "small cosmetic dip
      below baseline, up to ~150 units at Black" was wrong -- rendered
      at actual size, it read as a real, visible gash cut into the
      bottom of the counter, worse at every heavier weight, up to
      ~190 units at Black. Fixed with `_A_COUNTER_MAX_FOOT_DIP` (30
      units): `_largest_safe_width`'s own bisection now treats a foot
      point dipping past that tolerance as unsafe, the same as a
      genuine crossing, capping the width at heavy weights instead of
      holding the terminal's own full target width all the way down.
      (A hard `y >= 0` floor was tried first and was worse: `p1`/`p10`
      themselves already sit exactly at y=0 in this source, so ANY
      positive width fails that check, which silently skipped the
      whole rebuild -- breaking the uniform 23-point topology every
      other master needs for gvar interpolation, corrupting the
      interpolated shape at every wght between the skipped master and
      its rebuilt neighbors. Caught by the self-intersection sweep,
      not the render.)

      Two isolated, narrow self-intersections remain, found only by
      the sweep, not by eye: `wght` 525 and 735 (both off the 5-unit
      sweep step elsewhere) still cross. Not yet root-caused -- next
      step if picked back up.
