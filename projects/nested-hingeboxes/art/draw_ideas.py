#!/usr/bin/env python3
"""Draw art/ideas.svg, the lid artwork for box 4 ("Exuberant Ideas").

A brain with eight thought clouds fanned round it, each with a small picture of
something its owner loves doing: hiking, golf, skiing, sailing, biking, soccer,
chess and karaoke, with sparkles in the gaps.  No text.

Everything is built as shapely shapes in mm on a 160 x 100 canvas (y down) and
written out as black filled outlines, one path per piece, outline anticlockwise
and holes clockwise on screen, which is what engraving.lid_art expects.
Outlines are drawn at an even weight; inner detail is drawn with a brush that
tapers, so it reads as inked by hand.  The brain is in true side-view proportion with its
main grooves where they are on a real brain; the smaller folds are grown from
the notches in its outline and then into whatever room is left, from a fixed
random seed, so the drawing comes out the same every run.

generate.sh runs it, before it engraves the boxes.
"""
import math
import random
from pathlib import Path

import numpy as np
import shapely
from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box
from shapely.geometry.polygon import orient
from shapely.ops import nearest_points, unary_union

HERE = Path(__file__).resolve().parent
OUT = HERE / "ideas.svg"
W, H = 160.0, 100.0
BOLD = 1.2    # mm, outlines
LINE = 0.85   # mm, inner detail
FINE = 0.6    # mm, the smallest details

rng = random.Random(11)
ink = []


# --- drawing helpers ---------------------------------------------------------
def spline(pts, closed=False, n=12):
    """Catmull-Rom curve through pts."""
    ext = [pts[-1], *pts, pts[0], pts[1]] if closed else [pts[0], *pts, pts[-1]]
    out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1:i + 3]
        for k in range(n):
            t = k / n
            out.append(tuple(0.5 * (2 * p1[j] + (p2[j] - p0[j]) * t
                                    + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t
                                    + (3 * p1[j] - p0[j] - 3 * p2[j] + p3[j]) * t ** 3) for j in (0, 1)))
    out.append(pts[0] if closed else pts[-1])
    return out


def resample(pts, step=0.3):
    ls = LineString(pts)
    n = max(1, round(ls.length / step))
    return [ls.interpolate(ls.length * k / n).coords[0] for k in range(n + 1)]


def brush(pts, w, start=0.0, end=0.0, floor=0.18):
    """A line w mm wide that narrows to a point over the first `start` and the
    last `end` fraction of its length."""
    P = resample(pts)
    n = len(P) - 1

    def r(k):
        t, f = k / n, 1.0
        if start:
            f = min(f, t / start)
        if end:
            f = min(f, (1 - t) / end)
        return max(floor, w * math.sin(math.pi / 2 * max(0.0, min(1.0, f)))) / 2

    discs = [Point(p).buffer(r(k), quad_segs=6) for k, p in enumerate(P)]
    return unary_union([discs[k].union(discs[k + 1]).convex_hull for k in range(n)])


def stroke(geom, w):
    """A line (or the outline of a shape) drawn w mm wide, round ends."""
    if isinstance(geom, (list, tuple)):
        geom = LineString(geom)
    elif geom.geom_type == "Polygon":
        geom = geom.exterior
    return geom.buffer(w / 2, quad_segs=8)


def arc(cx, cy, r, a0, a1, n=24):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * k / n)),
             cy + r * math.sin(math.radians(a0 + (a1 - a0) * k / n))) for k in range(n + 1)]


def twinkle(cx, cy, r):
    """A four-pointed sparkle with curved sides."""
    pts = []
    for k in range(64):
        a = 2 * math.pi * k / 64
        c, s = math.cos(a), math.sin(a)
        rr = r / (abs(c) ** 0.5 + abs(s) ** 0.5) ** 2
        pts.append((cx + rr * c, cy + rr * s))
    return Polygon(pts)


def dot(cx, cy, r):
    return Point(cx, cy).buffer(r, quad_segs=16)


def ellipse(cx, cy, rx, ry, rot=0.0):
    e = affinity.scale(Point(0, 0).buffer(1, quad_segs=32), rx, ry, origin=(0, 0))
    return affinity.translate(affinity.rotate(e, rot, origin=(0, 0)), cx, cy)


