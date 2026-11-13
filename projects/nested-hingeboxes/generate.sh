#!/usr/bin/env bash
# Regenerate every file in this folder.
# Needs the boxes.py dependencies (see pyproject.toml), run from anywhere:
#   projects/nested-hingeboxes/generate.sh
# Set PYTHON to pick an interpreter (default: python3).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
PY="${PYTHON:-python3}"
cd "$HERE"
mkdir -p boxes sheets/clustered sheets/split

# 1. The four boxes: inside dimensions, 3 mm material, lid height 20 mm.
i=1
while read -r x y h; do
  PYTHONPATH="$ROOT" "$PY" "$ROOT/scripts/boxes" HingeBox --x "$x" --y "$y" --h "$h" \
    --lidheight 20 --thickness 3 --reference 0 --output "boxes/box$i.svg"
  i=$((i + 1))
done <<'SIZES'
160 80 60
168 95 68
176 110 76
184 125 84
SIZES
BOXES=(boxes/box1.svg boxes/box2.svg boxes/box3.svg boxes/box4.svg)

# 2. Everything on one sheet.
"$PY" pack_single.py cutsheet.svg "${BOXES[@]}"

# 3. N equal sheets, hinge pieces kept in clusters and split (runs in parallel).
for n in 6 8 9 10 12; do
  "$PY" pack_sheets.py "$n" "sheets/clustered/sheets$n.svg" "${BOXES[@]}" &
  "$PY" pack_sheets.py --split-hinges "$n" "sheets/split/sheets$n.svg" "${BOXES[@]}" &
done
wait

# 4. Comparison table of all layouts.
"$PY" compare.py
