#!/usr/bin/env python3
"""Burn (kerf) test for the finger joints between the walls: a pair of small
pieces per burn value, one with each half of the joint, to find the value that
fits best.

usage: finger_test_sheet.py [OUT.svg]      (default: finger-test.svg next to this script)

The joints are drawn by boxes.py itself, with the generate.sh settings (3.2 mm and
the default finger joint, as on every corner of the boxes: 2t fingers and spaces,
no play), at the burn values of the hinge test (burn_test_sheet.py):

* For each burn value, a piece with an "f" edge (FingerJointEdge in
  boxes/edges.py) above a piece with the matching "F" edge
  (FingerJointEdgeCounterPart), facing each other, both cut at that value and
  engraved with it.  The pairs are in order, left to right and top row first.

The labels are single-line text in a Hershey font, engraved as lines (see
burn_test_sheet.py).
"""
import sys
from pathlib import Path

from burn_test_sheet import BURN, BURNS, HERE, T, Engraved, label

FINGERS = 5               # fingers on the "f" piece: the joint is 2t fingers and 2t spaces
LENGTH = (2 * FINGERS + 1) * 2 * T   # mm, the joint's length: FINGERS fingers, 2t spare at each end
HEIGHT = 9.0              # mm, each piece's height besides the joint
COLS = 3                  # pairs per row
GAP = 2.0                 # mm between pairs, beyond boxes.py's spacing
LABEL = 3.0               # mm, digit height of the labels


class FingerBurnTest(Engraved):
    def piece(self, edges, b):
        self.burn = b
        self.rectangularWall(LENGTH, HEIGHT, edges, move="up",
                             callback=[lambda: self.engrave(label(b), LENGTH / 2, HEIGHT / 2, LABEL)])
        self.burn = BURN

    def render(self):
        # each piece is HEIGHT plus t for the joint's fingers, plus spacing
        col_w = LENGTH + self.spacing + GAP
        row_h = 2 * (HEIGHT + T + self.spacing) + GAP
        rows = -(-len(BURNS) // COLS)
        for i, b in enumerate(BURNS):
            with self.saved_context():
                self.moveTo((i % COLS) * col_w, (rows - 1 - i // COLS) * row_h)
                self.piece("eeFe", b)   # joint on its top edge
                self.piece("feee", b)   # joint on its bottom edge, facing the one below


if __name__ == "__main__":
    FingerBurnTest.write(Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "finger-test.svg")