# --- the brain -----------------------------------------------------------------
# A left side view in true proportion, drawn in a 100-unit frame (frontal pole at
# u = 0, occipital pole at u = 100, top at v = 0) and mapped onto the canvas.
# The cerebrum is long and low, highest just behind the middle, with a blunt
# frontal lobe, a narrower occipital lobe and, below the lateral fissure, the
# temporal lobe, whose tip sits in a notch under the frontal lobe.  The
# cerebellum tucks in under the back and the stem comes down between the two.
BRAIN_AT, BRAIN_SCALE = (45.0, 40.5), 0.7


def U(pts):
    return [(BRAIN_AT[0] + BRAIN_SCALE * u, BRAIN_AT[1] + BRAIN_SCALE * v) for u, v in pts]


BASE = U([(0, 36), (2, 24), (8, 13), (17, 5), (29, 1), (42, 0), (55, 0.5), (67, 3), (78, 8),
          (88, 15), (95, 24), (99, 33), (100, 41), (97, 47), (90, 51), (82, 54), (74, 58),
          (64, 61), (52, 62), (42, 61.5), (33, 58.5), (28.5, 54.5), (27, 50), (28.5, 46.5),
          (22, 45), (12, 44.5), (4, 41.5)])


def lobed(base, spacing=6.2):
    """The base outline bulged out a little between notches about `spacing` mm
    apart, like the rounded ends of the folds showing at the edge of a brain.
    The underside stays smoother.  Returns the outline and, for each notch, the
    point and the inward direction there."""
    loop = LineString(spline(base, closed=True, n=30))
    poly = Polygon(loop.coords)
    L = loop.length
    cuts, s = [], 0.0
    while s < L - spacing * 0.7:
        cuts.append(s)
        s += spacing * rng.uniform(0.75, 1.25)
    cuts.append(L)

    def normal(s):
        x, y = loop.interpolate(s % L).coords[0]
        x2, y2 = loop.interpolate((s + 0.2) % L).coords[0]
        nx, ny = -(y2 - y), x2 - x
        d = math.hypot(nx, ny)
        nx, ny = nx / d, ny / d
        if poly.contains(Point(x + nx * 0.3, y + ny * 0.3)):
            nx, ny = -nx, -ny
        return (x, y), (nx, ny)

    out, notch_pts = [], []
    for a, b in zip(cuts, cuts[1:]):
        (_, under) = normal((a + b) / 2)[1]
        amp = min(1.25, 0.18 * (b - a)) * (0.45 if under > 0.55 else 1.0)
        steps = max(4, int((b - a) / 0.25))
        for k in range(steps):
            (x, y), (nx, ny) = normal(a + (b - a) * k / steps)
            bump = amp * math.sin(math.pi * k / steps) ** 0.75
            out.append((x + bump * nx, y + bump * ny))
            if k == 0 and ny < 0.5:
                notch_pts.append(((x, y), (-nx, -ny)))
    return Polygon(out), notch_pts


CEREBRUM, NOTCH_PTS = lobed(BASE)
CEREBELLUM = Polygon(spline(U([(68, 60), (74, 55.5), (84, 53), (93, 53.5), (99, 58), (99.5, 65),
                               (95, 71.5), (86, 75), (77, 74), (70.5, 69.5)]), closed=True))
STEM = Polygon(spline(U([(58, 58), (56.5, 64), (57, 70), (59.5, 77), (61, 82.5), (64, 84.5), (66.5, 82),
                         (67, 75), (68.5, 66), (70, 59)]), closed=True))
BRAIN = unary_union([CEREBRUM, CEREBELLUM, STEM])

ink.append(stroke(CEREBRUM, BOLD))
ink.append(stroke(CEREBELLUM.exterior.difference(CEREBRUM), BOLD))
ink.append(stroke(STEM.exterior.difference(CEREBRUM.union(CEREBELLUM)), BOLD))
# the cerebellum's fine parallel folds, following its lower edge
for k, v in enumerate((60.5, 64.5, 68.5)):
    g = U([(70 + 2 * k, v + 1.5), (78, v - 0.5), (87, v - 1), (95, v + 0.5), (100, v + 3)])
    ink.append(brush(spline(g), FINE, 0.2, 0.2).intersection(CEREBELLUM.buffer(-0.5))
               .difference(CEREBRUM.buffer(0.6)))

