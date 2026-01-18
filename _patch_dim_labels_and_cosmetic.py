import os, re
from pathlib import Path

MOD = os.environ.get("MOD_PATH")
if not MOD:
    raise SystemExit("MOD_PATH env var missing")

p = Path(MOD)
txt = p.read_text(encoding="utf-8", errors="ignore")

# ------------------------------------------------------------------
# 1) Make PartRectItem pen cosmetic (so lines don't vanish after fitInView)
# Insert pen.setCosmetic(True) just before self.setPen(pen) in _update_pen
# ------------------------------------------------------------------
def patch_update_pen(src: str) -> str:
    m = re.search(r"(?ms)def _update_pen\(self\):\s*\n(.*?)(\n\s*def |\n\s*class |\Z)", src)
    if not m:
        return src
    block = m.group(0)

    # only patch inside that block
    def repl(match):
        line = match.group(0)
        indent = match.group(1)
        # if already cosmetic in previous lines, keep
        return f"{indent}pen.setCosmetic(True)\n{line}"

    # add before self.setPen(pen) if not already present nearby
    if "pen.setCosmetic(True)" not in block:
        block2 = re.sub(r"(?m)^(\s*)self\.setPen\(pen\)\s*$", repl, block, count=1)
        if block2 != block:
            src = src.replace(block, block2)
    return src

txt2 = patch_update_pen(txt)

# Also make outer/top pens cosmetic (pen_outer, pen_thin)
txt2 = re.sub(
    r"(?m)^(?P<i>\s*)pen_outer\s*=\s*QtGui\.QPen\(QtGui\.QColor\([^)]+\),\s*2\.0\)\s*$",
    r"\g<i>pen_outer = QtGui.QPen(QtGui.QColor(\"#0f172a\"), 2.0)\n\g<i>pen_outer.setCosmetic(True)",
    txt2,
    count=1
)

txt2 = re.sub(
    r"(?m)^(?P<i>\s*)pen_thin\s*=\s*QtGui\.QPen\(QtGui\.QColor\([^)]+\),\s*1\.2\)\s*$",
    r"\g<i>pen_thin = QtGui.QPen(QtGui.QColor(\"#334155\"), 1.2)\n\g<i>pen_thin.setCosmetic(True)",
    txt2,
    count=1
)

# ------------------------------------------------------------------
# 2) Replace DIMENSIONS block: move labels off the line + add white background
# Looks for the block starting at '# --- DIMENSIONS' up to D label
# ------------------------------------------------------------------
pattern = re.compile(
    r"(?ms)"
    r"^\s*#\s*---\s*DIMENSIONS.*?\n"
    r"\s*dim_pen\s*=.*?\n"
    r".*?\n"
    r"\s*#\s*FRONT VIEW: H only.*?\n"
    r"\s*xH\s*=.*?\n"
    r"\s*self\.scene\.addLine.*?\n"
    r"\s*dim_text\([^)]*\)\s*\n\n"
    r"\s*#\s*TOP VIEW: W.*?\n"
    r"\s*yW\s*=.*?\n"
    r"\s*self\.scene\.addLine.*?\n"
    r"\s*dim_text\([^)]*\)\s*\n\n"
    r"\s*xD\s*=.*?\n"
    r"\s*self\.scene\.addLine.*?\n"
    r"\s*dim_text\([^)]*\)\s*\n",
    re.MULTILINE
)

replacement = r"""
            # --- DIMENSIONS (czytelne, etykiety poza linią) ---
            dim_pen = QtGui.QPen(QtGui.QColor("#2563eb"), 2.6)
            dim_pen.setCosmetic(True)

            def dim_label(number_str: str, cx: float, cy: float):
                # text
                titem = self.scene.addText(number_str)
                f = QtGui.QFont()
                f.setPointSize(16)
                f.setBold(True)
                titem.setFont(f)
                titem.setDefaultTextColor(QtGui.QColor("#0f172a"))
                br = titem.boundingRect()

                # white background (improves legibility)
                bg = QtWidgets.QGraphicsRectItem(QtCore.QRectF(0, 0, br.width() + 10, br.height() + 6))
                bg.setPos(cx - br.width()/2 - 5, cy - br.height()/2 - 3)
                bg.setPen(QtGui.QPen(QtCore.Qt.PenStyle.NoPen))
                bg.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255, 210)))
                bg.setZValue(9998)
                self.scene.addItem(bg)

                titem.setPos(cx - br.width()/2, cy - br.height()/2)
                titem.setZValue(9999)
                return titem

            # FRONT VIEW: H label LEFT of the line (not on it)
            xH = front_rect.left() - 32
            lineH = self.scene.addLine(xH, front_rect.top(), xH, front_rect.bottom(), dim_pen)
            try: lineH.setZValue(50)
            except Exception: pass
            dim_label(f"{int(H)}", xH - 22, front_rect.center().y())

            # TOP VIEW: W label ABOVE the line
            yW = top_rect.top() - 26
            lineW = self.scene.addLine(top_rect.left(), yW, top_rect.right(), yW, dim_pen)
            try: lineW.setZValue(50)
            except Exception: pass
            dim_label(f"{int(W)}", top_rect.center().x(), yW - 16)

            # TOP VIEW: D label LEFT of the line
            xD = top_rect.left() - 32
            lineD = self.scene.addLine(xD, top_rect.top(), xD, top_rect.bottom(), dim_pen)
            try: lineD.setZValue(50)
            except Exception: pass
            dim_label(f"{int(D)}", xD - 22, top_rect.center().y())
"""

txt3 = re.sub(pattern, replacement, txt2, count=1)

if txt3 == txt:
    raise SystemExit("Patch failed: couldn't find target DIMENSIONS block. Paste me the current _refresh_scene DIMENSIONS snippet.")
p.write_text(txt3, encoding="utf-8")
print("PATCH OK: cosmetic pens + dimension labels moved off lines")
