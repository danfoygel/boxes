#!/usr/bin/env python3
"""Print a comparison table of the generated cut sheets.

usage: compare.py   (run after generate.sh; reads boxes/*.svg and sheets/*.svg)

Utilisation here = real area of the cut pieces in that file (outlines minus
holes, spare hinge pieces included) / total sheet area.
"""
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from shapely.geometry import Polygon
from svgpathtools import parse_path

HERE = Path(__file__).resolve().parent
BLACK, BLUE = "rgb(0,0,0)", "rgb(0,0,255)"


def path_area(d):
    pts = []
    for seg in parse_path(d):
        n = 1 if seg.__class__.__name__ == "Line" else 16
        pts += [seg.point(i / n) for i in range(n)]
    return Polygon([(p.real, p.imag) for p in pts]).area


def file_info(f):
    """Piece area and number of hinge pieces in one cut file."""
    root = ET.parse(f).getroot()
    area, hinges = 0.0, 0
    for g in root:
        if not g.tag.endswith("g") or g.get("id") == "sheet-cut-lines":
            continue
        paths = [el for el in g.iter() if el.tag.endswith("path")]
        black = sum(el.get("stroke") == BLACK for el in paths)
        has_text = any(el.tag.endswith("text") for el in g)
        if black > 1:              # a cluster of hinge pieces
            hinges += black
        elif black == 1 and not has_text:
            hinges += 1            # a single (unlabelled) hinge piece
        for el in paths:           # outlines add, holes (blue) take away; engraving doesn't count
            if el.get("stroke") in (BLACK, BLUE):
                a = path_area(el.get("d"))
                area += a if el.get("stroke") == BLACK else -a
    return root, area, hinges


def needed_hinges():
    """Hinge pieces the boxes need: outlines in the box SVGs' multi-piece groups."""
    n = 0
    for f in (HERE / "boxes").glob("box*.svg"):
        for g in ET.parse(f).getroot():
            black = sum(el.get("stroke") == BLACK for el in g if el.tag.endswith("path"))
            if black > 1:
                n += black
    return n


def mm(root, key):
    return float(root.get(key)[:-2])


def inch(v):
    return f"{v / 25.4:.2f}"


def main():
    rows = []
    for f in sorted((HERE / "sheets").glob("sheets*.svg"),
                    key=lambda p: int(re.findall(r"\d+", p.name)[0])):
        root, area, hinges = file_info(f)
        TW, TH = mm(root, "width"), mm(root, "height")
        d = [g for g in root if g.get("id") == "sheet-cut-lines"][0][0].get("d")
        # d = outer border "M 0 0 H .. V .. H 0 Z", then "M x 0 V .." per inner column
        # line and "M 0 y H .." per inner row line
        cols = len(re.findall(r"M [\d.]+ 0 V", d)) + 1
        rows_ = len(re.findall(r"M 0 [\d.]+ H", d))   # also matches the border's "M 0 0 H"
        rows.append((cols * rows_, TW / cols, TH / rows_, cols, rows_, TW, TH, area, hinges))
    best = min(n * w * h for n, w, h, *_ in rows)
    needed = needed_hinges()
    print("| Sheets | Sheet (mm) | Sheet (in) | Grid | Overall (mm) | Overall (in) "
          "| Material (m²) | vs best | Hinge pieces | Utilization |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for n, w, h, c, r, tw, th, area, hinges in rows:
        a = n * w * h
        spare = hinges - needed
        hp = f"{hinges} (+{spare} spare)" if spare else f"{hinges}"
        print(f"| {n} | {w:.0f} × {h:.0f} | {inch(w)} × {inch(h)} | {c} × {r} "
              f"| {tw:.0f} × {th:.0f} | {inch(tw)} × {inch(th)} | {a / 1e6:.3f} "
              f"| {(a / best - 1) * 100:+.1f}% | {hp} | {area / a:.1%} |")


if __name__ == "__main__":
    sys.exit(main())
