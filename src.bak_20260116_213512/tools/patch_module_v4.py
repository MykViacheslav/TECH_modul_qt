from __future__ import annotations
import re
from pathlib import Path

FILE = Path(__file__).resolve().parents[1] / "tabs" / "module_widget.py"

def must(pattern: str, text: str, name: str):
    if not re.search(pattern, text, flags=re.S):
        raise RuntimeError(f"Patch anchor not found: {name}")

def patch_drawer_rule(txt: str) -> str:
    out = txt

    # Replace "D - 50" drawer depth clearance with "D - 10" if present
    out = re.sub(r"(\bdrawer_?depth\b\s*=\s*)D\s*-\s*50\b", r"\1D - 10", out)
    out = re.sub(r"(\busable_?depth\b\s*=\s*)D\s*-\s*50\b", r"\1D - 10", out)

    # If there is a helper computing drawer length, enforce standard list with 10mm clearance.
    # We inject a tiny helper if not present and swap common expressions.
    if "def _drawer_std_length" not in out:
        # Inject near top-level helpers (after imports)
        out = re.sub(
            r"(^from __future__.*?\n)(.*?)(\n\n)",
            r"\1\2\3"
            "def _drawer_std_length(depth_mm: float) -> int:\n"
            "    \"\"\"Dobór długości szuflady: luz z tyłu 10 mm, standardy co 50 mm.\"\"\"\n"
            "    usable = max(0.0, float(depth_mm) - 10.0)\n"
            "    std = [270, 300, 350, 400, 450, 500, 550, 600]\n"
            "    ok = [x for x in std if x <= usable]\n"
            "    return int(ok[-1]) if ok else 0\n\n",
            out,
            flags=re.S,
            count=1
        )

    # Swap patterns like: drawer_len = int(D - 50) or drawer_len = D - 50
    out = re.sub(r"\bdrawer_len\b\s*=\s*int\(\s*D\s*-\s*50\s*\)", "drawer_len = _drawer_std_length(D)", out)
    out = re.sub(r"\bdrawer_len\b\s*=\s*D\s*-\s*50\b", "drawer_len = _drawer_std_length(D)", out)
    out = re.sub(r"\bdrawer_len\b\s*=\s*int\(\s*D\s*-\s*10\s*\)", "drawer_len = _drawer_std_length(D)", out)

    return out

def patch_view_scale_and_dims(txt: str) -> str:
    out = txt

    # Ensure QGraphicsView is centered + bigger minimum area
    # Try to find "self.view = QtWidgets.QGraphicsView(" and add a few lines after it.
    if "setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)" not in out:
        out = re.sub(
            r"(self\.view\s*=\s*QtWidgets\.QGraphicsView\([^\n]*\)\s*\n)",
            r"\1"
            "        self.view.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)\n"
            "        self.view.setMinimumHeight(520)\n"
            "        self.view.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)\n"
            "        self.view.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing, True)\n",
            out,
            flags=re.S,
            count=1
        )

    # Replace previous dimension block (if exists from earlier patch) with new bigger-only-number labels
    # We look for our earlier injected "dim_pen = QtGui.QPen" block and replace until "all_rect ="
    dim_block = re.search(r"\n\s*dim_pen\s*=\s*QtGui\.QPen.*?\n\s*all_rect\s*=\s*", out, flags=re.S)
    if dim_block:
        # Replace the whole injected block safely
        out = re.sub(
            r"\n\s*dim_pen\s*=\s*QtGui\.QPen.*?\n\s*all_rect\s*=\s*",
            "\n"
            "            # --- DIMENSIONS (czytelne, tylko liczby) ---\n"
            "            dim_pen = QtGui.QPen(QtGui.QColor(\"#2563eb\"), 2.6)\n"
            "            dim_pen.setCosmetic(True)\n"
            "\n"
            "            def dim_text(number_str: str, x: float, y: float, rotate_deg: float = 0.0):\n"
            "                t = self.scene.addText(number_str)\n"
            "                f = QtGui.QFont(); f.setPointSize(16); f.setBold(True)\n"
            "                t.setFont(f)\n"
            "                t.setDefaultTextColor(QtGui.QColor(\"#0f172a\"))\n"
            "                t.setPos(x, y)\n"
            "                if rotate_deg:\n"
            "                    t.setTransformOriginPoint(t.boundingRect().center())\n"
            "                    t.setRotation(rotate_deg)\n"
            "                return t\n"
            "\n"
            "            # FRONT VIEW: H only (vertical)\n"
            "            xH = front_rect.left() - 32\n"
            "            self.scene.addLine(xH, front_rect.top(), xH, front_rect.bottom(), dim_pen)\n"
            "            dim_text(f\"{int(H)}\", xH - 18, front_rect.center().y() - 12, rotate_deg=-90)\n"
            "\n"
            "            # TOP VIEW: W (horizontal) + D (vertical)\n"
            "            yW = top_rect.top() - 26\n"
            "            self.scene.addLine(top_rect.left(), yW, top_rect.right(), yW, dim_pen)\n"
            "            dim_text(f\"{int(W)}\", top_rect.center().x() - 12, yW - 22, rotate_deg=0)\n"
            "\n"
            "            xD = top_rect.left() - 32\n"
            "            self.scene.addLine(xD, top_rect.top(), xD, top_rect.bottom(), dim_pen)\n"
            "            dim_text(f\"{int(D)}\", xD - 18, top_rect.center().y() - 12, rotate_deg=-90)\n"
            "\n"
            "            all_rect = ",
            out,
            flags=re.S,
            count=1
        )

    # Make fitInView less aggressive (so drawing not tiny):
    # find "self.view.fitInView(" call and then scale up slightly.
    if "self.view.scale(1.25, 1.25)" not in out:
        out = re.sub(
            r"(self\.view\.fitInView\(\s*all_rect\s*,\s*QtCore\.Qt\.[^\)]*\)\s*\n)",
            r"\1            self.view.scale(1.25, 1.25)\n",
            out,
            flags=re.S,
            count=1
        )

    return out

def main():
    txt = FILE.read_text(encoding="utf-8", errors="ignore")

    # sanity anchors
    must(r"QGraphicsView", txt, "QGraphicsView exists")
    must(r"front_rect", txt, "front_rect exists")
    must(r"top_rect", txt, "top_rect exists")

    out = txt
    out = patch_drawer_rule(out)
    out = patch_view_scale_and_dims(out)

    if out == txt:
        print("NO_CHANGES")
        return

    FILE.write_text(out, encoding="utf-8")
    print("PATCHED:", str(FILE))

if __name__ == "__main__":
    main()
