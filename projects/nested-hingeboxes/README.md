# Four nested HingeBoxes

Four [HingeBox](https://boxes.hackerspace-bamberg.de/HingeBox) boxes
(`boxes/generators/hingebox.py`) that nest inside each other. The folder holds the
sizing analysis, the scripts that lay the pieces out, and the cut files they produced.

| Path | What it is |
|---|---|
| `generate.sh` | Regenerates every SVG in this folder |
| `pack_single.py` | Packs all pieces onto one sheet |
| `pack_sheets.py` | Packs all pieces onto N equal sheets laid out in a grid, with cut lines between sheets, and fills the leftover space with spare hinge pieces |
| `check_layout.py` | Checks a multi-sheet file from the SVG alone: every gap ≥ 3 mm, every piece ≥ 5 mm inside its sheet |
| `compare.py` | Prints the comparison table of all layouts |
| `render_previews.js` | Renders the SVGs to PNG previews (Playwright + Chromium) |
| `boxes/box1.svg` … `box4.svg` | The four boxes, each from the stock HingeBox generator |
| `cutsheet.svg` | All four boxes on one sheet |
| `sheets/sheetsN.svg` | N equal sheets, with spare hinge pieces |
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
7. *Drop the clustered layouts. For the others, fit as many extra hinge pieces as
   possible without making the sheets bigger.*

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

## 4.–7. N equal sheets with spare hinge pieces

Every piece is at least 5 mm inside its sheet's cut line, which leaves a protective
frame, and 3 mm from every other piece. The sheets sit in the grid closest to square,
and neighbours share one cut line.

How `pack_sheets.py` builds a layout:

1. **Sheet size.** The smallest sheet into which a rectangle packer (rectpack, several
   algorithms and sort orders, 90° rotation) fits every piece's bounding box, with the
   40 hinge pieces packed one by one. These sizes are the same as in the earlier
   rounds; adding spares never makes a sheet bigger.
2. **Spare hinge pieces at that fixed size.** The hinge pieces are identical for all
   four boxes, so any spare fits any box. Each layout is tried both ways:
   * **A:** the box pieces plus k hinge pieces are packed as rectangles, then more
     hinge pieces are dropped into the leftover space by their real outline.
   * **B:** the same packing, but the rectangle-placed hinge pieces are removed and
     every hinge piece is placed by outline.

   This runs for several k and every packer setting that fits. Placing by outline
   uses all 4 rotations, top-left first, in 0.25 mm steps. A fast grid test proposes
   positions, and each one is checked exactly against the real outlines. That lets the
   hook-shaped pieces interlock and tuck in beside the finger joints. The layout with
   the most hinge pieces wins.
3. **Independent check.** `check_layout.py` re-reads every finished SVG and confirms
   each gap is ≥ 3 mm and each piece is ≥ 5 mm inside its sheet. All layouts pass.

Spare pieces are unlabelled like the other hinge pieces. Cut them all; any 10 make one
box's hinges.

All of this is heuristic: these are the best layouts found, not proven optima.

### Comparison of all options

Utilization = real area of the cut pieces in the file (outlines minus holes and
finger notches, spare hinge pieces included) / total sheet area. "vs best" is the
extra material compared with the smallest layout. The table is the output of
`compare.py`.

| Sheets | Sheet (mm) | Sheet (in) | Grid | Overall (mm) | Overall (in) | Material (m²) | vs best | Hinge pieces | Utilization |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 803 × 559 | 31.61 × 22.00 | 1 × 1 | 803 × 559 | 31.61 × 22.00 | 0.449 | +5.5% | 40 | 74.4% |
| **6** | **278 × 255** | **10.94 × 10.04** | **2 × 3** | **556 × 765** | **21.89 × 30.12** | **0.425** | **best** | **74 (+34 spare)** | **79.5%** |
| 8 | 188 × 285 | 7.40 × 11.22 | 4 × 2 | 752 × 570 | 29.61 × 22.44 | 0.429 | +0.8% | 48 (+8 spare) | 78.1% |
| 9 | 256 × 189 | 10.08 × 7.44 | 3 × 3 | 768 × 567 | 30.24 × 22.32 | 0.435 | +2.4% | 71 (+31 spare) | 77.5% |
| 10 | 222 × 197 | 8.74 × 7.76 | 2 × 5 | 444 × 985 | 17.48 × 38.78 | 0.437 | +2.8% | 59 (+19 spare) | 76.9% |
| 12 | 188 × 198 | 7.40 × 7.80 | 4 × 3 | 752 × 594 | 29.61 × 23.39 | 0.447 | +5.0% | 78 (+38 spare) | 75.8% |

The single sheet is the original one-sheet layout (`cutsheet.svg`, 3 mm margins), with
no spares added.

Takeaways:

* **6 sheets uses the least material and still fits 34 spare hinge pieces,** enough
  for three more boxes' hinges.
* **8 sheets is the tightest layout:** its sheet size was pushed down until the
  required pieces barely fit, so only 8 spares fit.
* **More sheets means more leftover space but also more frame,** so total material
  rises from 0.425 m² (6 sheets) to 0.447 m² (12 sheets). 12 sheets fits the most
  spares (38).
* How many spares fit depends on where the packer happens to leave gaps, not just on
  total free area. That is why 9 sheets fits more than 10.

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

Each multi-sheet layout takes about 10–15 minutes (the sheet-size search plus filling
spares into every candidate layout), and `generate.sh` runs them in parallel. The
results are deterministic. `pack_sheets.py --sheet WxH` skips the size search. To change sizes, thickness or lid height,
edit the size list in step 1 of `generate.sh`.
