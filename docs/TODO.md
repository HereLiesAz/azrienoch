# TODO

Tracked follow-up work for Azrienoch, beyond what's in this repository.
Checked items are done (built, or a deliberate decision with reasoning);
everything else is open. See [`design.md`](./design.md) for the design
rationale these build on, and [`IDEAS.md`](./IDEAS.md) for speculative
future directions that aren't scoped or scheduled work yet.

This file tracks the current (Jost-based) pipeline. Earlier work on a
since-replaced Roboto Flex-based pipeline is preserved in git history,
not repeated here.

## Tooling

- [x] ~~Remove `tools/corner-editor/`~~ -- done: it never connected to
      this repository's actual build pipeline (Azrienoch's letterforms
      come from Jost via `tools/jost_source.py`, not from hand-drawn
      extremes -- see `design.md`), and had grown into a separate, much
      larger project in its own right. Continues as
      [Morphont](https://github.com/HereLiesAz/morphont), a standalone
      Compose Multiplatform (Kotlin/Wasm) PWA that can shape glyphs by
      hand across five weight/width anchors or import an existing
      variable TTF (Azrienoch's own compiled font included) and
      extract those anchors automatically.

## Glyph coverage

- [x] ~~Basic Latin, digits, punctuation~~ -- done: the original 62
      ASCII letters/digits, extracted from Jost, with a full pass of
      Azrienoch-specific modifications (terminal cuts, round-counter
      reshaping, serif feet).
- [x] ~~Latin-1 Supplement, Latin Extended-A, Cyrillic~~ -- done: 339
      glyphs total. `kerning.py` covers all of it; `quirks.py`'s
      round-counter reshaping and `serifs.py`'s per-letter-class foot
      rules extend to every accented Latin letter (`params.base_letter`,
      NFD decomposition) and nine lowercase Cyrillic letters confirmed
      to share a Latin letter's structure (`_CYRILLIC_ANALOG`).
- [ ] ~23 Cyrillic lowercase letters have no clean single-Latin-letter
      structural analog and are deliberately left on the generic
      unclassified default (see `design.md`).
- [ ] Greek -- tried (sourced from a second donor font), then dropped
      by direct decision: a structurally different donor's outlines
      don't share Jost's point topology for this project's own
      per-letter-class refinement to find anything, so Greek would have
      carried none of it. Out of scope unless revisited.

## Letterforms

- [x] ~~`c`/`e` derived directly from `o`~~ -- done
      (`tools/ring_derived.py`): guarantees bowl/counter proportions
      agree with `o`'s by construction, at every master.
- [x] ~~`a` built from `d`'s own outline~~ -- done
      (`tools/single_story_a.py`): single-story, not the double-story
      convention most grotesques inherit from print.
- [x] ~~`s` sourced from Arimo, weight-calibrated against Jost's own
      original `s`~~ -- done (`tools/arimo_source.py`).
- [ ] `s`'s advance width doesn't track `o`'s own `wght`-relative
      proportions (no ring to derive from -- an S-curve has no ring to
      cut open the way `c`/`e` do).
- [x] ~~`e`'s aperture terminal self-intersects at Thin Condensed~~ --
      done: `c`/`e` rebuilt with exactly horizontal terminals at
      levels read off Jost's own `e` (`c`'s upper terminal level with
      the top of `e`'s crossbar, lower with `e`'s terminal); no
      self-intersection at any master.
- [x] ~~V/W/M/v/w inconsistent stroke widths~~ -- done
      (`tools/stroke_balance.py`): one perpendicular thickness per
      glyph, outer silhouette unchanged.
- [x] ~~Thin Condensed serif feet oversized/off-center~~ -- done:
      stem measurement no longer filtered by the detection noise floor.
- [ ] At Black, `e`'s aperture (Jost's own `e` bar-bottom to terminal
      levels against `o`'s small counter) narrows to a slit.
- [ ] `s` at Thin has its own near-zero ring-wall pinch (~0.002 units,
      pre-existing, currently invisible).
- [ ] Round-counter treatment extended to `a` (its inner contour also
      carries the stem-join points, so it doesn't structurally match
      the others as a whole contour).

## Axis space

- [x] ~~`SERF` axis (slab feet)~~ -- done (`tools/serifs.py`).
- [x] ~~`GRAD` axis~~ -- done, approximated by sampling a nearby `wght`
      for shape while holding advance width fixed (Jost has no native
      grade axis).
- [ ] A true optically condensed `wdth` cut, replacing `condense.py`'s
      ink-density weighted compression (no counter is actually
      reshaped yet).

## Kerning

- [x] ~~Extract from Jost's own GPOS table~~ -- done: 7,774 pairs,
      covering the full character set.
- [x] ~~Derive kerning from our own outlines~~ -- done for the 62 base
      letters/digits (+ accented/Cyrillic inheritors): `tools/kern_derive.py`.
- [ ] Tune `GAP_CAP`/`STRENGTH`/`MIN_CLEAR` by eye against rendered
      specimens; extend derivation beyond the base set (punctuation,
      non-inheriting glyphs still use donor values).
