# Ideas

Speculative future directions for Azrienoch. Nothing here is scoped,
scheduled, or committed to -- this is a place to keep an idea from
being lost, not a promise it happens. Once something here gets picked
up in earnest, it graduates to [`TODO.md`](./TODO.md).

## Axes

- **An italic.** Jost has no slant axis at all, and Azrienoch currently
  has none either. A genuine italic needs redrawn 'a'/'e'/'f'
  constructions, not a shear -- a project roughly the size of the
  original Jost import, not a quick addition. Worth revisiting once the
  upright weight is considered finished, not before.
- **A stencil or display-cut axis.** Speculative, no design work done.
  Would need its own topology work (gaps in strokes are a much bigger
  structural change than `SERF`'s feet), and no specimen or sketch
  exists yet.

## Glyph coverage

- **Greek.** Tried once (a second donor font, structurally
  incompatible with Jost's own point topology for this project's
  per-letter-class refinement to reuse) and dropped. Doing it properly
  would mean either finding/drawing a Jost-compatible Greek glyph set,
  or accepting a permanent style seam and building Greek-specific
  quirks/serifs/kerning logic from scratch for a second donor -- real
  work, not attempted yet.
- **Beyond Latin-1/Latin Extended-A/Cyrillic.** Full Unicode coverage
  of any of those blocks, or additional scripts entirely, is out of
  scope for now. The ceiling here is "how much of what Jost already
  has does Azrienoch bring in," not a from-scratch drawing effort.
- **Ligatures and case-sensitive punctuation forms.** Unported. Worth
  it only if a concrete need comes up.

## Tooling and process

- **Breaking-change detection straight from the diff.** Currently the
  release version is computed purely from conventional-commit messages
  (`versioning.md`); nothing inspects the actual diff for a removed
  glyph, a narrowed axis range, a metric/kerning change that could
  shift an existing layout, or a changed glyph outline. Worth building
  once the font has real consumers to protect against an accidental
  breaking `MINOR`/`PATCH` release -- premature while the font is still
  actively changing shape.
- **Variable-font hinting.** Not attempted -- real variable-font
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
  specific glyph's shape at the extremes visually, outside this Python
  pipeline. There's currently no path for feeding a Morphont-edited
  glyph back *into* `sources/*.ufo` -- that would mean either a
  UFO-writing export from Morphont, or a Python-side import of
  Morphont's JSON export format. Neither exists yet; this is purely a
  "could be useful" note, not a plan.

## Known open letterform issues

Tracked in more detail in [`design.md`](./design.md)'s "Not yet done"
section; noted here as the shortlist as of this writing:

- `e`'s aperture terminal self-intersects at the single most extreme
  corner of the design space (`wght`=100, `wdth`=75).
- `s`'s advance width doesn't track `o`'s own `wght`-relative
  proportions (no ring to derive from).
- `s` at Thin has its own near-zero, currently invisible ring-wall
  pinch inherited from the plain Cartesian interpolation between
  Arimo's Regular and Bold.