# The landmark grooves where they are on a real brain: the lateral fissure and
# its two short branches, the central sulcus with the sulci either side of it,
# the frontal sulci running forward, the temporal sulci running along under
# the fissure, and the intraparietal sulcus running back.
LANDMARKS = [  # (points in the 100-unit frame, width, taper at start, taper at end)
    ([(28.5, 46.5), (36, 43.5), (45, 41.2), (54, 39.5), (63, 36.5), (69, 32), (71.5, 28)], 1.15, 0.0, 0.3),
    ([(33, 44.5), (31.5, 40), (32.5, 36)], LINE, 0.0, 0.5),
    ([(36.5, 43.8), (38, 39), (36.8, 35.5)], LINE, 0.0, 0.5),
    ([(53, 0.4), (51.5, 6), (53, 10), (49.5, 16), (50.5, 21), (47, 27), (46, 33)], 1.0, 0.0, 0.3),
    ([(42, 1.5), (40.5, 8), (41.5, 13), (39, 19)], LINE, 0.0, 0.4),
    ([(38.5, 23), (36.5, 28.5), (37, 33.5)], LINE, 0.25, 0.4),
    ([(63, 2.5), (60.5, 8.5), (61.5, 14), (58, 20), (57.5, 27)], LINE, 0.0, 0.35),
    ([(39.5, 13), (32, 12.5), (25, 14.5), (17, 14), (11, 17.5)], LINE, 0.25, 0.3),
    ([(37, 24.5), (29, 24), (21, 26.5), (13, 26.5), (6, 30)], LINE, 0.25, 0.3),
    ([(33.5, 53), (41, 50.5), (50, 48.5), (59, 46.5), (67, 43), (73, 38.5), (75, 34.5)], LINE, 0.3, 0.3),
    ([(42, 57), (51, 56), (60, 54.5), (68, 52.5)], LINE, 0.3, 0.4),
    ([(58, 21), (66, 20.5), (73, 22.5), (80, 26.5), (86, 28.5)], LINE, 0.3, 0.35),
    ([(80, 34), (87, 37.5), (92.5, 42.5)], LINE, 0.3, 0.4),
]
folds = []
for pts, w, t0, t1 in LANDMARKS:
    line = spline(U(pts))
    folds.append(LineString(line))
    ink.append(brush(line, w, t0, t1).intersection(CEREBRUM.buffer(-0.2)))

OUTLINE = CEREBRUM.exterior
INSIDE = CEREBRUM.buffer(-1.7)
CLEAR = 2.4   # mm between neighbouring folds


def grow(p, heading, length, others, curl=None, free=1.2):
    """A wandering fold from p, turning a little as it goes, stopped where it
    would come within CLEAR of another fold or run out of the brain."""
    a = rng.uniform(0.12, 0.26) * rng.choice((-1, 1))
    lam = rng.uniform(7, 12)
    ph = rng.uniform(0, 2 * math.pi)
    curl = rng.choice((-1, 1)) * rng.uniform(0.35, 0.6) if curl is None else curl
    pts, s, step = [p], 0.0, 0.35
    x, y = p
    while s < length:
        k = a * math.sin(2 * math.pi * s / lam + ph)
        if s > length - 2.2:
            k += curl          # finish with a hook
        heading += k * step
        x, y = x + step * math.cos(heading), y + step * math.sin(heading)
        s += step
        q = Point(x, y)
        if s > free and (not INSIDE.contains(q) or (others is not None and others.distance(q) < CLEAR)):
            break
        pts.append((x, y))
    return pts, s


# folds running in from each notch in the outline
for (x, y), (nx, ny) in NOTCH_PTS:
    if any(Point(x, y).distance(f) < 2.4 for f in folds):
        continue
    others = unary_union(folds).difference(Point(x, y).buffer(0.5))
    h = math.atan2(ny, nx) + rng.uniform(-0.35, 0.35)
    pts, s = grow((x, y), h, rng.uniform(4, 9), others, free=2.6)
    if s >= 3.0:
        folds.append(LineString(pts))
        ink.append(brush(pts, LINE, 0.0, 0.3))

# then short curled folds wherever there is still room
gx, gy = np.meshgrid(np.arange(44, 117, 0.8), np.arange(40, 87, 0.8))
grid = shapely.points(gx.ravel(), gy.ravel())
grid = grid[shapely.contains(INSIDE.buffer(-0.8), grid)]
for _ in range(80):
    taken = unary_union(folds + [OUTLINE])
    d = shapely.distance(grid, taken)
    i = int(np.argmax(d))
    if d[i] < 3.0:
        break
    seed = grid[i].coords[0]
    h = rng.uniform(0, 2 * math.pi)
    half1, _ = grow(seed, h, rng.uniform(2.5, 5.5), taken)
    half2, _ = grow(seed, h + math.pi, rng.uniform(2.5, 5.5), taken)
    pts = half2[::-1] + half1[1:]
    line = LineString(pts) if len(pts) > 1 else None
    if line is None or line.length < 3.0:
        grid = np.delete(grid, i)
        continue
    folds.append(line)
    ink.append(brush(pts, LINE, 0.18, 0.18))


