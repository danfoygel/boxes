#!/usr/bin/env python3
"""Pack the parts of several boxes.py SVGs onto one sheet (units: mm).

usage: pack_single.py OUT.svg BOX1.svg [BOX2.svg ...]

Each part (an SVG group in the boxes.py output) is packed as one rectangle,
rotation by 90 degrees allowed.  The sheet width is chosen to minimise the
sheet area while keeping the sheet no taller than it is wide.  Every part gets
a red "Box N" label (red = annotation in boxes.py, not meant to be cut).
"""
import copy
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import rectpack

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from boxes.svgmerge import SvgMerge, SVG_NS  # noqa: E402

GAP = 3.0  # mm between parts and around the sheet edge


def main(out, files):
    parts = []
    for n, f in enumerate(files, 1):
        groups, _ = SvgMerge.parse_svg_groups(f)
        for g in groups:
            x0, y0, x1, y1 = SvgMerge.get_bbox_of_group(g)
            parts.append(dict(g=g, box=n, bbox=(x0, y0, x1, y1), w=x1 - x0, h=y1 - y0))
    area = sum((p["w"] + GAP) * (p["h"] + GAP) for p in parts)

    def pack(width):
        pk = rectpack.newPacker(rotation=True, pack_algo=rectpack.MaxRectsBssf)
        for i, p in enumerate(parts):
            pk.add_rect(p["w"] + GAP, p["h"] + GAP, i)
        pk.add_bin(width, 10000)
        pk.pack()
        rects = pk.rect_list()
        if len(rects) != len(parts):
            return None
        return max(y + h for _, x, y, w, h, _ in rects), rects

    best = None
    for width in range(400, 1201, 10):
        r = pack(width)
        if r is None:
            continue
        height, rects = r
        if height > width:
            continue
        if best is None or width * height < best[0] - 1:
            best = (width * height, width, height, rects)
    _, W, H, rects = best
    W, H = W + GAP, H + GAP
    print(f"parts={len(parts)} part area={area / 1e6:.2f}m2 "
          f"sheet={W:.0f}x{H:.0f}mm fill={area / (W * H):.0%}")

    svg = ET.Element(f"{{{SVG_NS}}}svg", {"width": f"{W:.1f}mm", "height": f"{H:.1f}mm",
                                         "viewBox": f"0 0 {W:.1f} {H:.1f}"})
    for _, x, y, w, h, i in rects:
        p = parts[i]
        x0, y0, x1, y1 = p["bbox"]
        rotated = abs(w - (p["w"] + GAP)) > 0.01
        x += GAP
        y += GAP
        if rotated:
            t = f"translate({x + p['h']:.3f},{y:.3f}) rotate(90) translate({-x0:.3f},{-y0:.3f})"
        else:
            t = f"translate({x - x0:.3f},{y - y0:.3f})"
        ng = ET.SubElement(svg, f"{{{SVG_NS}}}g", {"transform": t, "style": p["g"].attrib.get("style", "")})
        for c in p["g"]:
            ng.append(copy.deepcopy(c))
        lbl = ET.SubElement(ng, f"{{{SVG_NS}}}text", {
            "x": f"{(x0 + x1) / 2:.2f}", "y": f"{(y0 + y1) / 2:.2f}",
            "font-size": "5", "font-family": "sans-serif", "fill": "rgb(255,0,0)",
            "text-anchor": "middle", "dominant-baseline": "middle"})
        lbl.text = f"Box {p['box']}"
    ET.ElementTree(svg).write(out, encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2:])
