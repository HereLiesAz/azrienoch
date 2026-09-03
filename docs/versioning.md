# Versioning and releases

Azrienoch follows [Semantic Versioning](https://semver.org/)
(`MAJOR.MINOR.PATCH`) and is currently pre-1.0 (`0.x.y`) -- the font is
still under active development, so per semver's own convention, a
`MINOR` bump can still include breaking changes; nothing before
`1.0.0` should be treated as stable.

`.github/workflows/release.yml` runs on every push to `master` (the
default branch): it computes the release version, rebuilds the font
with that version embedded, runs `tools/validate_build` as a gate (a
failed build or validation never gets released), and publishes a
GitHub Release tagged `v<version>` with the compiled
`Azrienoch-VF.ttf` (and a WOFF2 of the same font) attached.

## How the version is computed

**The version is computed by `tools/next_version.py`**, two ways:

- **Automatically**, from conventional-commit-style messages (`feat:`,
  `fix:`, `feat!:`/`BREAKING CHANGE:` in the body) in `git log` since
  the last release's tag -- a `feat:` commit bumps `MINOR`, a
  breaking-marked commit bumps `MAJOR`, anything else bumps `PATCH`.
  This is the default; most changes don't need a human to think about
  versioning at all.
- **Manually**, by editing the `VERSION` file at the repo root
  directly and committing it. A manual edit always wins over automatic
  computation -- this is how to declare a deliberate `MAJOR` bump that
  no single commit message captures (a redesign, or moving past
  `0.x.y` once the font is actually done breaking things), or to
  correct a mistake. See the module's own docstring for the exact
  mechanics (how it tells "manually bumped" apart from "already
  released").

The same computed version is what the built font itself embeds
(`AZRIENOCH_VERSION`, read by `ufo_build.py::_current_version`) -- a
release's tag and its binary's own version (`head.fontRevision`, and
the human-readable `Version X.Y.Z` string in its `name` table) always
agree. A local build outside CI (no `AZRIENOCH_VERSION` set) just
embeds whatever `VERSION` currently says.

## Not yet automated

Detecting a breaking change (a removed glyph, a narrowed axis range, a
metric/kerning change that could shift an existing layout, a changed
glyph outline) straight from the diff, independent of the commit
message. Given the font isn't finished yet, codifying that now would
be premature -- it's a natural next step once the letterform work
settles down and the font has real consumers to protect. Tracked in
[`IDEAS.md`](./IDEAS.md).
