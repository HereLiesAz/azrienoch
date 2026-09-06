# Azrienoch

A variable font built on [Jost](https://github.com/indestructible-type/Jost)
(SIL OFL 1.1), a real, professionally drawn geometric sans -- not drawn
from scratch. Azrienoch takes Jost's own outlines and adds a `SERF`
axis that grows a slab foot from nothing, a `GRAD` axis for optical
compensation, and a handful of Helvetica-inspired terminal/counter
adjustments on top.

339 glyphs -- basic Latin, digits, punctuation, Latin-1 Supplement,
Latin Extended-A, and Cyrillic.

## Axes

| Axis | Tag | Range | Default |
|---|---|---|---|
| Weight | `wght` | 100-900 | 400 |
| Width | `wdth` | 75-100 | 100 |
| Serif | `SERF` | 0-100 | 0 |
| Grade | `GRAD` | -50-50 | 0 |

See [`docs/axes.md`](docs/axes.md) for the full account.

## Building

```
pip install -r requirements.txt
python3 -m tools.designspace_build
```

Output: `sources/*.ufo`, `sources/Azrienoch.designspace`,
`fonts/variable/Azrienoch-VF.ttf`, `fonts/variable/Azrienoch-VF.woff2`.
This also validates the build and re-embeds the font into
`specimen/index.html`.

## Specimen

Open [`specimen/index.html`](specimen/index.html) directly in a
browser for a live, interactive specimen (axis sliders, named-instance
presets, glyph set) -- no server needed. Also published to GitHub
Pages on every change to `specimen/**` on `master` (see
`.github/workflows/pages.yml`).

## Known limitations

- No Greek. Jost itself has almost none of it (4 codepoints total); a
  second donor font was tried and dropped -- see
  [`docs/design.md`](docs/design.md#status).
- `wdth` is an ink-density weighted compression, not a true optically
  condensed redraw (no counter is actually reshaped).
- No italic.
- A handful of narrow, documented letterform residuals -- see
  [`docs/design.md`](docs/design.md#not-yet-done).

## Documentation

Full reference documentation lives in [`docs/`](docs/README.md):
design rationale, axis details, the build pipeline module by module,
versioning, and tracked follow-up work.

## License

Azrienoch's outline data is a Modified Version of Jost, under the SIL
Open Font License, Version 1.1 (`OFL.txt`; Jost's own license and
authors at `third_party/jost/OFL.txt`). `c`/`e`/`s` are additionally a
Modified Version of [Arimo](https://github.com/googlefonts/arimo),
under the same license (`third_party/arimo/OFL.txt`).
