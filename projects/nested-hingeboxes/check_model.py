#!/usr/bin/env python3
"""Check the 3D model (model.html) with the boxes nested and every lid closed:
no two pieces overlap, within a box or between boxes, and each box has at
least PLAY of room inside the next one out in every direction.

usage: check_model.py [--step MM] [PIECES.json]

The pieces come from model_pieces.js (run with node, which needs Playwright),
or from a JSON file it wrote.  Exits 1 if any check fails.

* Overlap: for every two pieces whose bounding boxes meet, sample points on a
  STEP grid inside both boxes and test each against the real pieces: the
  extruded outline (holes included) of each wall and hinge piece, and each pin's
  cylinder.  A point inside both is an overlap.  The grid is offset (OFF) so no
  point sits exactly on a face, where pieces meet with no gap (the model has no
  kerf).
* Room: the gap from each box's bounding box (knuckles included) to the nearest
  piece of the next box out in each direction: its walls, its floor and lid, and
  in y its hinge pieces.  Box and lid rest on the floor, so the gap below is 0
  and all of the play in height is above the lid.
* Controls, so a pass means something: box 1 is moved up and back by its
  measured gap less 0.1 mm, where it must still fit, and by the gap plus 0.5 mm,
  where it must overlap box 2.
"""
import argparse
import itertools
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import Polygon

HERE = Path(__file__).resolve().parent
PLAY = 2.0      # mm, the room each box has inside the next (README section 2)
OFF = 0.0137    # mm, grid offset
TOL = 0.005


class Piece:
    """A piece placed by `matrix` (4 x 4): inside(p) tests world points p (n x 3)."""

    def __init__(self, label, box, matrix):
        self.label, self.box = label, box
        self.m = np.array(matrix).reshape(4, 4).T     # three.js arrays are column-major
        self.inv = np.linalg.inv(self.m)

    def local(self, p):
        return p @ self.inv[:3, :3].T + self.inv[:3, 3]

    def bounds(self, corners):
        w = corners @ self.m[:3, :3].T + self.m[:3, 3]
        self.lo, self.hi = w.min(0), w.max(0)

    def moved(self, d):
        m = self.m.copy()
        m[:3, 3] += d
        return type(self)(self.label, self.box, m.T.reshape(-1), *self.args)


class Extrusion(Piece):
    """An outline with holes, extruded t along its local z."""

    def __init__(self, label, box, matrix, outline, holes, t):
        super().__init__(label, box, matrix)
        self.args, self.t = (outline, holes, t), t
        self.poly = shapely.make_valid(Polygon(outline, holes))
        shapely.prepare(self.poly)
        self.bounds(np.array([(x, y, z) for x, y in outline for z in (0, t)]))

    def inside(self, p):
        q = self.local(p)
        ok = (q[:, 2] > 0) & (q[:, 2] < self.t)
        ok[ok] = shapely.contains_xy(self.poly, q[ok, 0], q[ok, 1])
        return ok


class Pin(Piece):
    """A cylinder of radius r along its local y, centred."""

    def __init__(self, label, box, matrix, r, length):
        super().__init__(label, box, matrix)
        self.args, self.r, self.length = (r, length), r, length
        self.bounds(np.array([(x, y, z) for x in (-r, r) for y in (-length / 2, length / 2) for z in (-r, r)]))

    def inside(self, p):
        q = self.local(p)
        return (np.abs(q[:, 1]) < self.length / 2) & (q[:, 0] ** 2 + q[:, 2] ** 2 < self.r ** 2)


def load(data):
    pieces = []
    for i, b in enumerate(data["boxes"]):
        n = f"box {i + 1}"
        pieces += [Extrusion(f"{n} {p['group']} {p['name']}", i, p["matrix"], p["outline"], p["holes"], b["t"])
                   for p in b["pieces"]]
        pieces += [Extrusion(f"{n} hinge piece {k + 1} ({h['group']})", i, h["matrix"],
                             b["hinge"]["outline"], b["hinge"]["holes"], b["t"])
                   for k, h in enumerate(b["hinges"])]
        pieces += [Pin(f"{n} pin {k + 1}", i, p["matrix"], p["r"], p["length"]) for k, p in enumerate(b["pins"])]
    return pieces


