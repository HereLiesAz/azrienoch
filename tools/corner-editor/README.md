# Corner Editor

A standalone tool for building a variable-font character by drawing it at
four extremes -- **extra thin**, **extra black**, **condensed**, **wide**
-- and letting every shape in between (a regular weight, an intermediate
width, or any point in the space) fall out of bilinear interpolation
between corresponding nodes, rather than being drawn separately.

This is intentionally decoupled from the rest of the Azrienoch repo: no
dependency on `ufoLib2`, `fontTools`, or `sources/*.ufo`. It's meant to be
lifted into its own repository unchanged. Glyphs live as plain JSON under
`data/`.

## Running it

```
python3 tools/corner-editor/server.py [--port 8766]
```

Then open `http://localhost:8766/`.

## Workflow

1. **New glyph** -- type a name, click New. All four corners start empty.
2. Pick one corner (say Extra Thin) and click **New contour**, then click
   the canvas to place on-curve points tracing the letter's skeleton at
   that extreme. Click a point and **Toggle on/off-curve** to turn it into
   a quadratic control point where you need a curve instead of a corner.
3. Once that corner's outline is right, click **Copy active corner's
   outline to other 3 (seed topology)**. This is the step that makes
   interpolation possible: it gives all four corners the same contour
   count and the same number of points per contour, in the same order.
4. Switch to each of the other three panels and drag its points toward
   that corner's extreme -- **don't add or delete points** once they're
   seeded, since interpolation matches points by index. If a shape
   genuinely needs a different point (an extra corner that only exists
   when very condensed, say), add/remove that point in every corner at
   once so counts and on/off-curve types stay identical everywhere -- the
   preview panel tells you exactly which contour/point index disagrees if
   they don't.
5. The **Preview** panel interpolates live as you edit. Its two sliders
   are the weight axis (0 = extra thin, 1 = extra black) and the width
   axis (0 = condensed, 1 = wide); **Jump to regular** sets both to 0.5.
6. **Save glyph** writes all four corners back to `data/<name>.json`.

## How the interpolation works

Each of the four drawn shapes is one corner of a weight x width grid:

```
              condensed (wdth=0)   wide (wdth=1)
extra thin  (wght=0)   extraThin        condensed*
extra black (wght=1)   extraBlack       wide*
```

Concretely, this tool fixes the assignment `extraThin=(0,0)`,
`extraBlack=(1,0)`, `condensed=(0,1)`, `wide=(1,1)` -- i.e. it treats the
four named drawings directly as the four corners of one square in
(weight, width) space, and bilinearly interpolates each point's `x`/`y`
(and the glyph's advance width) across that square for any `(wght, wdth)`
in `[0,1] x [0,1]`. This needs exactly four drawings and no more, which is
why the tool enforces point-for-point compatibility across all four
rather than trying to guess correspondences.

## Data format

`data/<glyph>.json`:

```json
{
  "corners": {
    "extraThin":  { "width": 480, "contours": [{ "points": [{ "x": 0, "y": 0, "type": true, "smooth": false }, ...] }] },
    "extraBlack": { "width": 620, "contours": [...] },
    "condensed":  { "width": 420, "contours": [...] },
    "wide":       { "width": 600, "contours": [...] }
  }
}
```

`type: true` is an on-curve point; `type: false` is an off-curve quadratic
control point (TrueType-style runs of consecutive off-curve points use
implied midpoints, same as the main repo's `tools/point_editor.html`).
