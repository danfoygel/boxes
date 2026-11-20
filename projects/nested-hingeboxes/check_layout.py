#!/usr/bin/env python3
"""Check a multi-sheet cut file: no two pieces closer than GAP, every piece at
least EDGE inside its sheet, and no two sheets' cut lines closer than
SHEET_GAP.  Works from the SVG alone (real outlines).

usage: check_layout.py SHEETS.svg [...]
"""
import re
import sys
import xml.etree.ElementTree as ET

from shapely import affinity
from shapely.geometry import Polygon
from shapely.strtree import STRtree
from svgpathtools import parse_path

GAP, EDGE, SHEET_GAP, TOL = 3.0, 5.0, 3.0, 0.05


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


def check(f):
    root = ET.parse(f).getroot()
    cuts = [g for g in root if g.get("id") == "sheet-cut-lines"][0]
    sheets = [outline(p.get("d")) for p in cuts]     # one closed rectangle per sheet
    pieces = []
    for g in root:
        if not g.tag.endswith("g") or g.get("id") == "sheet-cut-lines":
            continue
        for p in g:
            if p.tag.endswith("path") and p.get("class") == "outline":
                pieces.append(apply_transform(outline(p.get("d")), g.get("transform", "")))
    problems = []
    for i, a in enumerate(sheets):
        for j in range(i + 1, len(sheets)):
            if a.exterior.distance(sheets[j].exterior) < SHEET_GAP - TOL:
                problems.append(f"sheets {i + 1} and {j + 1} only "
                                f"{a.exterior.distance(sheets[j].exterior):.2f} mm apart")
    for i, poly in enumerate(pieces):
        s = next((s for s in range(len(sheets)) if sheets[s].contains(poly.centroid)), None)
        if s is None:
            problems.append(f"piece {i} is on no sheet")
        elif not sheets[s].buffer(-EDGE + TOL, join_style="mitre").contains(poly):
            problems.append(f"piece {i} not {EDGE} mm inside sheet {s + 1}")
    tree = STRtree(pieces)
    for i, poly in enumerate(pieces):
        for j in tree.query(poly.buffer(GAP - TOL)):
            if j > i and pieces[j].distance(poly) < GAP - TOL:
                problems.append(f"pieces {i} and {j} only {pieces[j].distance(poly):.2f} mm apart")
    print(f"{f}: {len(sheets)} sheets, {len(pieces)} pieces, {'OK' if not problems else f'{len(problems)} problems'}")
    for p in problems[:10]:
        print("   ", p)
    return not problems


if __name__ == "__main__":
    ok = all([check(f) for f in sys.argv[1:]])
    sys.exit(0 if ok else 1)
