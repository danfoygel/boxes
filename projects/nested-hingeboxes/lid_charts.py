#!/usr/bin/env python3
"""Line art for the lid top of box 3 ("Problematic Data"): Anscombe's quartet.

usage: lid_charts.py [OUT.svg]      (default art/anscombes-quartet.svg)

The SVG is the lid top's inner face, 170 x 104 mm (box 3's x by y panel less
t all round), with the art as filled outlines in boxes.py's etching colour
(green).  A red rectangle marks the face's edge; it is unfilled, so
engraving.lid_art leaves it out.  engraving.LID_ART puts the art on box 3's
lid, where it is scaled to leave LID_PAD clear: drawn just inside that, so
it goes on at very nearly full size.

The charts, in Anscombe's (1973) order, I and II across the top, III and IV
below: four datasets of 11 points with the same means, variances, correlation
and least-squares line, y = 3 + x / 2, and nothing else alike.  Each chart
has the same axes and its own fit line, worked out from its points.
"""
import math
import sys
from pathlib import Path

from shapely import affinity
from shapely.geometry import LineString
from shapely.ops import unary_union

import engraving

W, H = 170.0, 104.0        # mm, inner face of box 3's lid top (176 x 110 less 2t)
XMAX, YMAX = 20, 14        # chart units: each chart's axes run 0-20 across and 0-14 up
U, UY = 3.51, 2.725        # mm per chart unit across and up: the four charts' ink fills 154 x 88 mm
TICKS_X, TICKS_Y = (5, 10, 15), (4, 8, 12)
GAP_X, GAP_Y = 10.0, 8.0   # mm between one chart's axes and the next
TICK = 1.5                 # mm, length of the axis ticks
AXIS = 0.7                 # mm, line widths
DATA = 0.7
FIT = 0.5
THIN = 0.6
DOT = 1.1                  # mm, from a scatter point's centre to the tips of its X
GREEN, RED = "rgb(0,255,0)", "rgb(255,0,0)"

# Anscombe, "Graphs in Statistical Analysis", The American Statistician 27 (1973).
X123 = [10, 8, 13, 9, 11, 14, 6, 4, 12, 7, 5]
QUARTET = [
    list(zip(X123, [8.04, 6.95, 7.58, 8.81, 8.33, 9.96, 7.24, 4.26, 10.84, 4.82, 5.68])),
    list(zip(X123, [9.14, 8.14, 8.74, 8.77, 9.26, 8.10, 6.13, 3.10, 9.13, 7.26, 4.74])),
    list(zip(X123, [7.46, 6.77, 12.74, 7.11, 7.81, 8.84, 6.08, 5.39, 8.15, 6.42, 5.73])),
    list(zip([8] * 7 + [19] + [8] * 3, [6.58, 5.76, 7.71, 8.84, 8.47, 7.04, 5.25, 12.50, 5.56, 7.91, 6.89])),
]


# Charts are drawn in chart units with y up, the axes' corner at (0, 0).
# Positions scale by U and UY; line widths and dot sizes are in mm and don't.
def mm(pts):
    return [(U * x, UY * y) for x, y in pts]


def stroke(pts, w=DATA):
    return LineString(mm(pts)).buffer(w / 2, quad_segs=8, cap_style="round", join_style="round")


def dot(x, y, r=DOT / math.sqrt(2)):
    """A scatter point, drawn as an X."""
    cx, cy = U * x, UY * y
    return unary_union([LineString([(cx - r, cy - r * s), (cx + r, cy + r * s)]).buffer(DATA / 2, quad_segs=8)
                        for s in (1, -1)])


def axes():
    parts = [stroke([(0, YMAX), (0, 0), (XMAX, 0)], AXIS)]
    parts += [stroke([(0, y), (-TICK / U, y)], THIN) for y in TICKS_Y]
    parts += [stroke([(x, 0), (x, -TICK / UY)], THIN) for x in TICKS_X]
    return parts


def fit_line(pts):
    """The ordinary least-squares line through `pts`, across the chart."""
    mx, my = (sum(c) / len(pts) for c in zip(*pts))
    slope = sum((x - mx) * (y - my) for x, y in pts) / sum((x - mx) ** 2 for x, _ in pts)
    return stroke([(x, my + slope * (x - mx)) for x in (1, XMAX - 0.5)], FIT)


def scatter(pts):
    return axes() + [fit_line(pts)] + [dot(x, y) for x, y in pts]


def art():
    """The four charts in a 2 x 2 grid as one shape, in mm on the face, y down:
    axes GAP_X and GAP_Y apart, centred on the face by ink."""
    step_x, step_y = XMAX * U + TICK + GAP_X, YMAX * UY + TICK + GAP_Y
    g = unary_union([affinity.translate(unary_union(scatter(pts)), (i % 2) * step_x, -(i // 2) * step_y)
                     for i, pts in enumerate(QUARTET)])
    g = affinity.scale(g, 1, -1, origin=(0, 0)).simplify(0.02)   # well under the laser's resolution
    x0, y0, x1, y1 = g.bounds
    g = affinity.translate(g, (W - x0 - x1) / 2, (H - y0 - y1) / 2)
    x0, y0, x1, y1 = g.bounds
    assert min(x0, y0) >= engraving.LID_PAD - 0.05, f"art closer than LID_PAD to the edge, would be shrunk: {g.bounds}"
    return g


def write_svg(g, path):
    Path(path).write_text(
        f'<?xml version="1.0" encoding="utf-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:g}mm" height="{H:g}mm" viewBox="0 0 {W:g} {H:g}">\n'
        f'<title>Box 3 lid top: Problematic Data</title>\n'
        f'<rect x="0" y="0" width="{W:g}" height="{H:g}" fill="none" stroke="{RED}" stroke-width="0.2"/>\n'
        f'<path class="engraving" d="{engraving._path(g)}" fill="{GREEN}" stroke="{GREEN}" '
        f'stroke-width="0.01" fill-rule="evenodd"/>\n</svg>\n')


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "art/anscombes-quartet.svg"
    g = art()
    write_svg(g, out)
    x0, y0, x1, y1 = g.bounds
    print(f"{out}: {len(QUARTET)} charts, ink {x1 - x0:.1f} x {y1 - y0:.1f} mm, "
          f"clear {x0:.1f} mm left/right, {y0:.1f} mm top/bottom")