# --- what the brain is thinking about ------------------------------------------------
# Eight small pictures, one per thought cloud.  Each is drawn about 11 x 8 mm,
# centred on the origin, then scaled to fill its cloud (see fit_in_cloud).
THIN = 0.5    # mm, the finest lines in the pictures


def ln(pts, w=0.7):
    return stroke(list(pts), w)


def poly(pts, r=0.0):
    """A polygon, its corners rounded by r."""
    p = Polygon(pts)
    return p.buffer(-r).buffer(r) if r else p


def rect(x0, y0, x1, y1, r=0.0):
    return poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], r)


def ring(cx, cy, r, w=0.7):
    return stroke(Point(cx, cy).buffer(r, quad_segs=24), w)


def wave(x0, x1, y, amp=0.35, lam=2.4, w=THIN):
    n = max(8, int((x1 - x0) / 0.2))
    return ln([(x0 + (x1 - x0) * k / n, y + amp * math.sin(2 * math.pi * (x1 - x0) * k / n / lam))
               for k in range(n + 1)], w)


def moved(geoms, dx, dy, rot=0.0, s=1.0):
    """geoms scaled by s and turned by rot degrees about the origin, then moved."""
    return [affinity.translate(affinity.rotate(affinity.scale(g, s, s, origin=(0, 0)), rot, origin=(0, 0)), dx, dy)
            for g in geoms]


def unit(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dx, dy)
    return dx / n, dy / n


def figure(head, limbs, w=0.8, hr=0.85):
    """A stick figure: a round head and limbs, each a list of points."""
    return [dot(*head, hr)] + [ln(j, w) for j in limbs]


def soccer_ball(cx, cy, r, w=0.7):
    """The middle pentagon, the five round it cut off by the edge, and the seams between."""
    out = [ring(cx, cy, r, w)]
    inner = Point(cx, cy).buffer(r - w / 2)
    pr = 0.36 * r
    out.append(Polygon([(cx + pr * math.cos(math.radians(-90 + 72 * k)),
                         cy + pr * math.sin(math.radians(-90 + 72 * k))) for k in range(5)]))
    for k in range(5):
        a = math.radians(-90 + 72 * k)
        u = (math.cos(a), math.sin(a))
        out.append(ln([(cx + pr * u[0], cy + pr * u[1]), (cx + 0.66 * r * u[0], cy + 0.66 * r * u[1])], THIN))
        oc = (cx + 0.98 * r * u[0], cy + 0.98 * r * u[1])
        out.append(Polygon([(oc[0] + 0.32 * r * math.cos(a + math.pi + 2 * math.pi * j / 5),
                             oc[1] + 0.32 * r * math.sin(a + math.pi + 2 * math.pi * j / 5))
                            for j in range(5)]).intersection(inner))
    return out


def golf():
    """A flag in the hole, the ball beside it on the green."""
    return [ln([(0, -4.6), (0, 2.6)], 0.55), poly([(0, -4.7), (4.2, -3.3), (0, -1.9)], 0.15),
            ellipse(0, 2.9, 1.6, 0.55), dot(-2.9, 2.0, 0.85), ln(arc(0, 11, 8.2, 243, 297), THIN)]


