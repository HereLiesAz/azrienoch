# Versioning and releases

Azrienoch follows [Semantic Versioning](https://semver.org/)
(`MAJOR.MINOR.PATCH`). The current version is **1.0.0**.

`tools/next_version.py` decides the version; `tools/ufo_build.py` embeds it
in the built font.

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
