#!/usr/bin/env python3
"""Burn (kerf) test for the hinges: a strip with a row of hinges along one edge
and loose hinge pieces, each hinge cut at a different burn value, to find the
value that fits best.

usage: burn_test_sheet.py [OUT.svg]      (default: burn-test.svg next to this script)

The hinges are drawn by boxes.py itself, with the generate.sh settings (3.2 mm,
the default "inside" CabinetHinge), so they are the ones in the boxes, cut down
to a single eye:

* The strip has one hinge per burn value along its bottom edge: the box side of a
  one-eye hinge (CabinetHingeEdge in boxes/edges.py), the slot in the edge for the
  eye and its one t x t hole, with the value engraved beside it.  The hinges are
  closer together than on a box (PITCH): the edge between them is plain.
* Below it, one hinge piece per burn value (CabinetHingeEdge.parts), in the same
  order, nested in pairs as boxes.py lays them out, with the value engraved on each.

Only the hinges and the pieces change with the burn value; the rest of the strip's
outline is cut at the generate.sh value (0.1 mm).  boxes.py draws an outline with
the cutting path offset outwards by the burn value, so where the value changes
along the outline, the path steps sideways by the difference (at most 0.025 mm,
on the straight edge between two hinges) and each hinge is the one a box cut at
its value would have.  The engraving is filled outlines in boxes.py's etching
colour (green), in the box engraving's font.
"""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from svgpathtools import CubicBezier, Line, QuadraticBezier, parse_path

import engraving

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
from boxes import Boxes, Color, edges  # noqa: E402

T = 3.2                   # --thickness in generate.sh
EYES = 1                  # eyes per test hinge: one hole, for one piece (the boxes have 7)
BURN = 0.1                # generate.sh's burn, used for the strip's outline between the hinges
BURNS = [round(0.075 + 0.005 * i, 3) for i in range(11)]   # 0.075 ... 0.125 mm
PITCH = 8.0               # mm from one hinge to the next (on a box, hinges are 2t apart at least)
END = 3.0                 # mm of plain edge at each end of the strip
LABEL = 3.0               # mm, font size of the labels, which run inward from the holes
LABEL_DEPTH = 18.5        # mm, strip edge to the centre of a label (the holes reach 14.4 mm)
TITLE = 3.0               # mm, font size of the title, above the labels
TITLE_DEPTH = 25.0        # mm, strip edge to the centre of the title
DEPTH = 28.0              # mm, the strip's width
PIECE_LABEL = 2.4         # mm, font size of the labels on the pieces (fits their 6 x 6 mm flat)
GREEN = "rgb(0,255,0)"    # boxes.py Color.ETCHING
NAMESPACES = {"": "http://www.w3.org/2000/svg", "cc": "http://creativecommons.org/ns#",
              "dc": "http://purl.org/dc/elements/1.1/",
              "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"}
for prefix, uri in NAMESPACES.items():
    ET.register_namespace(prefix, uri)


def label(value):
    return f"{value:.3f}".rstrip("0").lstrip("0")   # 0.075 -> ".075", 0.1 -> ".1"


class HingeRow(edges.BaseEdge):
    """The strip's bottom edge: one hinge per burn value."""

    def __call__(self, length, **kw):
        self.boxes.hinge_row()


class Engraved(Boxes):
    """Boxes with engraving, for the test sheets (finger_test_sheet.py and
    engrave_test_sheet.py use it too)."""

    def engrave_path(self, d, x=0.0, y=0.0, angle=0):
        """SVG path data `d` (y down, as in engraving.py) in the etching colour, its
        origin at x, y."""
        flip = lambda z: (z.real, -z.imag)   # noqa: E731  boxes.py is y up
        self.ctx.stroke()   # finish any outline in progress in its own colour
        with self.saved_context():
            self.moveTo(x, y, angle)
            self.set_source_color(Color.ETCHING)
            for seg in parse_path(d):
                if self.ctx._xy != flip(seg.start):
                    self.ctx.move_to(*flip(seg.start))
                if isinstance(seg, QuadraticBezier):   # the font's glyphs: raise to a cubic
                    seg = CubicBezier(seg.start, seg.start + 2 / 3 * (seg.control - seg.start),
                                      seg.end + 2 / 3 * (seg.control - seg.end), seg.end)
                if isinstance(seg, CubicBezier):
                    self.ctx.curve_to(*flip(seg.control1), *flip(seg.control2), *flip(seg.end))
                elif isinstance(seg, Line):
                    self.ctx.line_to(*flip(seg.end))
                else:
                    raise ValueError(f"can't draw {type(seg).__name__}")
            self.ctx.stroke()

    def engrave(self, text, x, y, size, angle=0):
        """Text centred (by its ink) on x, y, as glyph outlines in the etching colour."""
        d, _ = engraving.outlines([text], size, 0, 0)
        self.engrave_path(d, x, y, angle)

    def summary(self):
        return f"burn {', '.join(label(b) for b in BURNS)} mm"

    @classmethod
    def svg(cls, name):
        """Render as an SVG tree (for a file called `name`), with the etching filled,
        as in engrave_boxes.py; and the Boxes object."""
        box = cls()
        box.parseArgs(["--thickness", str(T), "--burn", str(BURN), "--reference", "0", "--labels", "0",
                       "--output", name])
        box.open()
        box.render()
        data = box.close()
        tree = ET.ElementTree(ET.fromstring(data.getvalue()))
        for el in tree.iter():
            if el.tag.endswith("path") and el.get("stroke") == GREEN:
                el.set("class", "engraving")
                el.set("fill", GREEN)
                el.set("stroke-width", "0.01")
        return tree, box

    @classmethod
    def write(cls, out):
        tree, box = cls.svg(out.name)
        tree.write(out, encoding="utf-8", xml_declaration=True)
        print(f"{out}: {box.summary()}")