def skiing():
    """A skier in a crouch going down a slope, snow flying off the tails."""
    d = unit((-5, 0.2), (5, 4.2))                    # down the slope
    n = (d[1], -d[0])
    tail, tip = ((t * d[0] + 0.5 * n[0], t * d[1] + 0.5 * n[1]) for t in (-3.0, 3.2))
    u = unit(tail, tip)
    ski = ln(spline([tail, (tip[0] - 1.4 * u[0], tip[1] - 1.4 * u[1]),
                     (tip[0] - 0.4 * u[0] + 0.3 * n[0], tip[1] - 0.4 * u[1] + 0.3 * n[1]),
                     (tip[0] + 0.95 * n[0], tip[1] + 0.95 * n[1])]), 0.75)
    body = figure((1.4, -5.45), [[(0.1, -0.65), (1.3, -1.95), (-0.8, -2.65), (0.5, -4.55)],
                                 [(0.5, -4.35), (1.2, -3.25), (2.1, -3.35)]], 0.95, 0.95)
    hand, end = (2.1, -3.35), (-3.2, -1.85)          # the pole, back under the arm
    u = unit(hand, end)
    b = (end[0] - 0.8 * u[0], end[1] - 0.8 * u[1])
    grip = (hand[0] + 0.12 * (end[0] - hand[0]), hand[1] + 0.12 * (end[1] - hand[1]))
    pole = [ln([hand, end], 0.45), ln([hand, grip], 0.85),
            ln([(b[0] + 0.6 * u[1], b[1] - 0.6 * u[0]), (b[0] - 0.6 * u[1], b[1] + 0.6 * u[0])], 0.45)]
    snow = [dot(x, y, 0.6 - 0.1 * k) for k, (x, y) in enumerate(((-3.4, -1.6), (-4.4, -2.8), (-4.7, -4.2),
                                                                 (-4.3, -5.4)))]
    return [ski] + body + pole + [ln([(t * d[0], t * d[1]) for t in (-5.4, 5.4)], THIN)] + snow + [
        dot(-3.4, -3.0, 0.4), dot(-5.6, -3.4, 0.35)]


def sailing():
    """A sailboat, mainsail and jib, on the waves."""
    return [poly([(-0.45, -4.8), (-0.45, 1.4), (-4.4, 1.4), (-3.0, -1.2), (-1.5, -3.5)], 0.15),
            poly([(0.45, -3.8), (0.45, 1.4), (3.6, 1.4), (2.1, -0.9)], 0.15),
            poly([(-5.0, 2.0), (5.2, 2.0), (3.8, 3.6), (-3.6, 3.6)], 0.2), wave(-4.8, 4.8, 4.5)]


def biking():
    """A racing bike, its rider bent over the bars."""
    s = 0.92
    S = lambda x, y: (x * s, y * s)  # noqa: E731
    rh, fh, bb = S(-3.5, 1.5), S(3.6, 1.5), S(-0.5, 1.5)          # hubs, bottom bracket
    st, ht, hb = S(-1.4, -1.5), S(2.0, -1.5), S(2.3, -0.5)         # seat tube top, head tube
    out = [ring(*rh, 2.5 * s, 0.6), ring(*fh, 2.5 * s, 0.6), dot(*rh, 0.4 * s + 0.1), dot(*fh, 0.4 * s + 0.1)]
    for a, b in ((rh, bb), (rh, st), (bb, S(-1.6, -2.2)), (st, ht), (bb, hb), (ht, hb), (hb, fh),
                 (ht, S(1.85, -2.3))):
        out.append(ln([a, b], 0.6))
    out.append(stroke(spline([S(1.85, -2.3), S(2.9, -2.25), S(3.25, -1.85), S(3.0, -1.4)]), 0.6))   # drop bars
    out += [ellipse(*S(-1.75, -2.45), 1.0 * s, 0.33 * s + 0.05, -4), dot(*bb, 0.7 * s)]           # saddle, chainring
    return out + figure((1.9, -4.6), [[(-1.5, -2.6), (1.0, -3.8)], [(0.9, -3.6), (2.2, -2.9), (2.75, -2.1)],
                                      [(-1.4, -2.5), (0.5, -1.0), (-0.2, 2.0)]], 0.85, 0.8)


def pine(cx, base, h):
    out = [ln([(cx, base), (cx, base - 0.25 * h)], 0.6)]
    for t, w in ((0.2, 0.55), (0.45, 0.42), (0.68, 0.3)):
        y = base - t * h
        out.append(poly([(cx - w * h / 2, y), (cx + w * h / 2, y), (cx, y - 0.42 * h)], 0.1))
    return out


def hiking():
    """A hiker with a pack and a stick, next to a pine."""
    pack = affinity.rotate(rect(-2.1, -2.9, -0.5, 0.0, 0.45), 10, origin=(-1.3, -1.4))
    body = figure((1.1, -3.6), [[(0.6, -2.6), (0.0, 0.6)], [(0.0, 0.6), (1.0, 2.3), (1.4, 4.2), (2.2, 4.2)],
                                [(0.0, 0.6), (-0.7, 2.4), (-1.7, 4.0), (-1.1, 4.3)],
                                [(0.5, -2.0), (1.3, -0.8), (2.6, -1.4)]])
    return [pack] + body + [ln([(2.7, -2.3), (3.3, 4.4)], 0.45)] + pine(6.2, 4.4, 7.4) + [
        ln([(-2.6, 4.7), (8.6, 4.7)], THIN)]


