#!/usr/bin/env python3
"""Pack the parts of several boxes.py SVGs onto N equal-sized sheets that sit
side by side in a grid on one big panel, with cut lines between the sheets,
then fill the leftover space with as many spare hinge pieces as fit.

usage: pack_sheets.py [--sheet WxH] N OUT.svg BOX1.svg [BOX2.svg ...]

* Every part stays at least EDGE mm inside its sheet's cut line (the frame
  that protects the parts when the sheets are stacked) and GAP mm from other
  parts.
* Sheet size: the search tries sheet widths in 2 mm steps and binary-searches
  the smallest sheet height into which the rectangle packer (rectpack, several
  algorithms and sort orders, 90 degree rotation) fits every part's bounding
  box; the smallest sheet area wins.  --sheet skips the search.  This is a
  heuristic: the best found, not a proven optimum.
* A group holding several loose pieces (the hinge pieces of a HingeBox) is
  split so each piece is handled on its own.  Hinge pieces are left
  unlabelled: they are identical for all boxes of the same thickness.
* Hinge pieces (the required ones and spares), with the sheet size fixed:
  - Strategy A: rectangle-pack everything plus as many spare hinge pieces as
    the packer can fit (gallop + binary search on the count, then a few probes
    above it), then shape-fill.
  - Strategy B: rectangle-pack only the box pieces (every packer setting that
    fits), then place all hinge pieces by shape-filling.
  - Shape filling drops hinge pieces into the free space by their real
    outline, in 4 rotations, top-left first, at RES mm steps.  A grid
    correlation proposes positions; each is checked exactly against the real
    outlines (>= GAP between pieces, >= EDGE from the sheet edge).
  - The variant with the most hinge pieces wins.
* The grid (cols x rows) is the factorisation of N whose overall panel is
  closest to square.  Neighbouring sheets share one cut line.  The sheet cut
  lines come last in the file so they are cut after the parts.
* Labels are red (boxes.py annotation colour, not meant to be cut): "Box N" on
  each box part and "Sheet N" in each sheet's top-left frame.
"""
import argparse
import copy
import itertools
import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import rectpack
from PIL import Image, ImageDraw
from shapely import affinity
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely.prepared import prep
from svgpathtools import parse_path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from boxes.svgmerge import SvgMerge, SVG_NS  # noqa: E402

EDGE = 5.0    # min distance part -> sheet cut line
GAP = 3.0     # min distance part -> part
RES = 0.25    # shape-filling grid (mm)
BLACK = "rgb(0,0,0)"

ALGOS = [rectpack.MaxRectsBssf, rectpack.MaxRectsBaf, rectpack.MaxRectsBl, rectpack.MaxRectsBlsf,
         rectpack.SkylineMwfl, rectpack.SkylineBl, rectpack.GuillotineBssfSas]
SORTS = [rectpack.SORT_AREA, rectpack.SORT_LSIDE, rectpack.SORT_SSIDE, rectpack.SORT_PERI,
         rectpack.SORT_DIFF]


# --------------------------------------------------------------------- parts

def bbox_of(el):
    tmp = ET.Element("g")
    tmp.append(el)
    return SvgMerge.get_bbox_of_group(tmp)


def load_parts(files):
    parts = []
    for n, f in enumerate(files, 1):
        groups, _ = SvgMerge.parse_svg_groups(f)
        for g in groups:
            outlines = [c for c in g if c.get("stroke") == BLACK]
            if len(outlines) <= 1:
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
    for p in parts:
        d = next(c for c in p["g"] if c.get("stroke") == BLACK).get("d")
        pts = []
        for seg in parse_path(d):
            n = 1 if seg.__class__.__name__ == "Line" else 8
            pts += [seg.point(i / n) for i in range(n)]
        # outline moved so its bbox corner is at 0,0
        p["poly"] = affinity.translate(Polygon([(z.real, z.imag) for z in pts]).buffer(0),
                                       -p["bbox"][0], -p["bbox"][1])
    return parts


def svg_transform(part, angle, px, py):
    """Transform that rotates `part` by angle (degrees) and puts its bbox corner at px, py.
    Also returns its outline in sheet coordinates."""
    x0, y0 = part["bbox"][:2]
    rot = affinity.rotate(part["poly"], angle, origin=(0, 0))
    mx, my = rot.bounds[:2]
    t = f"translate({px - mx:.3f},{py - my:.3f}) rotate({angle}) translate({-x0:.3f},{-y0:.3f})"
    return t, affinity.translate(rot, px - mx, py - my)


# --------------------------------------------------------- rectangle packing

def packs(parts, n_sheets, W, H):
    """Yield rect lists for every packer setting that fits all parts."""
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
            yield rl


def try_pack(parts, n_sheets, W, H):
    return next(packs(parts, n_sheets, W, H), None)


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
        if try_pack(parts, n_sheets, W, H) and (best is None or W * H < best[0]):
            best = (W * H, W, H)
    return best[1:]


