# Azrienoch

A variable font that multiplexes several axes of control into one
typeface: weight, width, grade, and a sans/serif toggle, with cap-height
and x-height themselves tied to the weight axis rather than to point size
or line height.

Its letterforms, spacing and kerning are derived from
[Roboto Flex](https://github.com/googlefonts/roboto-flex) (SIL OFL
1.1) in code, not drawn from scratch -- see [`docs/design.md`](./docs/design.md)
for what that derivation actually does, letterform by letterform, and
why. This repository previously held
[Graduate](https://github.com/etunni/Graduate-Variable-Font), a
12-axis variable font by Eduardo Tunni; Azrienoch replaces it with the
same ambition for axis versatility on a different letterform
foundation.

## Documentation

Full documentation lives in [`docs/`](./docs/README.md):

- [`docs/design.md`](./docs/design.md) -- the design rationale, in full.
- [`docs/axes.md`](./docs/axes.md) -- the axis table and what's
  deliberately not an axis.
- [`docs/build-pipeline.md`](./docs/build-pipeline.md) -- repository
  layout and what each build tool does.
- [`docs/versioning.md`](./docs/versioning.md) -- semver, releases, CI.
- [`docs/TODO.md`](./docs/TODO.md) -- tracked follow-up work.
- [`docs/IDEAS.md`](./docs/IDEAS.md) -- speculative future directions.

## Axes

| Axis | Tag | Range | Default |
|---|---|---|---|
| Weight | `wght` | 180-900 | 400 |
| Width | `wdth` | 75-100 | 100 |
| Serif | `SERF` | 0-100 | 0 |
| Grade | `GRAD` | -50-50 | 0 |

## Building

```
pip install -r requirements.txt
python3 -m tools.designspace_build
```

This regenerates `sources/*.ufo`, `sources/Azrienoch.designspace` and
`fonts/variable/Azrienoch-VF.ttf`, and validates the result. See
[`docs/build-pipeline.md`](./docs/build-pipeline.md) for what each
step does.

## Specimen

`specimen/index.html` is a self-contained (font embedded) interactive
specimen: live `wght`/`wdth`/`SERF` sliders, all named-instance
presets, an editable hero sample, and a glyph-set showcase. Open it
directly in a browser -- no server needed.

## Known limitations

418 glyphs: uppercase, lowercase, digits (default tabular + alternate
proportional via the `pnum` feature), core punctuation, Latin-1
Supplement, Latin Extended-A, Greek and Cyrillic -- not full Unicode
coverage of any of those blocks, no other scripts, and no `GSUB`
features beyond `pnum` and the kerning that is carried over (no
ligatures, no case-sensitive forms). No hinting (see
[`docs/TODO.md`](./docs/TODO.md) for why that's a deliberate decision,
not an oversight). See [`docs/TODO.md`](./docs/TODO.md) for the full,
itemized list of what's next, and [`docs/IDEAS.md`](./docs/IDEAS.md)
for what's speculative beyond that.

## License

Azrienoch is licensed under the [SIL Open Font License, Version 1.1](./OFL.txt),
as a Modified Version of Roboto Flex. Roboto Flex's own license is in
`third_party/roboto-flex/OFL.txt` and its authors are in
`third_party/roboto-flex/AUTHORS.txt`.
