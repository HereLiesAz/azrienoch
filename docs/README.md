# Azrienoch documentation

Reference documentation for the Azrienoch variable font project. The
root [`README.md`](../README.md) is a short overview and quick-start;
everything else lives here.

- [`design.md`](./design.md) -- what Azrienoch does with Roboto Flex's
  own axis space, letterform by letterform: the reasoning behind every
  deliberate deviation from the source font.
- [`axes.md`](./axes.md) -- the four registered axes Azrienoch exposes,
  their ranges, and why `opsz`/`slnt` are deliberately not among them.
- [`build-pipeline.md`](./build-pipeline.md) -- the repository layout
  and what each module under `tools/` does, in build order.
- [`versioning.md`](./versioning.md) -- semantic versioning, how a
  release's version number gets computed, and what CI does on every
  push to `master`.
- [`TODO.md`](./TODO.md) -- tracked follow-up work: done items (with
  the reasoning or verification behind them) and what's still open.
- [`IDEAS.md`](./IDEAS.md) -- speculative future directions, not yet
  committed to. Distinct from `TODO.md`: nothing here has been decided
  on, scoped, or scheduled -- it's a place to keep an idea from being
  lost, not a promise it happens.

## Related tooling

The corner-editor tool that used to live at `tools/corner-editor/` --
a browser-based, draw-the-extremes glyph shaping experiment -- has been
removed from this repository. It didn't connect to Azrienoch's actual
build pipeline (which derives its letterforms from Roboto Flex, not
from hand-drawn corners; see `design.md`) and had grown into a
separate, much larger effort in its own right: a full variable-font
authoring tool, now developed as
[**Morphont**](https://github.com/HereLiesAz/morphont), a standalone
Compose Multiplatform (Kotlin/Wasm) PWA. Morphont can both shape glyphs
by hand across five weight/width anchors and import an existing
variable TTF (this includes `fonts/variable/Azrienoch-VF.ttf` itself)
to extract those anchors automatically. It isn't part of Azrienoch's
build and isn't required to build this font -- it's a separate project
that happens to share this font's design problem.