def soccer():
    """A studded boot that has just kicked the ball."""
    upper = poly([(-4.2, -1.8), (-2.0, -2.2), (0.0, -1.6), (2.6, -0.6), (4.4, 0.4), (4.6, 1.6), (-4.4, 1.6),
                  (-4.6, 0.0)], 0.5)
    studs = [poly([(x - 0.4, 2.0), (x + 0.4, 2.0), (x + 0.25, 3.0), (x - 0.25, 3.0)], 0.1)
             for x in (-3.6, -2.2, 0.6, 2.2, 3.7)]
    laces = [ln([(-0.4 + 0.75 * k, -1.7 + 0.32 * k), (-0.7 + 0.75 * k, -0.6 + 0.32 * k)], 0.4) for k in range(4)]
    boot = moved([stroke(upper, 0.7), ln([(-4.6, 1.9), (4.8, 1.9)], 0.8), *studs, *laces], -4.0, 1.8, -25, 0.6)
    return boot + soccer_ball(2.8, -0.6, 2.8) + [ln([(-0.4, -2.9), (-0.9, -3.8)], 0.45),
                                                 ln([(-0.7, -1.9), (-1.6, -2.4)], 0.45)]


def chess_base(w=2.8):
    """What every piece stands on: a plinth and a flared foot."""
    return unary_union([rect(-w, 3.3, w, 4.4, 0.3), poly([(-w + 0.5, 3.4), (w - 0.5, 3.4), (1.5, 2.3), (-1.5, 2.3)])])


def chess():
    """A rook and a knight."""
    top = rect(-2.5, -4.4, 2.5, -2.0, 0.15).difference(
        unary_union([rect(-1.3, -4.8, -0.5, -3.5), rect(0.5, -4.8, 1.3, -3.5)]))
    rook = unary_union([chess_base(2.9), poly([(-1.8, 2.5), (1.8, 2.5), (1.5, -2.0), (-1.5, -2.0)]), top])
    rook = rook.difference(ln([(-2.6, -1.85), (2.6, -1.85)], 0.35))
    head = poly([(2.3, 2.4), (2.6, -0.2), (2.0, -2.6), (1.0, -4.4), (0.4, -3.5), (-0.8, -3.3), (-2.2, -2.0),
                 (-3.3, -0.5), (-3.4, 0.5), (-2.6, 1.0), (-1.6, 0.5), (-0.6, 0.3), (-1.4, 1.4), (-1.8, 2.5)], 0.35)
    knight = unary_union([chess_base(), head]).difference(dot(-0.9, -1.9, 0.42))
    return moved([rook], -3.1, 0) + moved([knight], 3.2, 0)


def note(cx, cy, s=1.0, flag=True):
    """An eighth note s times full size, its head at (cx, cy)."""
    x = cx + 0.82 * s                                # the stem
    out = [ellipse(cx, cy, 0.95 * s, 0.68 * s, -22), ln([(x, cy - 0.2 * s), (x, cy - 4.2 * s)], 0.45)]
    if flag:
        out.append(brush(spline([(x, cy - 4.2 * s), (cx + 1.9 * s, cy - 3.1 * s), (cx + 2.0 * s, cy - 2.0 * s)]),
                         0.6, 0.0, 0.5))
    return out


def karaoke():
    """A handheld mic, tipped, with a pair of notes and a single one."""
    head = Point(0, -2.7).buffer(2.0)
    mesh = unary_union([ln([(-3, -2.7 + k), (3, -2.7 + k + 1.2)], 0.3) for k in (-1.5, -0.5, 0.5)] +
                       [ln([(-3, -2.7 + k + 1.2), (3, -2.7 + k)], 0.3) for k in (-1.5, -0.5, 0.5)])
    mic = [unary_union([stroke(head, 0.7), mesh.intersection(head.buffer(-0.3))]),
           rect(-1.6, -1.05, 1.6, -0.35, 0.15), poly([(-1.15, -0.2), (1.15, -0.2), (0.6, 5.0), (-0.6, 5.0)], 0.3)]
    s, cx, cy = 0.62, 1.6, -1.4                      # the beamed pair
    pair = note(cx, cy, s, False) + note(cx + 2.6 * s, cy - 0.6 * s, s, False) + [
        poly([(cx + 0.6 * s, cy - 4.4 * s), (cx + 3.65 * s, cy - 5.0 * s), (cx + 3.65 * s, cy - 4.0 * s),
              (cx + 0.6 * s, cy - 3.4 * s)])]
    return moved(mic, -3.4, 0.6, 25) + pair + note(4.4, 2.8, 0.8)


