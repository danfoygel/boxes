# Four nested HingeBoxes

Four [HingeBox](https://boxes.hackerspace-bamberg.de/HingeBox) boxes
(`boxes/generators/hingebox.py`) that nest inside each other. The folder holds the
sizing analysis, the scripts that lay the pieces out, and the cut files they produced.

| Path | What it is |
|---|---|
| `generate.sh` | Regenerates every SVG in this folder |
| `pack_sheets.py` | Packs all pieces onto N equal sheets laid out in a grid, with cut lines between sheets, and fills the leftover space with spare hinge pieces |
| `check_layout.py` | Checks a multi-sheet file from the SVG alone: every gap ≥ 3 mm, every piece ≥ 5 mm inside its sheet |
| `compare.py` | Prints the comparison table of all layouts |
| `render_previews.js` | Renders the SVGs to PNG previews (Playwright + Chromium) |
| `boxes/box1.svg` … `box4.svg` | The four boxes, each from the stock HingeBox generator (7-piece hinges) |
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
8. *Build each hinge from 7 pieces instead of 5 to make it stronger.* Then: *remove
   the single cutsheet.*

The single cutsheet (request 3) and the clustered layouts (request 4) have since been
removed. The repository history has them.

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

All boxes use inside dimensions (outside mode off), `--thickness 3`,
`--lidheight 20` and `--CabinetHinge_eyes_per_hinge 7`. The height is split as h + 20.

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

### 7-piece hinges

Each box has 2 hinges, and each hinge is now built from 7 pieces instead of the
generator's default 5: 4 attached to the box's back wall and 3 to the lid's, alternating
on one pin. So each box has 14 hinge pieces, 56 for all four. The pieces themselves are
unchanged. The back walls get 4 t × t holes per hinge (lid walls 3), and each hinge's
cut-out in the wall edge is 2 × (t + play) = 6.3 mm wider. That widens the bearing
surface on the pin from about 16 mm to about 22 mm per hinge.

Nesting is unaffected: the hinge pieces have the same shape and sit in the same
place, so the knuckle and interior offsets above still hold. The hinges get wider, but
the 160 mm innermost box still has plenty of room for two of them.

## 3. N equal sheets with spare hinge pieces

Every piece is at least 5 mm inside its sheet's cut line, which leaves a protective
frame, and 3 mm from every other piece. The sheets sit in the grid closest to square,
and neighbours share one cut line.

How `pack_sheets.py` builds a layout:

1. **Sheet size.** The size search finds the smallest sheet into which a rectangle
   packer (rectpack, several algorithms and sort orders, 90° rotation) fits every
   piece's bounding box. It ran with the 5-piece hinges, and those sizes are kept
   (`--sheet` in `generate.sh`). A sheet grows, in 2 mm steps and smallest area
   first, only if the required pieces no longer fit. With 7-piece hinges, only the
   8-sheet layout had to grow, from 188 × 285 to 190 × 287 mm.
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

Spare pieces are unlabelled like the other hinge pieces. Cut them all; any 14 make one
box's hinges (2 hinges × 7 pieces).

All of this is heuristic: these are the best layouts found, not proven optima.

### Comparison of all options

Utilization = real area of the cut pieces in the file (outlines minus holes and
finger notches, spare hinge pieces included) / total sheet area. "vs best" is the
extra material compared with the smallest layout. The table is the output of
`compare.py`.

| Sheets | Sheet (mm) | Sheet (in) | Grid | Overall (mm) | Overall (in) | Material (m²) | vs best | Hinge pieces | Utilization |
|---|---|---|---|---|---|---|---|---|---|
| **6** | **278 × 255** | **10.94 × 10.04** | **2 × 3** | **556 × 765** | **21.89 × 30.12** | **0.425** | **best** | **74 (+18 spare)** | **79.3%** |
| 8 | 190 × 287 | 7.48 × 11.30 | 4 × 2 | 760 × 574 | 29.92 × 22.60 | 0.436 | +2.6% | 75 (+19 spare) | 77.3% |
| 9 | 256 × 189 | 10.08 × 7.44 | 3 × 3 | 768 × 567 | 30.24 × 22.32 | 0.435 | +2.4% | 71 (+15 spare) | 77.4% |
| 10 | 222 × 197 | 8.74 × 7.76 | 2 × 5 | 444 × 985 | 17.48 × 38.78 | 0.437 | +2.8% | 59 (+3 spare) | 76.7% |
| 12 | 188 × 198 | 7.40 × 7.80 | 4 × 3 | 752 × 594 | 29.61 × 23.39 | 0.447 | +5.0% | 78 (+22 spare) | 75.6% |

56 hinge pieces are needed (4 boxes × 2 hinges × 7).

Takeaways:

* **6 sheets uses the least material** and still fits 18 spare hinge pieces, enough
  for one more box's hinges.
* **The 7-piece hinges fit at unchanged sheet sizes everywhere except 8 sheets.** The
  16 extra required pieces come out of the spares, so 6, 9, 10 and 12 sheets each
  hold the same total number of hinge pieces as before.
* **8 sheets grew by 2 mm each way** (+1.8% material). The larger sheet happened to
  pack much better, so it now holds 19 spares instead of 8.
* **10 sheets has only 3 spares**, the fewest of any layout.
* How many spares fit depends on where the packer happens to leave gaps, not just on
  total free area.

## Cutting notes

* Colours follow boxes.py: black is the outline cut, blue the inner cuts (the hinge
  holes), red is labels only. Set red to engrave or skip.
* In the multi-sheet files the sheet cut lines come last, so the pieces are cut before
  the sheets come free. If your laser software reorders cuts, make sure the sheet
  lines go last.
* Kerf compensation is the boxes.py default (`--burn 0.1`).
* Each box needs two metal hinge pins about 3 mm thick, for example cut-off nails; the
  holes are 3.2 mm. With 7 pieces per hinge each pin spans about 22 mm of hinge
  pieces (7 × 3.15 mm). Cut the pins to that length: they are captured once the hinge
  is assembled.

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

Each multi-sheet layout takes about 3–8 minutes, and `generate.sh` runs them in
parallel. The results are deterministic. To change sizes, thickness, lid height or
hinge pieces, edit step 1 of `generate.sh`. To search sheet sizes from scratch instead
of starting from the stored ones, drop `--sheet` in step 2 (10–15 minutes per layout).
