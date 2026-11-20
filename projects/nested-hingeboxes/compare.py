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
BLACK = "rgb(0,0,0)"            # piece outline in the box SVGs
HINGE_CUT = "rgb(0,0,255)"      # hinge pieces' cut colour in the cut files


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
        hinges += sum(el.get("class") == "outline" and el.get("stroke") == HINGE_CUT
                      for el in paths)
        for el in paths:           # outlines add, holes take away; engraving doesn't count
            if el.get("class") in ("outline", "hole"):
                a = path_area(el.get("d"))
                area += a if el.get("class") == "outline" else -a
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
        # one closed rectangle per sheet: (x0, x1, y0, y1) each
        cuts = [parse_path(p.get("d")).bbox()
                for p in [g for g in root if g.get("id") == "sheet-cut-lines"][0]]
        x0, x1, y0, y1 = cuts[0]
        cols, rows_ = len({round(c[0]) for c in cuts}), len({round(c[2]) for c in cuts})
        rows.append((len(cuts), x1 - x0, y1 - y0, cols, rows_, TW, TH, area, hinges))
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
