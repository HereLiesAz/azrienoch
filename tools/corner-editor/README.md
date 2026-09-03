# Corner Editor

A standalone tool for building a variable-font character by drawing it at
four extremes -- **extra thin**, **extra black**, **condensed**, **wide**
-- plus a fifth anchor, **regular**, at the dead center of that space --
and letting every other shape (any intermediate weight or width) fall out
of interpolation between corresponding nodes, rather than being drawn
separately.

Most variable-font editors let you hand-adjust the shape at any
interpolated instance. This tool deliberately doesn't: editing is confined
to these five fixed anchors. If the automatic interpolation looks wrong
somewhere in between, the fix is to adjust `regular`, not to add another
editable point.

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

1. **New glyph** -- type a name, click New. All five anchors start empty.
2. Pick one anchor (say Extra Thin) and click **New contour**, then click
   the canvas to place on-curve points tracing the letter's skeleton at
   that extreme. Click a point and **Toggle on/off-curve** to turn it into
   a quadratic control point where you need a curve instead of a corner.
3. Once that anchor's outline is right, click **Copy active anchor's
   outline to other 4 (seed topology)**. This is the step that makes
   interpolation possible: it gives all five anchors the same contour
   count and the same number of points per contour, in the same order.
4. Switch to each of the other four panels (including Regular) and drag
   its points toward that anchor's shape -- **don't add or delete points**
   once they're seeded, since interpolation matches points by index. If a
   shape genuinely needs a different point (an extra corner that only
   exists when very condensed, say), add/remove that point in every anchor
   at once so counts and on/off-curve types stay identical everywhere --
   the preview panel tells you exactly which contour/point index
   disagrees if they don't.
5. The **Preview** panel interpolates live as you edit, read-only. Its two
   sliders are the weight axis (0 = extra thin, 1 = extra black) and the
   width axis (0 = condensed, 1 = wide); **Jump to regular** sets both to
   0.5, which is exactly where the hand-drawn Regular anchor sits.
6. **Save glyph** writes all five anchors back to `data/<name>.json`.

## How the interpolation works

The four corner shapes sit at the corners of a weight x width grid:

```
              condensed (wdth=0)   wide (wdth=1)
extra thin  (wght=0)   extraThin        condensed*
extra black (wght=1)   extraBlack       wide*
```

Concretely, this tool fixes the assignment `extraThin=(0,0)`,
`extraBlack=(1,0)`, `condensed=(0,1)`, `wide=(1,1)` -- i.e. it treats the
four named drawings directly as the four corners of one square in
(weight, width) space. Plain bilinear interpolation of just those four
corners would already pass through all four exactly, but at the center
(0.5, 0.5) it can only ever land on their average -- it has no way to
reproduce a `regular` shape that was hand-corrected to be anything else.

So each point's interpolated position is corner-bilinear *plus a
displacement term*: the difference between the drawn `regular` anchor and
what bilinear alone would have predicted at the center, scaled by a bump
function (the product of two triangular "tent" curves, one per axis) that
equals 1 exactly at the center and fades to 0 along all four edges and
corners. The result reproduces all five hand-drawn anchors exactly and
blends smoothly everywhere between them, without needing the four
additional edge-midpoint masters a true biquadratic patch would require.

This needs exactly five drawings and no more, which is why the tool
enforces point-for-point compatibility across all five rather than trying
to guess correspondences.

## Data format

`data/<glyph>.json`:

```json
{
  "corners": {
    "extraThin":  { "width": 480, "contours": [{ "points": [{ "x": 0, "y": 0, "type": true, "smooth": false }, ...] }] },
    "extraBlack": { "width": 620, "contours": [...] },
    "condensed":  { "width": 420, "contours": [...] },
    "wide":       { "width": 600, "contours": [...] },
    "regular":    { "width": 500, "contours": [...] }
  }
}
```

`type: true` is an on-curve point; `type: false` is an off-curve quadratic
control point (TrueType-style runs of consecutive off-curve points use
implied midpoints, same as the main repo's `tools/point_editor.html`).