class HingeBurnTest(Engraved):
    piece_label = None

    def hole(self, x, y, *args, **kw):
        # CabinetHingeEdge.parts draws each piece's pin hole first, at (0, e) in the
        # piece's own frame.  The piece is x = -2t ... 0 (plus the eye, x > 0, below
        # y = 2e), with a round bottom up to y = 2t and the notch for the wall at
        # y = 2e + t ... 2e + 2t, so the 2t x 2t square between them is flat.
        super().hole(x, y, *args, **kw)
        if self.piece_label:
            upside_down = self.ctx._m.a < 0     # the second piece of a pair is turned 180°
            self.engrave(self.piece_label, -T, self.hinge.eye + 1.5 * T, PIECE_LABEL, 180 if upside_down else 0)

    def set_burn(self, burn):
        """Change the burn value along an outline: the cutting path runs `burn`
        outside the part (to the right, going round it anticlockwise), so step
        out by the difference first."""
        d = burn - self.burn
        self.ctx.line_to(0, -d)
        self.ctx.translate(0, -d)
        self.burn = burn

    def hinge_row(self):
        self.edge(END)
        for b in BURNS:
            self.set_burn(b)
            self.hinge_edge(PITCH)
            self.set_burn(BURN)
        self.edge(END)

    def strip_labels(self):
        # labels turned to run inward, so they take little room along the edge
        for i, b in enumerate(BURNS):
            self.engrave(label(b), END + (i + 0.5) * PITCH, LABEL_DEPTH, LABEL, 90)
        self.engrave("hinge burn test (mm)", self.length / 2, TITLE_DEPTH, TITLE)

    def pieces(self):
        """One piece per burn value, nested in pairs as CabinetHingeEdge.parts lays
        them out: the second of a pair turned 180° and moved by (s, 4e + 3t + s)."""
        e, t, s = self.hinge.eye, T, self.spacing
        edge = edges.CabinetHingeEdge(self, self.hinge)
        pair_w = 2 * max(e, 2 * t) + 3 * s
        for i, b in enumerate(BURNS):
            with self.saved_context():
                self.moveTo((i // 2) * pair_w)
                if i % 2:
                    # parts() moves by (s/2, s/2) and then 2t in its own frame before
                    # drawing, so undo that for the turned piece
                    self.moveTo(2 * max(e, 2 * t) + 2 * s, 4 * e + 3 * t + 2 * s, 180)
                self.burn, self.piece_label = b, label(b)
                edge.parts(move=None)
                self.burn, self.piece_label = BURN, None
        return 4 * e + 3 * t + 2 * s

    def render(self):
        # spacing: the plain edge either side of the eye slot, so hinges are PITCH apart
        self.hinge = edges.CabinetHingeSettings(T, True, hinges=1, eyes_per_hinge=EYES)
        play = self.hinge.play
        self.hinge.values["spacing"] = (PITCH - (T + play) * EYES - play) / 2   # as in CabinetHingeEdge.__poly
        self.hinge_edge = edges.CabinetHingeEdge(self, self.hinge)
        self.length = 2 * END + len(BURNS) * PITCH

        # the pieces, then the strip above them
        self.moveTo(0, self.pieces() + self.spacing)
        self.rectangularWall(self.length, DEPTH, [HingeRow(self, None), "e", "e", "e"],
                             callback=[self.strip_labels])


if __name__ == "__main__":
    HingeBurnTest.write(Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "burn-test.svg")
