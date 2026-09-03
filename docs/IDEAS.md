# Ideas

Speculative future directions for Azrienoch. Nothing here is scoped,
scheduled, or committed to -- this is a place to keep an idea from
being lost, not a promise it happens. Once something here gets picked
up in earnest, it graduates to [`TODO.md`](./TODO.md).

## Axes

- **An italic.** Roboto Flex's own `slnt` only reaches -10 degrees, a
  lean rather than a real italic (see `axes.md`), and Azrienoch
  currently has none. A genuine italic needs redrawn 'a'/'e'/'f'
  constructions, not a shear -- a project roughly the size of the
  original Roboto Flex import, not a quick addition. Worth revisiting
  once the upright weight is considered finished, not before.
- **Optical size (`opsz`), reconsidered as something other than a
  size-driven proportion change.** Currently rejected outright because
  it would reintroduce coupling between point size and proportions
  (`axes.md`). If a use case ever calls for size-sensitive rendering
  *without* touching height (unlike Roboto Flex's own `opsz`), that
  would be a different axis in spirit, not a straightforward reversal
  of the current decision.
- **A stencil or display-cut axis.** Speculative, no design work done.
  Would need its own topology work (gaps in strokes are a much bigger
  structural change than `SERF`'s feet), and no specimen or sketch
  exists yet.

## Glyph coverage

- **Beyond Latin-1/Latin Extended-A/Greek/Cyrillic.** Full Unicode
  coverage of any of those blocks, or additional scripts entirely, is
  out of scope for now (see root `README.md`'s "Known limitations").
  Roboto Flex itself covers considerably more than Azrienoch currently
  imports -- the ceiling here is "how much of what Roboto Flex already
  has does Azrienoch bring in," not a from-scratch drawing effort,
  which makes this cheaper than it sounds if it's ever prioritized.
- **`GSUB` beyond `pnum`.** Ligatures and case-sensitive punctuation
  forms remain unported (`TODO.md`, "Font engineering completeness").
  Roboto Flex's own use of them is minimal enough that it wasn't
  judged worth the build complexity yet -- revisit if a concrete need
  comes up, rather than speculatively.

## Tooling and process

- **Breaking-change detection straight from the diff.** Currently the
  release version is computed purely from conventional-commit
  messages (`versioning.md`); nothing inspects the actual diff for a
  removed glyph, a narrowed axis range, a metric/kerning change that
  could shift an existing layout, or a changed glyph outline. Worth
  building once the font has real consumers to protect against an
  accidental breaking `MINOR`/`PATCH` release -- premature while the
  font is still actively changing shape.
- **Variable-font hinting.** Deliberately decided against for now
  (`TODO.md`, "Font engineering completeness") -- real variable-font
  hinting needs specialized, largely manual tooling (e.g. Microsoft's
  VTT), not the static-font autohinters that exist today. Worth
  revisiting only if a legacy small-size rendering path (old Windows
  GDI, mainly) turns out to matter for this project's actual users.
- **A design-app / non-Chromium rendering spot check.** The rendering
  verification done so far uses headless Chromium (Skia + HarfBuzz);
  an actual design app (Illustrator, Figma, InDesign) or a
  non-Chromium text engine (DirectWrite, CoreText) hasn't been
  checked, for lack of available software in the development
  environment. A manual pass outside it would close this gap.
- **Feeding Morphont's variable-font import back into this pipeline.**
  [Morphont](https://github.com/HereLiesAz/morphont) can already
  import `fonts/variable/Azrienoch-VF.ttf` and extract its own
  five-anchor representation from it -- useful for hand-tuning a
  specific glyph's shape at the extremes visually, outside this
  Python pipeline. There's currently no path for feeding a
  Morphont-edited glyph back *into* `sources/*.ufo` -- that would mean
  either a UFO-writing export from Morphont, or a Python-side import
  of Morphont's JSON export format. Neither exists yet; this is purely
  a "could be useful" note, not a plan.

## Known open letterform issues

Tracked in more detail in `TODO.md`'s "Known issues" section; noted
here as the two genuinely open items as of this writing:

- Capital 'M' has the same species of pre-existing self-intersection
  'A' had (fixed), at the same low-weight range -- 'A's fix
  (`tools/quirks.py::_sharpen_A_apex`/`_rebuild_A_counter_apex`)
  proves the right general technique; extending it to 'M's three
  vertices is the next step.
- 'e' has a real, pre-existing self-intersection near its own
  upper-left eye opening, unrelated to and unaffected by the terminal
  graft work already done on its right side.
