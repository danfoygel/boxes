#!/usr/bin/env python3
"""Engraving test: small pieces with samples of the boxes' engraving, at the same
size as on the boxes, to tune the laser's engraving settings before the real job.

usage: engrave_test_sheet.py [OUT.svg]      (default: engrave-test.svg next to this script)

The engraving comes from engraving.box_text on the faces of the box SVGs in boxes/
(as engrave_boxes.py finds them), so it is exactly what the boxes get:

* A square per lid with one element of that lid's artwork (LID_SAMPLES).
* A rectangle with box 1's bottom: the tree, the name, "Chrismukkah 2026" and the
  menorah.
* A rectangle with box 1's front text.

Each piece is a plain cut rectangle with MARGIN clear round its engraving.  Run it
after generate.sh's step 1 (the box SVGs) and lid_charts.py (box 3's art).
"""
import sys
from pathlib import Path

from shapely.geometry import box
from shapely.ops import unary_union
from svgpathtools import parse_path

import engrave_boxes
import engraving
from burn_test_sheet import HERE, Engraved

# One element of each lid's artwork, by a rectangle (x0, y0, x1, y1) in mm from the
# top-left corner of the art's ink box on the lid: the shapes wholly inside it, or
# with clip=True (box 3's charts are a single shape), all the art cut to it.
LID_SAMPLES = [
    ("heart", (4.0, -0.4, 21.6, 23.3), False),
    ("cat", (20.9, 26.7, 46.9, 42.7), False),
    ("corner of chart III", (0.0, 62.0, 26.0, 88.0), True),
    ("light bulb", (22.9, 5.9, 56.9, 43.9), False),
]
MARGIN = 4.0              # mm, piece edge to its engraving
GAP = 2.0                 # mm between pieces, beyond boxes.py's spacing


def samples():
    """(name, path data list (y down), ink box, square) for each test piece."""
    jobs = [engrave_boxes.engrave(str(HERE / "boxes" / f"box{i}.svg")) for i in range(1, 5)]
    text = engraving.box_text(*([j[k][1] for j in jobs] for k in (1, 2, 3)))
    out = []
    for i, (name, (x0, y0, x1, y1), clip) in enumerate(LID_SAMPLES):
        lid = text[i]["lid"]
        ix, iy = lid["ink"][:2]
        win = (ix + x0, iy + y0, ix + x1, iy + y1)
        paths = [parse_path(d) for d in lid["d"]]
        if clip:
            g = unary_union([engraving._region(p) for p in paths]).intersection(box(*win))
            ds, ink = [engraving._path(g)], g.bounds
        else:
            keep = [(d, p.bbox()) for d, p in zip(lid["d"], paths)]
            keep = [(d, b) for d, b in keep if win[0] <= b[0] and b[1] <= win[2] and win[1] <= b[2] and b[3] <= win[3]]
            assert keep, f"box {i + 1}: nothing in the {name}'s rectangle"
            ds = [d for d, _ in keep]
            ink = (min(b[0] for _, b in keep), min(b[2] for _, b in keep),
                   max(b[1] for _, b in keep), max(b[3] for _, b in keep))
        out.append((f"box {i + 1} lid: {name}", ds, ink, True))
    for key, what in (("bottom", "box 1 bottom"), ("front", "box 1 front")):
        out.append((what, [text[0][key]["d"]], text[0][key]["ink"], False))
    return out


class EngraveTest(Engraved):
    def summary(self):
        return "; ".join(f"{name} {w:.1f} x {h:.1f} mm" for name, w, h in self.pieces)

    def piece(self, ds, ink, w, h):
        """The engraving centred on a w x h piece (callback: origin at its corner)."""
        cx, cy = (ink[0] + ink[2]) / 2, (ink[1] + ink[3]) / 2
        for d in ds:
            self.engrave_path(d, w / 2 - cx, h / 2 + cy)

    def render(self):
        self.pieces = []
        rows, row = [], []
        for name, ds, ink, square in samples():
            w, h = ink[2] - ink[0] + 2 * MARGIN, ink[3] - ink[1] + 2 * MARGIN
            if square:
                w = h = max(w, h)
            self.pieces.append((name, w, h))
            # the lid squares share a row; the bottom and front get one each
            if row and not square:
                rows.append(row)
                row = []
            row.append((ds, ink, w, h))
        rows.append(row)

        y = 0.0
        for row in reversed(rows):   # boxes.py is y up: the last row goes at the bottom
            x = 0.0
            for ds, ink, w, h in row:
                with self.saved_context():
                    self.moveTo(x, y)
                    self.rectangularWall(w, h, "eeee",
                                         callback=[lambda ds=ds, ink=ink, w=w, h=h: self.piece(ds, ink, w, h)])
                x += w + self.spacing + GAP
            y += max(h for *_, h in row) + self.spacing + GAP


if __name__ == "__main__":
    EngraveTest.write(Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "engrave-test.svg")
