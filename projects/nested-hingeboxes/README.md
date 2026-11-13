# Four nested HingeBoxes

Four [HingeBox](https://boxes.hackerspace-bamberg.de/HingeBox) boxes
(`boxes/generators/hingebox.py`) that nest inside each other. The folder holds the
sizing analysis, the scripts that lay the pieces out, and the cut files they produced.

| Path | What it is |
|---|---|
| `generate.sh` | Regenerates every SVG in this folder |
| `pack_single.py` | Packs all pieces onto one sheet |
| `pack_sheets.py` | Packs all pieces onto N equal sheets laid out in a grid, with cut lines between sheets |
| `compare.py` | Prints the comparison table of all layouts |
| `render_previews.js` | Renders the SVGs to PNG previews (Playwright + Chromium) |
| `boxes/box1.svg` … `box4.svg` | The four boxes, each from the stock HingeBox generator |
| `cutsheet.svg` | All four boxes on one sheet |
| `sheets/clustered/sheetsN.svg` | N sheets, each box's hinge pieces kept together |
| `sheets/split/sheetsN.svg` | N sheets, hinge pieces packed one by one |
| `previews/` | PNG renders of the cut sheets |

## The requests

1. *Look at the HingeBox design and figure out the offsets needed for another box of
   the same design to fit inside.*
2. *Use offset 8 for x and z and 15 for y. Four nested boxes, the innermost is
   160 × 80 × 80 mm. Calculate the other boxes.* Then convert those to inches, and
   explain "outside" mode.
3. *Lay out all the pieces for the four sizes on a single SVG cutsheet.*
4. *Split it into multiple sheets for packing as a protected stack for travel. All
   sheets must be the same size and sit side by side in the overall layout, with cut
   lines for each sheet, so they can be cut from one larger sheet of material. Find
   the best layout for 6, 8, 9 and 10 sheets and report the sheet size and overall
   utilization.*
5. *Recalculate without keeping each box's hinge pieces together.*
6. *Add a 12-sheet layout and a table comparing all the options.*

## 1. How much smaller the inner box must be

From the HingeBox generator code (`CabinetHingeEdge` in `boxes/edges.py`, default
`inside` hinge style), checked against a rendered SVG:

* **The pivot is on the outside face of the back wall.** Each hinge piece hooks
  through a slot and a t × t hole in the back wall. Its knuckle (radius `eye` = 1.5t)
  is centred on the line where box and lid meet, at the outer face. So the knuckles
  stick out **1.5t behind the box**: the real depth is y + 2t + 1.5t.
* **The hinge pieces reach 1t into the interior** from the back wall, in a band from
  4.5t (`eye` + 3t) below the box/lid joint to 4.5t above it.
* **The interior height of the closed box is h + lidheight.** Box and lid walls meet
  with no gap.

Minimum offsets for the next smaller box (same thickness t, default hinge settings):

| Dimension | Inner box | t = 3 mm |
|---|---|---|
| x | X − 2t − gap | X − 6 − gap |
| y | Y − 2t − 1.5t − 1t − gap = Y − 4.5t − gap | Y − 13.5 − gap |
| h + lidheight | H + LH − 2t − gap | H + LH − 6 − gap |

In y, 2t is the inner box's walls, 1.5t its knuckles and 1t the outer box's hinge
pieces.

* If the inner box's total closed height stays below the outer hinge band
  (h + lidheight + 2t ≤ H − 4.5t − gap), the y offset drops to 3.5t.
* The inner box can't fully open while inside the outer one, because its lid swings
  back past its back wall. Allow about lidheight + t more in y if it must open in place.
* Different thicknesses (outer T, inner t): x −2t, y −(2t + 1.5t + T), height −2t.

## 2. The four boxes

The chosen offsets are **8 mm for x and height, 15 mm for y**. With 3 mm material that
leaves about 2 mm of play in x and height and 1.5 mm in y. That works for material up
to about 3.3 mm thick; at that thickness y has no play left.

All boxes use inside dimensions (outside mode off), `--thickness 3` and
`--lidheight 20`. The height is split as h + 20.

| Box | x | y | height (h + lidheight) | h | x (in) | y (in) | height (in) |
|---|---|---|---|---|---|---|---|
| 1 (innermost) | 160 | 80 | 80 | 60 | 6.30 | 3.15 | 3.15 |
| 2 | 168 | 95 | 88 | 68 | 6.61 | 3.74 | 3.46 |
| 3 | 176 | 110 | 96 | 76 | 6.93 | 4.33 | 3.78 |
| 4 (outermost) | 184 | 125 | 104 | 84 | 7.24 | 4.92 | 4.09 |

The outermost box takes up about 190 × 135.5 × 110 mm
(7.48 × 5.33 × 4.33 in). That is 184 + 2t by 125 + 2t + 1.5t (the knuckles) by
104 + 2t.

### Outside mode

boxes.py's `outside` option treats x/y/h as outer instead of inner dimensions and
subtracts the walls. For HingeBox there are three exceptions:

* `lidheight` is always an inside measure.
* h becomes the closed outside height minus `lidheight`, because the generator
  subtracts 2t from h although the hinge edge at the top has no wall.
* The hinge knuckles stick out 1.5t beyond y.

The offsets above work in either mode, as long as all boxes use the same mode and
thickness.

## 3. One cutsheet

`cutsheet.svg`: 44 pieces on **803 × 559 mm**, 74.4% utilization by real piece area
(85% by bounding box). Pieces are 3 mm apart and may be rotated 90°.

## 4./5./6. N equal sheets

Every piece is at least 5 mm inside its sheet's cut line, which leaves a protective
frame, and 3 mm from other pieces. The sheets sit in the grid closest to square, and
neighbours share one cut line. The packer is a heuristic, so these are the best
layouts found, not proven optima.

`sheets/clustered/` keeps each box's 10 hinge pieces together. `sheets/split/` packs
all 40 hinge pieces one by one. The hinge pieces are identical for all four boxes
(they depend only on thickness and the hinge settings), so the split layouts leave
them unlabelled.

### Comparison of all options

Utilization here = real area of the cut pieces (outlines minus holes and finger
notches, 0.334 m² in total) / total sheet area. That makes every row directly
comparable. "vs best" is the extra material compared with the smallest layout. The
table is the output of `compare.py`.

| Hinge pieces | Sheets | Sheet (mm) | Sheet (in) | Grid | Overall (mm) | Overall (in) | Material (m²) | vs best | Utilization |
|---|---|---|---|---|---|---|---|---|---|
| single sheet | 1 | 803 × 559 | 31.61 × 22.00 | 1 × 1 | 803 × 559 | 31.61 × 22.00 | 0.449 | +5.5% | 74.4% |
| clustered | 6 | 282 × 257 | 11.10 × 10.12 | 2 × 3 | 564 × 771 | 22.20 × 30.35 | 0.435 | +2.2% | 76.8% |
| clustered | 8 | 280 × 197 | 11.02 × 7.76 | 2 × 4 | 560 × 788 | 22.05 × 31.02 | 0.441 | +3.7% | 75.7% |
| clustered | 9 | 248 × 197 | 9.76 × 7.76 | 3 × 3 | 744 × 591 | 29.29 × 23.27 | 0.440 | +3.4% | 75.9% |
| clustered | 10 | 174 × 258 | 6.85 × 10.16 | 5 × 2 | 870 × 516 | 34.25 × 20.31 | 0.449 | +5.5% | 74.4% |
| clustered | 12 | 188 × 198 | 7.40 × 7.80 | 4 × 3 | 752 × 594 | 29.61 × 23.39 | 0.447 | +5.0% | 74.7% |
| **split** | **6** | **278 × 255** | **10.94 × 10.04** | **2 × 3** | **556 × 765** | **21.89 × 30.12** | **0.425** | **best** | **78.5%** |
| split | 8 | 188 × 285 | 7.40 × 11.22 | 4 × 2 | 752 × 570 | 29.61 × 22.44 | 0.429 | +0.8% | 77.9% |
| split | 9 | 256 × 189 | 10.08 × 7.44 | 3 × 3 | 768 × 567 | 30.24 × 22.32 | 0.435 | +2.4% | 76.7% |
| split | 10 | 222 × 197 | 8.74 × 7.76 | 2 × 5 | 444 × 985 | 17.48 × 38.78 | 0.437 | +2.8% | 76.3% |
| split | 12 | 188 × 198 | 7.40 × 7.80 | 4 × 3 | 752 × 594 | 29.61 × 23.39 | 0.447 | +5.0% | 74.7% |

Takeaways:

* **6 sheets with split hinge pieces uses the least material.** Every other option
  costs 0.8–5.5% more.
* Splitting the hinge pieces saves 1–3% at 6–10 sheets. At 12 sheets it makes no
  difference: both end up at 188 × 198 mm. Box 4's bottom and lid top are
  184 × 125 mm, so with the 5 mm frame every sheet must be at least 194 mm in one
  direction. At 12 sheets that minimum leaves enough spare room that it doesn't
  matter how the hinge pieces are packed.
* Even 12 sheets costs only 5% more material than the best layout, and every
  multi-sheet layout beats the single sheet.

Earlier versions of these results quoted utilization by bounding box (for example
82.0% and 83.6% for the 6-sheet layouts). Those figures are higher because a piece's
bounding rectangle is larger than the piece. They also can't be compared between
clustered and split layouts.

## Cutting notes

* Colours follow boxes.py: black is the outline cut, blue the inner cuts (the hinge
  holes), red is labels only. Set red to engrave or skip.
* In the multi-sheet files the sheet cut lines come last, so the pieces are cut before
  the sheets come free. If your laser software reorders cuts, make sure the sheet
  lines go last.
* Kerf compensation is the boxes.py default (`--burn 0.1`).
* Each box needs two metal hinge pins about 3 mm thick, for example cut-off nails; the
  holes are 3.2 mm. Cut the pins to length: they are captured once the hinge is
  assembled.

## Regenerating

```bash
pip install -e .   # or the dependencies listed in pyproject.toml
```

```bash
projects/nested-hingeboxes/generate.sh
```

```bash
python3 projects/nested-hingeboxes/compare.py
```

```bash
node projects/nested-hingeboxes/render_previews.js
```

The multi-sheet searches take one to a few minutes each, and `generate.sh` runs them
in parallel. The results are deterministic. To change sizes, thickness or lid height,
edit the size list in step 1 of `generate.sh`.
