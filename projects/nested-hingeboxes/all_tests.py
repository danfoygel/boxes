#!/usr/bin/env python3
"""All three test sheets on one: the hinge burn test (burn_test.py), the finger
joint burn test (finger_test.py) and the engraving test (engrave_test.py), for one
laser job.

usage: all_tests.py [OUT.svg]      (default: all-tests.svg next to this script)

Each test is drawn by its own script, exactly as in its own file, and moved into
place (LAYOUT): the engraving test top left, the hinge test beside it and the
finger test below.  Only the paths' coordinates change: they are shifted by whole
sheets, with no transforms, so laser software sees plain paths as in the other
files.
"""
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from svgpathtools import parse_path

from burn_test import HERE, HingeBurnTest
from engrave_test import EngraveTest
from finger_test import FingerBurnTest

SVG = "{http://www.w3.org/2000/svg}"
GAP = 5.0                 # mm between the tests
PAD = 10.0                # mm round the whole sheet, as boxes.py leaves
# rows of (class, id prefix), top row first, each row left to right: the engraving
# and hinge tests side by side, the finger test below
LAYOUT = [[(EngraveTest, "engrave"), (HingeBurnTest, "hinge")], [(FingerBurnTest, "finger")]]
NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


def shift(d, dx, dy):
    """Path data `d` moved by dx, dy.  boxes.py writes only absolute M, L, C, H, V
    and Z, with x, y pairs after M, L and C."""
    out = []
    for cmd, args in re.findall(r"([A-Za-z])([^A-Za-z]*)", d):
        if cmd not in "MLCHVZ":
            raise ValueError(f"can't shift a {cmd} command")
        nums = [float(n) for n in NUMBER.findall(args)]
        if cmd == "H":
            nums = [n + dx for n in nums]
        elif cmd == "V":
            nums = [n + dy for n in nums]
        else:
            nums = [n + (dy if i % 2 else dx) for i, n in enumerate(nums)]
        out.append(" ".join([cmd] + [f"{n:.3f}" for n in nums]))
    return " ".join(out)


def bounds(root):
    """(x0, y0, x1, y1) of all the paths in an SVG root."""
    boxes = [parse_path(p.get("d")).bbox() for p in root.iter(f"{SVG}path")]
    return (min(b[0] for b in boxes), min(b[2] for b in boxes),
            max(b[1] for b in boxes), max(b[3] for b in boxes))


def main(out):
    # each test's SVG, its bounds and where its top-left corner goes
    sheets = []
    y = PAD
    for row in LAYOUT:
        x, row_h = PAD, 0
        for cls, prefix in row:
            tree, box = cls.svg(out.name)
            root = tree.getroot()
            b = bounds(root)
            sheets.append((root, b, prefix, x, y, box.summary()))
            x += b[2] - b[0] + GAP
            row_h = max(row_h, b[3] - b[1])
        y += row_h + GAP
    w = max(x + (b[2] - b[0]) for _, b, _, x, _, _ in sheets) + PAD
    h = y - GAP + PAD

    svg = ET.Element(f"{SVG}svg", {"width": f"{w:.2f}mm", "height": f"{h:.2f}mm",
                                   "viewBox": f"0.0 0.0 {w:.2f} {h:.2f}"})
    ET.SubElement(svg, f"{SVG}title").text = "All tests"
    for root, (x0, y0, _, _), prefix, x, y, _ in sheets:
        dx, dy = round(x - x0, 3), round(y - y0, 3)   # keeps boxes.py's 0.001 mm grid
        for g in root.findall(f"{SVG}g"):
            g.set("id", f"{prefix}-{g.get('id')}")
            for p in g.iter(f"{SVG}path"):
                p.set("d", shift(p.get("d"), dx, dy))
            svg.append(g)
    ET.ElementTree(svg).write(out, encoding="utf-8", xml_declaration=True)
    print(f"{out}: {w - 2 * PAD:.0f} x {h - 2 * PAD:.0f} mm")
    for _, (x0, y0, x1, y1), prefix, *_, summary in sheets:
        print(f"  {prefix} {x1 - x0:.0f} x {y1 - y0:.0f} mm: {summary}")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "all-tests.svg")
