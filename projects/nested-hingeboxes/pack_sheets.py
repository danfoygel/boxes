#!/usr/bin/env python3
"""Pack the parts of several boxes.py SVGs onto N equal-sized sheets that sit
side by side in a grid on one big panel, with cut lines between the sheets.

usage: pack_sheets.py [--split-hinges] N OUT.svg BOX1.svg [BOX2.svg ...]

* Every part stays at least EDGE mm inside its sheet's cut line (the frame
  that protects the parts when the sheets are stacked) and GAP mm from other
  parts.  Parts may be rotated by 90 degrees.
* The search tries sheet widths in 2 mm steps and binary-searches the smallest
  sheet height that the packer (rectpack, several algorithms and sort orders)
  can fill; the smallest sheet area wins.  This is a heuristic: the best found,
  not a proven optimum.
* The grid (cols x rows) is the factorisation of N whose overall panel is
  closest to square.  Neighbouring sheets share one cut line.  The sheet cut
  lines come last in the file so they are cut after the parts.
* By default a group holding several loose pieces (the hinge pieces of a
  HingeBox) is packed as one cluster.  --split-hinges packs each of those
  pieces on its own; they are left unlabelled since they are identical for
  all boxes of the same thickness.
* Labels are red (boxes.py annotation colour, not meant to be cut): "Box N" on
  each part and "Sheet N" in each sheet's top-left frame.
* Utilisation = sum of part bounding-box areas / total sheet area.
"""
import argparse
import copy
import itertools
import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import rectpack

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from boxes.svgmerge import SvgMerge, SVG_NS  # noqa: E402

EDGE = 5.0   # min distance part -> sheet cut line
GAP = 3.0    # min distance part -> part
BLACK = "rgb(0,0,0)"

ALGOS = [rectpack.MaxRectsBssf, rectpack.MaxRectsBaf, rectpack.MaxRectsBl, rectpack.MaxRectsBlsf,
         rectpack.SkylineMwfl, rectpack.SkylineBl, rectpack.GuillotineBssfSas]
SORTS = [rectpack.SORT_AREA, rectpack.SORT_LSIDE, rectpack.SORT_SSIDE, rectpack.SORT_PERI,
         rectpack.SORT_DIFF]


def bbox_of(el):
    tmp = ET.Element("g")
    tmp.append(el)
    return SvgMerge.get_bbox_of_group(tmp)


def load_parts(files, split_hinges):
    parts = []
    for n, f in enumerate(files, 1):
        groups, _ = SvgMerge.parse_svg_groups(f)
        for g in groups:
            outlines = [c for c in g if c.get("stroke") == BLACK]
            if not split_hinges or len(outlines) <= 1:
                x0, y0, x1, y1 = SvgMerge.get_bbox_of_group(g)
                parts.append(dict(g=g, box=n, bbox=(x0, y0, x1, y1), w=x1 - x0, h=y1 - y0))
                continue
            # A group of several loose pieces: one part per outline, each taking
            # the inner cuts (holes) whose centre lies inside its bbox; drop text.
            others = [(c, bbox_of(c)) for c in g if c.get("stroke") not in (None, BLACK)]
            for o in outlines:
                x0, y0, x1, y1 = bbox_of(o)
                ng = ET.Element(g.tag, dict(g.attrib))
                ng.append(o)
                for c, (a0, b0, a1, b1) in others:
                    if x0 <= (a0 + a1) / 2 <= x1 and y0 <= (b0 + b1) / 2 <= y1:
                        ng.append(c)
                parts.append(dict(g=ng, box=None, bbox=(x0, y0, x1, y1), w=x1 - x0, h=y1 - y0))
    return parts


def try_pack(parts, n_sheets, W, H):
    iw, ih = W - 2 * EDGE + GAP, H - 2 * EDGE + GAP   # usable size incl. one GAP of padding
    for algo, sort in itertools.product(ALGOS, SORTS):
        pk = rectpack.newPacker(rotation=True, pack_algo=algo, sort_algo=sort,
                                bin_algo=rectpack.PackingBin.Global)
        for i, p in enumerate(parts):
            pk.add_rect(p["w"] + GAP, p["h"] + GAP, i)
        pk.add_bin(iw, ih, count=n_sheets)
        pk.pack()
        rl = pk.rect_list()
        if len(rl) == len(parts):
            return rl
    return None


