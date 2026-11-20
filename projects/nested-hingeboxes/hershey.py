"""Single-line text in a Hershey font, for engraving as lines rather than filled
outlines: the laser traces each stroke once, which is quick and stays legible at
the small sizes of the burn test labels.

The font is Hershey Roman Simplex (fonts/futural.jhf, see fonts/HERSHEY-LICENSE.txt).
Each glyph in the .jhf file is a record: a 5-character glyph number, a 3-character
vertex count, then that many pairs of letters, each letter's offset from "R" a
coordinate in font units (y down).  The first pair is the glyph's left and right
edges, " R" lifts the pen.  Long records wrap onto the next line.  The glyphs are
in order from " " (ASCII 32).

Coordinates are mm, x to the right, y down (as in SVG).
"""
from functools import cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
FONT = HERE / "fonts" / "futural.jhf"
CAP = 21                  # font units: capitals and digits run from y = -12 to 9


@cache
def _glyphs():
    """{character: (left, right, strokes)}, each stroke a list of (x, y) in font units."""
    lines = FONT.read_text().splitlines()
    records = []
    while lines:
        line = lines.pop(0)
        n = int(line[5:8])
        while len(line) < 8 + 2 * n:      # the record goes on on the next line
            line += lines.pop(0)
        records.append(line[8:8 + 2 * n])
    glyphs = {}
    for code, rec in zip(range(32, 127), records):
        pairs = [(ord(rec[i]) - ord("R"), ord(rec[i + 1]) - ord("R")) for i in range(0, len(rec), 2)]
        (left, right), strokes = pairs[0], [[]]
        for p in pairs[1:]:
            if p == (ord(" ") - ord("R"), 0):
                strokes.append([])
            else:
                strokes[-1].append(p)
        glyphs[chr(code)] = left, right, [s for s in strokes if s]
    return glyphs


def strokes(text, height):
    """The strokes of one line of text with capitals and digits `height` mm tall,
    centred on (0, 0) by their ink: a list of polylines, each a list of (x, y)."""
    s = height / CAP
    out, x = [], 0
    for ch in text:
        left, right, glyph = _glyphs()[ch]
        out += [[((x - left + px) * s, py * s) for px, py in stroke] for stroke in glyph]
        x += right - left
    xs = [p[0] for line in out for p in line]
    ys = [p[1] for line in out for p in line]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    return [[(px - cx, py - cy) for px, py in line] for line in out]