def rect_spares(parts, n_sheets, W, H):
    """Largest k so that parts + k extra hinge pieces still rectangle-pack."""
    hinge = next(p for p in parts if p["box"] is None)

    def attempt(k):
        ps = parts + [hinge] * k
        return ps, try_pack(ps, n_sheets, W, H)

    best = (parts, try_pack(parts, n_sheets, W, H))
    k, lo = 1, 0
    while True:                       # gallop: 1, 2, 4, ... until a failure
        ps, r = attempt(k)
        if r is None:
            break
        best, lo = (ps, r), k
        k *= 2
    hi = k                            # lo packs, hi does not
    while True:
        while hi - lo > 1:
            mid = (lo + hi) // 2
            ps, r = attempt(mid)
            if r:
                lo, best = mid, (ps, r)
            else:
                hi = mid
        for k in range(hi + 1, hi + 4):   # probe a little above the failure
            ps, r = attempt(k)
            if r:
                lo, best, hi = k, (ps, r), k + 1
                break
        else:
            return best


def rect_placements(parts, rl):
    placed = []
    for b, x, y, w, h, i in rl:
        p = parts[i]
        angle = 90 if abs(w - (p["w"] + GAP)) > 0.01 else 0
        t, poly = svg_transform(p, angle, x + EDGE, y + EDGE)
        placed.append((b, p, t, poly))
    return placed


# ------------------------------------------------------------- shape filling

class Filler:
    """Places copies of one piece into the free space of each sheet.

    A RES mm occupancy grid and an FFT correlation propose candidate positions
    (top-left first, all 4 rotations); each candidate is then checked exactly
    against the real outlines (>= GAP from every piece, >= EDGE from the sheet
    edge) and the first one that passes is taken.
    """

    MAX_CHECKS = 3000     # exact checks per placement before giving up on a sheet

    def __init__(self, piece, W, H):
        self.piece, self.W, self.H = piece, W, H
        self.gw = int((W - 2 * EDGE) / RES)
        self.gh = int((H - 2 * EDGE) / RES)
        self.kernels = []
        for angle in (0, 90, 180, 270):
            rot = affinity.rotate(piece["poly"], angle, origin=(0, 0))
            rot = affinity.translate(rot, -rot.bounds[0], -rot.bounds[1])
            kw = int(math.ceil(rot.bounds[2] / RES)) + 1
            kh = int(math.ceil(rot.bounds[3] / RES)) + 1
            # slightly shrunk so the grid proposes optimistically; the exact check decides
            k = self._draw(np.zeros((kh, kw), bool), rot.buffer(-RES / 2), 0, 0)
            self.kernels.append((angle, k))
        self.shape = (self.gh + max(k.shape[0] for _, k in self.kernels),
                      self.gw + max(k.shape[1] for _, k in self.kernels))
        self.kfft = [(a, k.shape, np.fft.rfft2(k[::-1, ::-1].astype(float), self.shape))
                     for a, k in self.kernels]

    @staticmethod
    def _draw(arr, poly, ox, oy):
        """OR the polygon into arr; (ox, oy) is the mm position of pixel (0, 0)."""
        img = Image.new("1", (arr.shape[1], arr.shape[0]), 0)
        draw = ImageDraw.Draw(img)
        for g in getattr(poly, "geoms", [poly]):
            if not g.is_empty:
                draw.polygon([((x + ox) / RES, (y + oy) / RES) for x, y in g.exterior.coords],
                             fill=1)
        return arr | np.array(img, bool)

    def fits(self, cand, keepout):
        x0, y0, x1, y1 = cand.bounds
        if x0 < EDGE or y0 < EDGE or x1 > self.W - EDGE or y1 > self.H - EDGE:
            return False
        return not keepout.intersects(cand)

    def fill(self, polys):
        """Add pieces to one sheet holding `polys`; returns [(transform, poly)]."""
        occ = np.zeros((self.gh, self.gw), bool)
        zones = []
        for poly in polys:
            zones.append(poly.buffer(GAP + 0.02))
            occ = self._draw(occ, poly.buffer(GAP - RES / 2), -EDGE, -EDGE)
        out = []
        while True:
            keepout = prep(unary_union(zones))
            offt = np.fft.rfft2(occ.astype(float), self.shape)
            cands = []
            for angle, (kh, kw), kf in self.kfft:
                if kh > self.gh or kw > self.gw:
                    continue
                corr = np.fft.irfft2(offt * kf, self.shape)
                r, c = np.nonzero(corr[kh - 1:self.gh, kw - 1:self.gw] < 0.5)
                cands.append(np.stack([r, c, np.full_like(r, angle)], axis=1))
            cands = np.concatenate(cands) if cands else np.zeros((0, 3), int)
            cands = cands[np.lexsort((cands[:, 2], cands[:, 1], cands[:, 0]))]
            found = None
            for r0, c0, angle in cands[:self.MAX_CHECKS]:
                t, cand = svg_transform(self.piece, int(angle), EDGE + c0 * RES, EDGE + r0 * RES)
                if self.fits(cand, keepout):
                    found = (t, cand)
                    break
            if found is None:
                return out
            out.append(found)
            zones.append(found[1].buffer(GAP + 0.02))
            occ = self._draw(occ, found[1].buffer(GAP - RES / 2), -EDGE, -EDGE)