def find_best(parts, n_sheets):
    need_short = max(min(p["w"], p["h"]) for p in parts) + 2 * EDGE
    need_long = max(max(p["w"], p["h"]) for p in parts) + 2 * EDGE
    lb_area = sum((p["w"] + GAP) * (p["h"] + GAP) for p in parts) / n_sheets

    best = None
    for W in [x * 2.0 for x in range(int(need_short // 2), int(need_long * 2.2 // 2))]:
        if W * W * 3 < lb_area:      # keep aspect within 1:3
            continue
        lo = max(need_short, lb_area / W * 0.9)
        if W < need_long:
            lo = max(lo, need_long)
        hi = max(lo, W * 3)
        if best and lo * W >= best[0]:
            continue
        if try_pack(parts, n_sheets, W, hi) is None:
            continue
        while hi - lo > 1:           # binary search the height (1 mm)
            mid = (lo + hi) / 2
            if try_pack(parts, n_sheets, W, mid):
                hi = mid
            else:
                lo = mid
        H = math.ceil(hi)
        rl = try_pack(parts, n_sheets, W, H)
        if rl and (best is None or W * H < best[0]):
            best = (W * H, W, H, rl)
    return best[1:]


def write_svg(out, parts, n_sheets, W, H, rl):
    grids = [(c, n_sheets // c) for c in range(1, n_sheets + 1) if n_sheets % c == 0]
    cols, rows = min(grids, key=lambda g: abs(math.log((g[0] * W) / (g[1] * H))))
    TW, TH = cols * W, rows * H

    svg = ET.Element(f"{{{SVG_NS}}}svg", {"width": f"{TW:.1f}mm", "height": f"{TH:.1f}mm",
                                         "viewBox": f"0 0 {TW:.1f} {TH:.1f}"})
    for b, x, y, w, h, i in rl:
        p = parts[i]
        x0, y0, x1, y1 = p["bbox"]
        x += (b % cols) * W + EDGE
        y += (b // cols) * H + EDGE
        rotated = abs(w - (p["w"] + GAP)) > 0.01
        if rotated:
            t = f"translate({x + p['h']:.3f},{y:.3f}) rotate(90) translate({-x0:.3f},{-y0:.3f})"
        else:
            t = f"translate({x - x0:.3f},{y - y0:.3f})"
        ng = ET.SubElement(svg, f"{{{SVG_NS}}}g", {"transform": t, "style": p["g"].attrib.get("style", "")})
        for c in p["g"]:
            ng.append(copy.deepcopy(c))
        if p["box"] is None:
            continue
        lbl = ET.SubElement(ng, f"{{{SVG_NS}}}text", {
            "x": f"{(x0 + x1) / 2:.2f}", "y": f"{(y0 + y1) / 2:.2f}", "font-size": "5",
            "font-family": "sans-serif", "fill": "rgb(255,0,0)", "text-anchor": "middle",
            "dominant-baseline": "middle"})
        lbl.text = f"Box {p['box']}"
    for b in range(n_sheets):        # sheet numbers in the frame margin
        t = ET.SubElement(svg, f"{{{SVG_NS}}}text", {
            "x": f"{(b % cols) * W + EDGE:.2f}", "y": f"{(b // cols) * H + EDGE / 2:.2f}",
            "font-size": "3", "font-family": "sans-serif", "fill": "rgb(255,0,0)",
            "dominant-baseline": "middle"})
        t.text = f"Sheet {b + 1}"
    # sheet cut lines last, shared between neighbours
    d = [f"M 0 0 H {TW} V {TH} H 0 Z"]
    d += [f"M {c * W} 0 V {TH}" for c in range(1, cols)]
    d += [f"M 0 {r * H} H {TW}" for r in range(1, rows)]
    ET.SubElement(svg, f"{{{SVG_NS}}}g", {"id": "sheet-cut-lines"}).append(
        ET.Element(f"{{{SVG_NS}}}path", {"d": " ".join(d), "stroke": BLACK, "fill": "none",
                                          "stroke-width": "0.2"}))
    ET.ElementTree(svg).write(out, encoding="utf-8", xml_declaration=True)
    return cols, rows, TW, TH


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--split-hinges", action="store_true",
                    help="pack each hinge piece separately instead of as one cluster per box")
    ap.add_argument("n_sheets", type=int)
    ap.add_argument("out")
    ap.add_argument("files", nargs="+")
    a = ap.parse_args()

    parts = load_parts(a.files, a.split_hinges)
    W, H, rl = find_best(parts, a.n_sheets)
    cols, rows, TW, TH = write_svg(a.out, parts, a.n_sheets, W, H, rl)
    util = sum(p["w"] * p["h"] for p in parts) / (a.n_sheets * W * H)
    print(json.dumps(dict(parts=len(parts), N=a.n_sheets, sheet=[W, H], grid=[cols, rows],
                          overall=[TW, TH], util=round(util, 4))))


if __name__ == "__main__":
    main()
