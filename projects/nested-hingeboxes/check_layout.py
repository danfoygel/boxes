#!/usr/bin/env python3
"""Check a multi-sheet cut file: no two pieces closer than GAP, every piece at
least EDGE inside its sheet.  Works from the SVG alone (real outlines).

usage: check_layout.py SHEETS.svg [...]
"""
import re
import sys
import xml.etree.ElementTree as ET

from shapely import affinity
from shapely.geometry import Polygon, box
from shapely.strtree import STRtree
from svgpathtools import parse_path

GAP, EDGE, TOL = 3.0, 5.0, 0.05


def apply_transform(poly, t):
    # SVG applies the right-most transform first
    for op, args in reversed(re.findall(r"(translate|rotate)\(([^)]*)\)", t)):
        v = [float(a) for a in re.split(r"[ ,]+", args.strip())]
        if op == "translate":
            poly = affinity.translate(poly, v[0], v[1] if len(v) > 1 else 0)
        else:
            poly = affinity.rotate(poly, v[0], origin=(0, 0))
    return poly


def outline(d):
    pts = []
    for seg in parse_path(d):
        n = 1 if seg.__class__.__name__ == "Line" else 8
        pts += [seg.point(i / n) for i in range(n)]
    return Polygon([(z.real, z.imag) for z in pts]).buffer(0)


def sheets(root):
    """Each sheet's cut rectangle (x0, y0, x1, y1), from its path "M x0 y0 H x1 V y1 H x0 Z"."""
    return [tuple(float(v) for v in re.match(r"M ([\d.]+) ([\d.]+) H ([\d.]+) V ([\d.]+)", p.get("d")).groups())
            for p in root if p.get("class") == "sheet"]


def check(f):
    root = ET.parse(f).getroot()
    rects = sheets(root)
    pieces = []
    for g in root:
        if not g.tag.endswith("}g"):
            continue
        for p in g:
            if p.tag.endswith("path") and p.get("class") == "outline":
                pieces.append(apply_transform(outline(p.get("d")), g.get("transform", "")))
    problems = []
    for i, poly in enumerate(pieces):
        c = poly.centroid
        s = next((k for k, (x0, y0, x1, y1) in enumerate(rects) if x0 <= c.x <= x1 and y0 <= c.y <= y1), None)
        if s is None:
            problems.append(f"piece {i} not on any sheet")
            continue
        x0, y0, x1, y1 = rects[s]
        if not box(x0 + EDGE - TOL, y0 + EDGE - TOL, x1 - EDGE + TOL, y1 - EDGE + TOL).contains(poly):
            problems.append(f"piece {i} not {EDGE} mm inside sheet {s + 1}")
    tree = STRtree(pieces)
    for i, poly in enumerate(pieces):
        for j in tree.query(poly.buffer(GAP - TOL)):
            if j > i and pieces[j].distance(poly) < GAP - TOL:
                problems.append(f"pieces {i} and {j} only {pieces[j].distance(poly):.2f} mm apart")
    print(f"{f}: {len(pieces)} pieces, {'OK' if not problems else f'{len(problems)} problems'}")
    for p in problems[:10]:
        print("   ", p)
    return not problems


if __name__ == "__main__":
    ok = all([check(f) for f in sys.argv[1:]])
    sys.exit(0 if ok else 1)
