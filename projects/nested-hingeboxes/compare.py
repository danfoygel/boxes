#!/usr/bin/env python3
"""Print a comparison table of the generated cut sheets.

usage: compare.py   (run after generate.sh; reads boxes/*.svg and sheets/*/*.svg)

Utilisation here = real area of the cut pieces (outlines minus holes, from the
box SVGs) / total sheet area, so clustered and split layouts compare directly.
"""
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from shapely.geometry import Polygon
from svgpathtools import parse_path

HERE = Path(__file__).resolve().parent


def path_area(d):
    pts = []
    for seg in parse_path(d):
        n = 1 if seg.__class__.__name__ == "Line" else 16
        pts += [seg.point(i / n) for i in range(n)]
    return Polygon([(p.real, p.imag) for p in pts]).area


def piece_area():
    total = 0.0
    for f in sorted((HERE / "boxes").glob("box*.svg")):
        for el in ET.parse(f).iter():
            if el.tag.endswith("path"):
                a = path_area(el.get("d"))
                total += a if el.get("stroke") == "rgb(0,0,0)" else -a
    return total


def sheet_info(f):
    root = ET.parse(f).getroot()
    TW, TH = float(root.get("width")[:-2]), float(root.get("height")[:-2])
    d = [g for g in root if g.get("id") == "sheet-cut-lines"][0][0].get("d")
    # d = outer border "M 0 0 H .. V .. H 0 Z", then "M x 0 V .." per inner column line
    # and "M 0 y H .." per inner row line
    cols = len(re.findall(r"M [\d.]+ 0 V", d)) + 1
    rows = len(re.findall(r"M 0 [\d.]+ H", d))   # also matches the border's "M 0 0 H"
    return cols * rows, TW / cols, TH / rows, cols, rows, TW, TH


def inch(v):
    return f"{v / 25.4:.2f}"


def main():
    area = piece_area()
    rows = []
    cs = ET.parse(HERE / "cutsheet.svg").getroot()
    W, H = float(cs.get("width")[:-2]), float(cs.get("height")[:-2])
    rows.append(("single sheet", 1, W, H, 1, 1, W, H))
    for kind in ("clustered", "split"):
        for f in sorted((HERE / "sheets" / kind).glob("sheets*.svg"),
                        key=lambda p: int(re.findall(r"\d+", p.name)[0])):
            n, w, h, c, r, tw, th = sheet_info(f)
            rows.append((kind, n, w, h, c, r, tw, th))
    best = min(n * w * h for _, n, w, h, *_ in rows)
    print(f"Real piece area: {area / 1e6:.4f} m2\n")
    print("| Hinge pieces | Sheets | Sheet (mm) | Sheet (in) | Grid | Overall (mm) | Overall (in) "
          "| Material (m²) | vs best | Utilization |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for kind, n, w, h, c, r, tw, th in rows:
        a = n * w * h
        print(f"| {kind} | {n} | {w:.0f} × {h:.0f} | {inch(w)} × {inch(h)} | {c} × {r} "
              f"| {tw:.0f} × {th:.0f} | {inch(tw)} × {inch(th)} | {a / 1e6:.3f} "
              f"| {(a / best - 1) * 100:+.1f}% | {area / a:.1%} |")


if __name__ == "__main__":
    sys.exit(main())
