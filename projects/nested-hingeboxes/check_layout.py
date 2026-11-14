#!/usr/bin/env python3
"""Check a multi-sheet cut file: no two pieces closer than GAP, every piece at
least EDGE inside its sheet.  Works from the SVG alone (real outlines).

usage: check_layout.py SHEETS.svg [...]
"""
import math
import re
import sys
import xml.etree.ElementTree as ET

from shapely import affinity
from shapely.geometry import Polygon, box
from shapely.strtree import STRtree
from svgpathtools import parse_path

GAP, EDGE, TOL = 3.0, 5.0, 0.05
BLACK = "rgb(0,0,0)"


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
    cut = [g for g in root if g.get("id") == "sheet-cut-lines"][0][0].get("d")
    TW, TH = float(root.get("width")[:-2]), float(root.get("height")[:-2])
    cols = len(re.findall(r"M [\d.]+ 0 V", cut)) + 1
    rows = len(re.findall(r"M 0 [\d.]+ H", cut))
    W, H = TW / cols, TH / rows
    pieces = []
    for g in root:
        if not g.tag.endswith("g") or g.get("id") == "sheet-cut-lines":
            continue
        for p in g:
            if p.tag.endswith("path") and p.get("stroke") == BLACK:
                pieces.append(apply_transform(outline(p.get("d")), g.get("transform", "")))
    problems = []
    for i, poly in enumerate(pieces):
        cx, cy = poly.centroid.x, poly.centroid.y
        sx, sy = math.floor(cx / W), math.floor(cy / H)
        inner = box(sx * W + EDGE - TOL, sy * H + EDGE - TOL,
                    (sx + 1) * W - EDGE + TOL, (sy + 1) * H - EDGE + TOL)
        if not inner.contains(poly):
            problems.append(f"piece {i} not {EDGE} mm inside sheet ({sx},{sy})")
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
