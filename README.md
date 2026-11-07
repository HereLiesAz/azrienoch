# Azrienoch

Version 1.0.0. A 915-glyph variable font -- basic Latin, digits, punctuation, Latin-1 Supplement,
Latin Extended-A/B and Additional (including Vietnamese), Cyrillic, spacing and combining marks,
currency and math symbols, four Greek letters, and a set of logic and set-theory symbols.
The width axis runs down to a monospaced setting.

## Axes

| Axis | Tag | Range | Default |
|---|---|---|---|
| Weight | `wght` | 100-900 | 400 |
| Width | `wdth` | 0-100 (0 = Mono, 75 = Condensed) | 100 |
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
browser for the live, interactive proof (axis sliders, named-instance
presets, glyph set, kerning, TTF/WOFF2 download) -- no server needed. Also published to GitHub
Pages on every change to `specimen/**` on `master` (see
`.github/workflows/pages.yml`).

## Known limitations

- Greek is only the four letters Jost has (Δ Ω μ π) -- see [`docs/design.md`](docs/design.md#status).
- `wdth` is an ink-density weighted compression, not a true optically
  condensed redraw (no counter is actually reshaped); at `wdth` 0 the
  Condensed shapes are fitted into one fixed cell.
- No italic.
- A handful of narrow, documented letterform residuals -- see
  [`docs/design.md`](docs/design.md#not-yet-done).

## Documentation

Full reference documentation lives in [`docs/`](docs/README.md):
design rationale, axis details, the build pipeline module by module,
and versioning.

## License

Azrienoch's outline data is a heavily-modified version of Jost, under the SIL
Open Font License, Version 1.1 (`OFL.txt`; Jost's own license and
authors at `third_party/jost/OFL.txt`). `c`/`e`/`s` are additionally a
Modified Version of [Arimo](https://github.com/googlefonts/arimo),
under the same license (`third_party/arimo/OFL.txt`).