def shape_fill(filler, n_sheets, placed):
    """Fill every sheet of a placement list; returns the extended list."""
    placed = list(placed)
    for b in range(n_sheets):
        polys = [poly for s, _, _, poly in placed if s == b]
        for t, poly in filler.fill(polys):
            placed.append((b, filler.piece, t, poly))
    return placed


def best_layout(parts, n_sheets, W, H, log):
    """Try the rectangle layouts below and shape-fill each; the most hinge pieces wins.

    The rectangle packer is a heuristic whose choices depend on the small pieces
    it is given, so the box pieces are packed together with k hinge-piece
    rectangles for several k (every 10th k, the required count and the largest
    count that still packs), with every packer setting that fits.  For each
    layout, A keeps the rectangle-placed hinge pieces and shape-fills the rest;
    B drops them and places all hinge pieces by shape-filling.  A layout must
    end up with at least the required number of hinge pieces.
    """
    hinge = next(p for p in parts if p["box"] is None)
    panels = [p for p in parts if p["box"] is not None]
    needed = len(parts) - len(panels)
    filler = Filler(hinge, W, H)
    count = lambda pl: sum(p["box"] is None for _, p, _, _ in pl)   # noqa: E731

    k_max = len(rect_spares(parts, n_sheets, W, H)[0]) - len(panels)
    best, seen, tried = None, set(), 0
    for k in sorted(set(range(0, k_max + 1, 10)) | {needed, k_max}):
        if k > k_max:
            continue
        ps = panels + [hinge] * k
        for rl in packs(ps, n_sheets, W, H):
            key = tuple(sorted((b, round(x), round(y), round(w), ps[i]["box"] or 0)
                               for b, x, y, w, h, i in rl))
            if key in seen:
                continue
            seen.add(key)
            rect = rect_placements(ps, rl)
            variants = [("A", rect), ("B", [q for q in rect if q[1]["box"] is not None])]
            for name, start in variants[: 2 if k else 1]:
                pl = shape_fill(filler, n_sheets, start)
                tried += 1
                if count(pl) >= needed and (best is None or count(pl) > best[1]):
                    best = (f"{name}, k={k}", count(pl), pl)
    log(f"{tried} layouts tried (rectangle packing fits at most {k_max} hinge pieces), "
        f"best {best[1]} hinge pieces ({best[0]})")
    return best


# -------------------------------------------------------------------- output

def write_svg(out, n_sheets, W, H, placed):
    grids = [(c, n_sheets // c) for c in range(1, n_sheets + 1) if n_sheets % c == 0]
    cols, rows = min(grids, key=lambda g: abs(math.log((g[0] * W) / (g[1] * H))))
    TW, TH = cols * W, rows * H

    svg = ET.Element(f"{{{SVG_NS}}}svg", {"width": f"{TW:.1f}mm", "height": f"{TH:.1f}mm",
                                         "viewBox": f"0 0 {TW:.1f} {TH:.1f}"})
    for b, p, t, _ in placed:
        x0, y0, x1, y1 = p["bbox"]
        t = f"translate({(b % cols) * W:.3f},{(b // cols) * H:.3f}) {t}"
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
    ap.add_argument("--sheet", help="sheet size WxH in mm (skips the size search)")
    ap.add_argument("n_sheets", type=int)
    ap.add_argument("out")
    ap.add_argument("files", nargs="+")
    a = ap.parse_args()

    def log(msg):
        print(f"[{a.n_sheets} sheets] {msg}", file=sys.stderr, flush=True)

    parts = load_parts(a.files)
    needed = sum(p["box"] is None for p in parts)
    if a.sheet:
        W, H = (float(v) for v in a.sheet.lower().split("x"))
    else:
        W, H = find_best(parts, a.n_sheets)
    log(f"sheet {W:g} x {H:g} mm")
    strategy, hinges, placed = best_layout(parts, a.n_sheets, W, H, log)
    cols, rows, TW, TH = write_svg(a.out, a.n_sheets, W, H, placed)
    print(json.dumps(dict(N=a.n_sheets, sheet=[W, H], grid=[cols, rows], overall=[TW, TH],
                          hinge_pieces=hinges, spare_hinge_pieces=hinges - needed,
                          strategy=strategy)))


if __name__ == "__main__":
    main()
