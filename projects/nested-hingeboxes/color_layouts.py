#!/usr/bin/env python3
"""Make colour-coded layout views of the multi-sheet cut files.

usage: color_layouts.py SHEETS.svg [...]     (writes layouts/<same name>.svg)

Each piece is filled with a tint of its box's colour and outlined in the full
colour; hinge pieces, which are shared by all boxes, are grey.  A legend strip
is added above the sheets.  These files are for reading the layout, not for
cutting: use the files in sheets/ for that.

Colours: blue, orange, aqua (the first three slots of the data-viz reference
palette) plus plum.  Checked with the palette validator for all pairs (pieces
of every box sit next to each other): worst colour-blind separation ΔE 9.2,
worst normal-vision ΔE 20.4.  Every piece also keeps its "Box N" label, so
colour is never the only cue.
"""
import copy
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)
HERE = Path(__file__).resolve().parent
BLACK = "rgb(0,0,0)"
BOX_SIZES = {1: "160 × 80 × 80", 2: "168 × 95 × 88", 3: "176 × 110 × 96", 4: "184 × 125 × 104"}
COLORS = {1: "#2a78d6", 2: "#eb6834", 3: "#1baf7a", 4: "#b0367c", None: "#8a8984"}
TINT = 0.45          # share of the colour in the fill (rest is white)
INK = "#1f1f1e"      # text colour
LEGEND = 16.0        # mm added above the sheets for the legend


def tint(hex_color, share):
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    mix = [round(255 - (255 - c) * share) for c in (r, g, b)]
    return "#" + "".join(f"{c:02x}" for c in mix)


def q(tag):
    return f"{{{SVG_NS}}}{tag}"


def convert(src, dst):
    tree = ET.parse(src)
    root = tree.getroot()
    W, H = float(root.get("width")[:-2]), float(root.get("height")[:-2])
    out = ET.Element(q("svg"), {"width": f"{W:.1f}mm", "height": f"{H + LEGEND:.1f}mm",
                                "viewBox": f"0 0 {W:.1f} {H + LEGEND:.1f}"})
    ET.SubElement(out, q("rect"), {"x": "0", "y": "0", "width": f"{W:.1f}",
                                   "height": f"{H + LEGEND:.1f}", "fill": "#ffffff"})
    body = ET.SubElement(out, q("g"), {"transform": f"translate(0,{LEGEND})"})
    counts = {}
    for el in root:
        el = copy.deepcopy(el)
        if el.tag == q("g") and el.get("id") == "sheet-cut-lines":
            for p in el.iter(q("path")):
                p.set("stroke", "#9a9994")
                p.set("stroke-width", "0.4")
            body.append(el)
            continue
        if el.tag == q("text"):                     # "Sheet N"
            el.set("fill", INK)
            body.append(el)
            continue
        if el.tag != q("g"):
            continue
        label = next((t for t in el if t.tag == q("text") and (t.text or "").startswith("Box ")),
                     None)
        box = int(label.text.split()[1]) if label is not None else None
        counts[box] = counts.get(box, 0) + 1
        color = COLORS[box]
        for p in el:
            if p.tag != q("path"):
                continue
            if p.get("stroke") == BLACK:            # outline
                p.set("fill", tint(color, TINT))
            else:                                   # holes
                p.set("fill", "#ffffff")
            p.set("stroke", color)
            p.set("stroke-width", "0.5")
        if label is not None:
            label.set("fill", INK)
            label.set("font-weight", "bold")
        body.append(el)

    # legend: swatch + name for each box and for the hinge pieces
    x = 5.0
    ET.SubElement(out, q("text"), {"x": f"{x}", "y": "6", "font-size": "4.5",
                                   "font-family": "sans-serif", "font-weight": "bold",
                                   "fill": INK}).text = f"{Path(src).stem}: pieces by box"
    for key in (1, 2, 3, 4, None):
        if key not in counts:
            continue
        name = (f"Box {key} ({BOX_SIZES[key]} mm, {counts[key]} pieces)" if key
                else f"Hinge pieces, any box ({counts[None]})")
        ET.SubElement(out, q("rect"), {"x": f"{x}", "y": "9", "width": "5", "height": "4",
                                       "rx": "0.8", "fill": tint(COLORS[key], TINT),
                                       "stroke": COLORS[key], "stroke-width": "0.5"})
        t = ET.SubElement(out, q("text"), {"x": f"{x + 6.5}", "y": "12.3", "font-size": "3.5",
                                           "font-family": "sans-serif", "fill": INK})
        t.text = name
        x += 6.5 + len(name) * 1.85 + 6
    ET.ElementTree(out).write(dst, encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    (HERE / "layouts").mkdir(exist_ok=True)
    for f in sys.argv[1:]:
        dst = HERE / "layouts" / Path(f).name
        convert(f, dst)
        print(dst.relative_to(HERE))