# --- the thought clouds --------------------------------------------------------------
# Eight clouds fanned round the brain, each GAP mm from it at its nearest, and
# spread so that neighbours are evenly spaced.  The two along the bottom are
# mirror images of each other across the middle of the brain instead, since the
# brain isn't symmetric.  A cloud on the left is drawn mirrored.
CS = 0.9
CLOUD = unary_union([dot(CS * dx, CS * dy, CS * r) for dx, dy, r in (
    (-8, 1.5, 4.8), (-3.5, -3, 5.4), (3, -3.5, 5.2), (8.2, 0.5, 4.6), (5, 5, 4.4),
    (-1.5, 5.2, 4.6), (-7, 5.5, 3.6), (0, 1, 6))])
ROOM = CLOUD.buffer(-BOLD / 2 - 0.9)                 # inside the outline, with a margin
GAP = 18.0
O = (80, 66)                                         # the clouds are placed along rays from here
MID_X = 80.0
CLOUDS = [  # (angle from O, picture, shrink); the last is the bottom pair: left, right
    (-170.0, hiking, 1.0), (-141.9, golf, 1.0), (-110.3, skiing, 1.0), (-72.4, sailing, 1.0),
    (-39.3, biking, 1.0), (-10.0, soccer, 1.0)]
BOTTOM = (162.5, 22.0, 20.0, chess, 0.85, karaoke)   # angle, centre x, trail angle, left, shrink, right


def cloud_at(c, mirror):
    return affinity.translate(affinity.scale(CLOUD, -1 if mirror else 1, 1, origin=(0, 0)), *c)


def cloud_out(angle):
    """The point along the ray from O where a cloud first comes GAP from the brain."""
    u = (math.cos(math.radians(angle)), math.sin(math.radians(angle)))
    mirror = u[0] < 0
    lo, hi = 0.0, 80.0
    for _ in range(18):
        m = (lo + hi) / 2
        lo, hi = (lo, m) if cloud_at((O[0] + m * u[0], O[1] + m * u[1]), mirror).distance(BRAIN) >= GAP else (m, hi)
    return (O[0] + hi * u[0], O[1] + hi * u[1]), mirror


def fit_in_cloud(geoms, c, mirror, shrink=1.0):
    """A picture scaled up as far as it will go inside the cloud, then by shrink."""
    g = unary_union(geoms)
    if mirror:   # fit the picture the right way round in the mirrored room
        g = affinity.scale(g, -1, 1, origin=(0, 0))
    x0, y0, x1, y1 = g.bounds
    g = affinity.translate(g, -(x0 + x1) / 2, -(y0 + y1) / 2)
    best = (0, 0, 0)
    for dx in [k * 0.25 for k in range(-6, 7)]:
        for dy in [k * 0.25 for k in range(-6, 7)]:
            lo, hi = max(0.3, best[0]), 1.6
            if not ROOM.contains(affinity.translate(affinity.scale(g, lo, lo, origin=(0, 0)), dx, dy)):
                continue
            for _ in range(12):
                m = (lo + hi) / 2
                lo, hi = (m, hi) if ROOM.contains(affinity.translate(affinity.scale(g, m, m, origin=(0, 0)),
                                                                     dx, dy)) else (lo, m)
            if lo > best[0]:
                best = (lo, dx, dy)
    s, dx, dy = best
    g = affinity.translate(affinity.scale(g, s, s, origin=(0, 0)), dx, dy)
    if mirror:
        g = affinity.scale(g, -1, 1, origin=(0, 0))
    g = affinity.scale(g, shrink, shrink, origin=g.centroid)
    return affinity.translate(g, *c)


def trail(p, u, length):
    """Two circles, big then small, spaced evenly along length mm from p in direction u."""
    (r1, w1), (r2, w2) = (1.8, 0.85), (1.08, 0.6)
    sp = (length - 2 * r1 - 2 * r2) / 3
    return [stroke(Point(p[0] + u[0] * d, p[1] + u[1] * d).buffer(r), w)
            for d, r, w in ((sp + r1, r1, w1), (2 * sp + 2 * r1 + r2, r2, w2))]