def grid(lo, hi, step):
    axes = [np.arange(np.ceil((a - OFF) / step), np.floor((b - OFF) / step) + 1) * step + OFF for a, b in zip(lo, hi)]
    return np.stack(np.meshgrid(*axes, indexing="ij"), -1).reshape(-1, 3)


def overlaps(pieces, step):
    """[(label, label, points inside both)] and the number of pairs checked."""
    found, pairs = [], 0
    for a, b in itertools.combinations(pieces, 2):
        lo, hi = np.maximum(a.lo, b.lo), np.minimum(a.hi, b.hi)
        if np.any(hi <= lo):
            continue
        pairs += 1
        p = grid(lo, hi, step)
        n = int(np.count_nonzero(a.inside(p) & b.inside(p))) if len(p) else 0
        if n:
            found.append((a.label, b.label, n))
    return found, pairs


def gaps(inner, outer):
    """{(axis, -1 / +1): gap} from the inner box's bounding box to the outer box's
    pieces facing it on that side (by their centres); negative where they overlap."""
    lo, hi = np.min([p.lo for p in inner], 0), np.max([p.hi for p in inner], 0)
    mid = (lo + hi) / 2
    out = {}
    for ax in range(3):
        rest = [a for a in range(3) if a != ax]
        facing = [p for p in outer if all(p.lo[a] < hi[a] and p.hi[a] > lo[a] for a in rest)]
        out[ax, -1] = min(lo[ax] - p.hi[ax] for p in facing if (p.lo[ax] + p.hi[ax]) / 2 < mid[ax])
        out[ax, 1] = min(p.lo[ax] - hi[ax] for p in facing if (p.lo[ax] + p.hi[ax]) / 2 > mid[ax])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--step", type=float, default=0.25, help="grid step in mm (default 0.25)")
    ap.add_argument("pieces", nargs="?", help="JSON from model_pieces.js (default: run it)")
    args = ap.parse_args()
    if args.pieces:
        data = json.loads(Path(args.pieces).read_text())
    else:
        data = json.loads(subprocess.run(["node", str(HERE / "model_pieces.js")], check=True,
                                         capture_output=True, text=True).stdout)
    pieces = load(data)
    ok = True

    found, pairs = overlaps(pieces, args.step)
    same = sum(a.split()[1] == b.split()[1] for a, b, _ in found)
    print(f"{len(pieces)} pieces, {pairs} pairs checked at {args.step} mm: "
          f"{same} overlaps within a box, {len(found) - same} between boxes")
    for a, b, n in found:
        print(f"  {a} / {b}: {n} points")
    if found:
        print("FAILED (room and controls not measured: pieces overlap)")
        sys.exit(1)

    boxes = [[p for p in pieces if p.box == i] for i in range(len(data["boxes"]))]
    for i in range(len(boxes) - 1):
        g = gaps(boxes[i], boxes[i + 1])
        room = [g[a, -1] + g[a, 1] for a in range(3)]
        print(f"box {i + 1} in box {i + 2}: room " + ", ".join(
            f"{'xyz'[a]} {g[a, -1]:.2f} + {g[a, 1]:.2f} = {room[a]:.2f}" for a in range(3)) + " mm")
        if min(room) < PLAY - TOL:
            print(f"  less than {PLAY} mm")
            ok = False

    g = gaps(boxes[0], boxes[1])
    for ax, name in ((2, "up"), (1, "back")):
        for d, overlap in ((g[ax, 1] - 0.1, False), (g[ax, 1] + 0.5, True)):
            v = np.zeros(3)
            v[ax] = d
            n = len(overlaps([p.moved(v) for p in boxes[0]] + boxes[1], args.step)[0])
            good = (n > 0) == overlap
            print(f"control: box 1 moved {name} {d:.2f} mm: {n} overlapping pairs "
                  f"({'as expected' if good else 'WRONG'})")
            ok &= good

    print("OK" if ok else "FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
