"""The text engraved on the boxes: the words, their sizes, and their outlines.

Shared by engrave_boxes.py (the cut files) and make_model.py (the 3D model), so
both show exactly the same outlines.  The text is set in Special Elite
(fonts/SpecialElite-Regular.ttf, Apache License 2.0) and turned into paths, so
the laser software doesn't need the font.

Coordinates are mm on the face that carries the text, origin at the top-left
corner of the face's inner area, x to the right, y down (as in SVG).  The inner
area of the front wall is x by h, of the bottom x by y.
"""
from functools import cache
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

HERE = Path(__file__).resolve().parent
FONT = HERE / "fonts" / "SpecialElite-Regular.ttf"

# Text on the front of each box and under its bottom, one tuple of lines per box.
FRONT_TEXT = [("Scientific", "Discoveries"), ("Feline", "Facts"), ("Problematic", "Data"),
              ("Exuberant", "Ideas")]
BOTTOM_TEXT = [(name, "Chrismukkah 2026")
               for name in ("Ember Barber", "Leah Barber", "Rina Foygel Barber", "Mathew Barber")]

PAD = 12.0          # mm clear around the front text on the box with the lowest front
LEADING = 1.2       # line pitch, in font sizes
BOTTOM_SIZE = 6.0   # mm, font size of the bottom text


@cache
def _font():
    f = TTFont(FONT)
    return f, f.getGlyphSet(), f.getBestCmap(), f["head"].unitsPerEm, _kerning(f)


def _kerning(f):
    """Pair kerning (x advance adjustments, font units) from the GPOS kern lookups."""
    kern = {}
    gpos = f["GPOS"].table
    for li in {i for fr in gpos.FeatureList.FeatureRecord if fr.FeatureTag == "kern"
               for i in fr.Feature.LookupListIndex}:
        for st in gpos.LookupList.Lookup[li].SubTable:
            if st.Format == 1:
                for first, ps in zip(st.Coverage.glyphs, st.PairSet):
                    for pv in ps.PairValueRecord:
                        v = getattr(pv.Value1, "XAdvance", 0) or 0
                        kern.setdefault((first, pv.SecondGlyph), v)
            else:
                c1, c2 = st.ClassDef1.classDefs, st.ClassDef2.classDefs
                for first in st.Coverage.glyphs:
                    rec = st.Class1Record[c1.get(first, 0)]
                    for second in f.getGlyphOrder():
                        v = getattr(rec.Class2Record[c2.get(second, 0)].Value1, "XAdvance", 0) or 0
                        if v:
                            kern.setdefault((first, second), v)
    return kern


def _line(text):
    """Glyph names and their x positions (font units) for one line."""
    f, _, cmap, _, kern = _font()
    hmtx = f["hmtx"]
    x, out, prev = 0, [], None
    for ch in text:
        g = cmap[ord(ch)]
        if prev:
            x += kern.get((prev, g), 0)
        out.append((g, x))
        x += hmtx[g][0]
        prev = g
    return out


@cache
def _glyph_bounds(g):
    _, gs, _, _, _ = _font()
    pen = BoundsPen(gs)
    gs[g].draw(pen)
    return pen.bounds  # None for a space


def _ink(lines, size):
    """Ink box of the lines at `size` mm: each line centred on x = 0 by its ink,
    baseline of line k at y = k * LEADING * size (y down).  Returns the box and
    each line's x offset."""
    _, _, _, upem, _ = _font()
    s = size / upem
    x0 = y0 = float("inf")
    x1 = y1 = float("-inf")
    offsets = []
    for k, text in enumerate(lines):
        bs = [(px + b[0], b[1], px + b[2], b[3]) for g, px in _line(text)
              if (b := _glyph_bounds(g))]
        lx0, lx1 = min(b[0] for b in bs) * s, max(b[2] for b in bs) * s
        dx = -(lx0 + lx1) / 2
        offsets.append(dx)
        base = k * LEADING * size
        x0, x1 = min(x0, lx0 + dx), max(x1, lx1 + dx)
        y0 = min(y0, base - max(b[3] for b in bs) * s)
        y1 = max(y1, base - min(b[1] for b in bs) * s)
    return (x0, y0, x1, y1), offsets


def fit(lines, w, h, pad=PAD):
    """Largest font size (mm) at which the lines fit a w x h face with `pad` all round."""
    (x0, y0, x1, y1), _ = _ink(lines, 1.0)
    return min((w - 2 * pad) / (x1 - x0), (h - 2 * pad) / (y1 - y0))


def front_sizes(faces):
    """Font sizes for the fronts, faces = [(lines, w, h), ...]: the lowest front gets
    the largest size that fits it; the others scale up from it with their front's
    height, never past their own fit."""
    ref = min(faces, key=lambda f: f[2])
    s = fit(*ref)
    return [min(s * h / ref[2], fit(lines, w, h)) for lines, w, h in faces]


def outlines(lines, size, w, h, at=(0.0, 0.0)):
    """SVG path data of the lines at `size` mm, centred on a w x h face (by ink)
    whose top-left corner is at `at`, plus the ink box."""
    _, gs, _, upem, _ = _font()
    s = size / upem
    (x0, y0, x1, y1), offsets = _ink(lines, size)
    ox, oy = at[0] + w / 2 - (x0 + x1) / 2, at[1] + h / 2 - (y0 + y1) / 2
    pen = SVGPathPen(gs, ntos=lambda v: f"{v:.2f}".rstrip("0").rstrip("."))
    for k, text in enumerate(lines):
        base = oy + k * LEADING * size
        for g, px in _line(text):
            gs[g].draw(TransformPen(pen, (s, 0, 0, -s, ox + offsets[k] + px * s, base)))
    return pen.getCommands(), (x0 + ox, y0 + oy, x1 + ox, y1 + oy)


def box_text(faces_front, faces_bottom):
    """All engravings: for each box a dict with the front and bottom outlines.
    faces_front / faces_bottom = [(x, y, w, h), ...] per box: where the face's
    inner area starts and its size in mm."""
    sizes = front_sizes([(t, w, h) for t, (_, _, w, h) in zip(FRONT_TEXT, faces_front)])
    out = []
    for i, ((fx, fy, fw, fh), (bx, by, bw, bh)) in enumerate(zip(faces_front, faces_bottom)):
        fd, fink = outlines(FRONT_TEXT[i], sizes[i], fw, fh, (fx, fy))
        bd, bink = outlines(BOTTOM_TEXT[i], BOTTOM_SIZE, bw, bh, (bx, by))
        out.append({
            "front": {"lines": FRONT_TEXT[i], "size": sizes[i], "w": fw, "h": fh, "d": fd, "ink": fink},
            "bottom": {"lines": BOTTOM_TEXT[i], "size": BOTTOM_SIZE, "w": bw, "h": bh, "d": bd, "ink": bink},
        })
    return out