clouds = []
for angle, picture, shrink in CLOUDS:
    c, mirror = cloud_out(angle)
    cl = cloud_at(c, mirror)
    p, q = nearest_points(cl, BRAIN)
    ink += [stroke(cl, BOLD), *trail((p.x, p.y), unit((p.x, p.y), (q.x, q.y)), GAP),
            fit_in_cloud(picture(), c, mirror, shrink)]
    clouds.append(cl)

# the bottom pair: the left one where the ray puts it, moved sideways to a set
# x, its trail leaving its edge at a set angle up and in, as long as the shorter
# of the runs to the brain on either side; the right one, the mirror image
angle, x, up, left, shrink, right = BOTTOM
c = (x, cloud_out(angle)[0][1])
cl = cloud_at(c, True)
u = (math.cos(math.radians(up)), -math.sin(math.radians(up)))
ray = LineString([c, (c[0] + 80 * u[0], c[1] + 80 * u[1])])
p = min(getattr(ray.intersection(cl.exterior), "geoms", [ray.intersection(cl.exterior)]),
        key=lambda q: Point(c).distance(q))
runs = []
for br in (BRAIN, affinity.scale(BRAIN, -1, 1, origin=(MID_X, 0))):
    hits = ray.intersection(br.exterior)
    runs.append(p.distance(min(getattr(hits, "geoms", [hits]), key=lambda q: Point(c).distance(q))))
pair = [stroke(cl, BOLD), *trail((p.x, p.y), u, min(runs))]
ink += pair + [affinity.scale(g, -1, 1, origin=(MID_X, 0)) for g in pair]
ink += [fit_in_cloud(left(), c, True, shrink), fit_in_cloud(right(), (2 * MID_X - c[0], c[1]), False)]
clouds += [cl, affinity.scale(cl, -1, 1, origin=(MID_X, 0))]


# --- sparkles ------------------------------------------------------------------------
# Biggest first, each where it is farthest from everything already drawn, so they
# spread out and the big ones take the big gaps.  The lid's edge counts too, a
# little less, so they don't line up along it.
SPARKLES = [4.2, 3.8, 3.4, 3.2, 3.0, 2.8, 2.6, 2.4, 2.4, 2.2, 2.0, 2.0, 1.8, 1.8, 1.6, 1.6, 1.5, 1.4]  # radii, mm
MARGIN = 3.0
CLEAR = 2.5   # mm between a sparkle and anything else
sx, sy = np.meshgrid(np.arange(MARGIN, W - MARGIN, 0.5), np.arange(MARGIN, H - MARGIN, 0.5))
spots = shapely.points(sx.ravel(), sy.ravel())
edge = shapely.distance(spots, box(MARGIN, MARGIN, W - MARGIN, H - MARGIN).exterior)
taken = unary_union(ink)
sparkles = []
for r in SPARKLES:
    d = shapely.distance(spots, taken)
    ok = (d >= r + CLEAR) & (edge >= r)
    i = int(np.argmax(np.where(ok, np.minimum(d, edge + 4.0), -1)))
    if not ok[i]:
        break
    g = twinkle(spots[i].x, spots[i].y, r)
    ink.append(g)
    taken = taken.union(g)
    sparkles.append(g)


def main():
    art = unary_union(ink)
    polys = getattr(art, "geoms", [art])
    n = lambda v: f"{v:.2f}".rstrip("0").rstrip(".")  # noqa: E731
    paths = []
    for q in polys:
        q = orient(q.simplify(0.01), 1.0)
        d = "".join("M" + "L".join(f"{n(x)} {n(y)}" for x, y in ring.coords[:-1]) + "Z"
                    for ring in (q.exterior, *q.interiors))
        paths.append(f'<path d="{d}" fill="#000000"/>')
    OUT.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:g}mm" height="{H:g}mm" '
                   f'viewBox="0 0 {W:g} {H:g}">\n' + "\n".join(paths) + "\n</svg>\n")
    x0, y0, x1, y1 = art.bounds
    gaps = [cl.distance(BRAIN) for cl in clouds]
    print(f"{OUT}: {len(paths)} paths, {len(folds)} brain folds, {len(clouds)} clouds "
          f"({min(gaps):.1f}-{max(gaps):.1f} mm from the brain), {len(sparkles)} sparkles, "
          f"ink {x1 - x0:.1f} x {y1 - y0:.1f} mm")


if __name__ == "__main__":
    main()
