import os
from pathlib import Path

MOD = os.environ.get("MOD_PATH")
if not MOD:
    raise SystemExit("MOD_PATH env var missing")

p = Path(MOD)
lines = p.read_text(encoding="utf-8", errors="ignore").splitlines(True)

def indent_len(s: str) -> int:
    return len(s) - len(s.lstrip(" \t"))

def startswith_stripped(line: str, prefix: str) -> bool:
    return line.lstrip(" \t").startswith(prefix)

def ensure_insert_after(match_substr: str, insert_line: str) -> int:
    """Insert insert_line right after the first line containing match_substr,
    but only if insert_line is not already present near it."""
    for i, ln in enumerate(lines):
        if match_substr in ln:
            # check next ~3 lines for existing insert
            window = "".join(lines[i:i+4])
            if insert_line.strip() in window:
                return 0
            ind = ln[:indent_len(ln)]
            lines.insert(i+1, ind + insert_line + "\n")
            return 1
    return 0

# 1) Make PartRectItem pen cosmetic: insert pen.setCosmetic(True) before self.setPen(pen)
changed_part_pen = 0
for i, ln in enumerate(lines):
    if "self.setPen(pen)" in ln:
        # if previous few lines already have setCosmetic, skip
        window = "".join(lines[max(0, i-4):i+1])
        if "pen.setCosmetic(True)" in window:
            continue
        ind = ln[:indent_len(ln)]
        lines.insert(i, ind + "pen.setCosmetic(True)\n")
        changed_part_pen += 1
        break  # only once

# 2) In _refresh_scene: make pen_outer and pen_thin cosmetic (safe insert)
changed_pen_outer = ensure_insert_after("pen_outer = QtGui.QPen(", "pen_outer.setCosmetic(True)")
changed_pen_thin  = ensure_insert_after("pen_thin = QtGui.QPen(",  "pen_thin.setCosmetic(True)")

# 3) Replace DIMENSIONS block inside _refresh_scene
start_idx = None
for i, ln in enumerate(lines):
    if "# --- DIMENSIONS" in ln:
        start_idx = i
        break

if start_idx is None:
    raise SystemExit("Patch failed: cannot find '# --- DIMENSIONS' block in file.")

base_indent = lines[start_idx][:indent_len(lines[start_idx])]

# find end marker: first 'all_rect =' after the DIMENSIONS block
end_idx = None
for j in range(start_idx+1, len(lines)):
    if startswith_stripped(lines[j], "all_rect"):
        end_idx = j
        break

if end_idx is None:
    raise SystemExit("Patch failed: cannot find 'all_rect' after DIMENSIONS block (file layout changed).")

new_block = [
    base_indent + "# --- DIMENSIONS (czytelne, etykiety poza linią) ---\n",
    base_indent + "dim_pen = QtGui.QPen(QtGui.QColor('#2563eb'), 2.6)\n",
    base_indent + "dim_pen.setCosmetic(True)\n",
    base_indent + "\n",
    base_indent + "def dim_label(number_str: str, cx: float, cy: float):\n",
    base_indent + "    titem = self.scene.addText(number_str)\n",
    base_indent + "    f = QtGui.QFont(); f.setPointSize(16); f.setBold(True)\n",
    base_indent + "    titem.setFont(f)\n",
    base_indent + "    titem.setDefaultTextColor(QtGui.QColor('#0f172a'))\n",
    base_indent + "    br = titem.boundingRect()\n",
    base_indent + "\n",
    base_indent + "    bg = QtWidgets.QGraphicsRectItem(QtCore.QRectF(0, 0, br.width() + 10, br.height() + 6))\n",
    base_indent + "    bg.setPos(cx - br.width()/2 - 5, cy - br.height()/2 - 3)\n",
    base_indent + "    bg.setPen(QtGui.QPen(QtCore.Qt.PenStyle.NoPen))\n",
    base_indent + "    bg.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255, 210)))\n",
    base_indent + "    bg.setZValue(9998)\n",
    base_indent + "    self.scene.addItem(bg)\n",
    base_indent + "\n",
    base_indent + "    titem.setPos(cx - br.width()/2, cy - br.height()/2)\n",
    base_indent + "    titem.setZValue(9999)\n",
    base_indent + "    return titem\n",
    base_indent + "\n",
    base_indent + "# FRONT VIEW: H — tekst obok linii (nie na linii)\n",
    base_indent + "xH = front_rect.left() - 32\n",
    base_indent + "self.scene.addLine(xH, front_rect.top(), xH, front_rect.bottom(), dim_pen)\n",
    base_indent + "dim_label(f\"{int(H)}\", xH - 22, front_rect.center().y())\n",
    base_indent + "\n",
    base_indent + "# TOP VIEW: W — tekst NAD linią\n",
    base_indent + "yW = top_rect.top() - 26\n",
    base_indent + "self.scene.addLine(top_rect.left(), yW, top_rect.right(), yW, dim_pen)\n",
    base_indent + "dim_label(f\"{int(W)}\", top_rect.center().x(), yW - 16)\n",
    base_indent + "\n",
    base_indent + "# TOP VIEW: D — tekst obok linii\n",
    base_indent + "xD = top_rect.left() - 32\n",
    base_indent + "self.scene.addLine(xD, top_rect.top(), xD, top_rect.bottom(), dim_pen)\n",
    base_indent + "dim_label(f\"{int(D)}\", xD - 22, top_rect.center().y())\n",
    base_indent + "\n",
]

# replace
lines[start_idx:end_idx] = new_block

p.write_text("".join(lines), encoding="utf-8")

print("PATCH OK:",
      "dim_block_replaced=1,",
      f"part_pen_cosmetic={changed_part_pen},",
      f"pen_outer_cosmetic={changed_pen_outer},",
      f"pen_thin_cosmetic={changed_pen_thin}")
