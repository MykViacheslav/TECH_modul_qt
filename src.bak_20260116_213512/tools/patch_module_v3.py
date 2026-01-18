from __future__ import annotations
import re
from pathlib import Path
from datetime import datetime

FILE = Path(__file__).resolve().parents[1] / "tabs" / "module_widget.py"

def must(pattern: str, text: str, name: str):
    if not re.search(pattern, text, flags=re.S):
        raise RuntimeError(f"Patch anchor not found for: {name}")

def patch(text: str) -> str:
    out = text

    # 1) Shelves: if enabled -> at least 1
    out = out.replace(
        "shelves_cnt = int(self.in_shelves.value()) if shelves_on else 0",
        "shelves_cnt = max(1, int(self.in_shelves.value())) if shelves_on else 0"
    )
    out = out.replace(
        "shelves_cnt = int(self.in_shelves.value()) if (self.ck_shelves.isChecked() and self.in_shelves.value() > 0) else 0",
        "shelves_cnt = max(1, int(self.in_shelves.value())) if self.ck_shelves.isChecked() else 0"
    )

    # 2) Add checkboxes for hiding/click-through fronts (after drawers group added)
    anchor = "pl.addWidget(self.gb_drawers)\n"
    if anchor in out and "self.ck_hide_fronts" not in out:
        insert = (
            anchor
            + "\n        # Widok: fronty na rysunku\n"
            + "        self.ck_hide_fronts = QtWidgets.QCheckBox(\"Ukryj fronty na rysunku\")\n"
            + "        self.ck_hide_fronts.setChecked(False)\n"
            + "        self.ck_hide_fronts.setStyleSheet(\"font-weight:900; QCheckBox::indicator{width:18px;height:18px;}\")\n"
            + "        self.ck_fronts_clickable = QtWidgets.QCheckBox(\"Fronty nie przechwytują kliknięć\")\n"
            + "        self.ck_fronts_clickable.setChecked(True)\n"
            + "        self.ck_fronts_clickable.setStyleSheet(\"font-weight:900; QCheckBox::indicator{width:18px;height:18px;}\")\n"
            + "        pl.addWidget(self.ck_hide_fronts)\n"
            + "        pl.addWidget(self.ck_fronts_clickable)\n"
        )
        out = out.replace(anchor, insert)

    # 3) Wire signals: add these checkboxes into hook list
    # find list "for w in [ ... ]:" and append if present
    if "self.ck_hide_fronts" in out and "self.ck_fronts_clickable" in out:
        # crude but stable: insert near other ck_*
        out = out.replace(
            "self.cb_drawer_brand, self.cb_drawer_system, self.cb_drawer_height_code,",
            "self.cb_drawer_brand, self.cb_drawer_system, self.cb_drawer_height_code,\n            self.ck_hide_fronts, self.ck_fronts_clickable,"
        )

    # 4) Make PartRectItem support selectable flag
    # Replace constructor signature + setFlag line
    must(r"class\s+PartRectItem\(", out, "PartRectItem class")
    out = re.sub(
        r"class PartRectItem\(QtWidgets\.QGraphicsRectItem\):\s*?\n\s*def __init__\((.*?)\):\s*?\n\s*super\(\)\.__init__\((.*?)\)\s*?\n\s*self\.part_key = part_key\s*?\n\s*self\.setAcceptHoverEvents\(True\)\s*?\n\s*self\.setFlag\(QtWidgets\.QGraphicsItem\.GraphicsItemFlag\.ItemIsSelectable,\s*True\)\s*?\n",
        "class PartRectItem(QtWidgets.QGraphicsRectItem):\n"
        "    def __init__(self, part_key: str, rect: QtCore.QRectF, selectable: bool = True):\n"
        "        super().__init__(rect)\n"
        "        self.part_key = part_key\n"
        "        self.setAcceptHoverEvents(True)\n"
        "        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, bool(selectable))\n",
        out,
        flags=re.S
    )

    # 5) Update add_part to respect hide/click-through fronts
    # replace "it = PartRectItem(key, rect)" with logic
    must(r"def add_part\(key: str, rect: QtCore\.QRectF\):", out, "add_part function")
    out = re.sub(
        r"it = PartRectItem\(key, rect\)",
        "hide_fronts = getattr(self, 'ck_hide_fronts', None)\n"
        "                hide_fronts = hide_fronts.isChecked() if hide_fronts is not None else False\n"
        "                fronts_clickable = getattr(self, 'ck_fronts_clickable', None)\n"
        "                fronts_clickable = fronts_clickable.isChecked() if fronts_clickable is not None else True\n"
        "\n"
        "                if key.startswith('front_') and hide_fronts:\n"
        "                    return None\n"
        "\n"
        "                selectable = True\n"
        "                if key.startswith('front_') and fronts_clickable:\n"
        "                    selectable = False\n"
        "\n"
        "                it = PartRectItem(key, rect, selectable=selectable)\n"
        "                if key.startswith('front_') and selectable is False:\n"
        "                    it.setOpacity(0.55)\n",
        out,
        flags=re.S
    )

    # 6) Replace module dimensions block: Front=H only; Top=W + D
    must(r"# module dimensions", out, "dimensions block")
    out = re.sub(
        r"# module dimensions.*?all_rect = front_rect\.united\(top_rect\)\.adjusted",
        "# module dimensions\n"
        "            dim_pen = QtGui.QPen(QtGui.QColor(\"#2563eb\"), 2.2)\n"
        "            dim_pen.setCosmetic(True)\n"
        "\n"
        "            def dim_label(text: str, x: float, y: float):\n"
        "                # background\n"
        "                bg = QtWidgets.QGraphicsRectItem(0, 0, 10, 10)\n"
        "                bg.setPen(QtGui.QPen(QtCore.Qt.PenStyle.NoPen))\n"
        "                bg.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255, 220)))\n"
        "                self.scene.addItem(bg)\n"
        "                titem = self.scene.addText(text)\n"
        "                f = QtGui.QFont(); f.setPointSize(11); f.setBold(True)\n"
        "                titem.setFont(f)\n"
        "                titem.setDefaultTextColor(QtGui.QColor(\"#0f172a\"))\n"
        "                br = titem.boundingRect()\n"
        "                bg.setRect(x-6, y-4, br.width()+12, br.height()+8)\n"
        "                titem.setPos(x, y)\n"
        "\n"
        "            # FRONT VIEW: only H\n"
        "            x_dim = front_rect.left() - 38\n"
        "            self.scene.addLine(x_dim, front_rect.top(), x_dim, front_rect.bottom(), dim_pen)\n"
        "            dim_label(f\"H = {H:.0f} mm\", x_dim - 6, front_rect.center().y() - 12)\n"
        "\n"
        "            # TOP VIEW: W + D\n"
        "            y_dim = top_rect.top() - 26\n"
        "            self.scene.addLine(top_rect.left(), y_dim, top_rect.right(), y_dim, dim_pen)\n"
        "            dim_label(f\"W = {W:.0f} mm\", top_rect.center().x() - 48, y_dim - 18)\n"
        "\n"
        "            x_dim2 = top_rect.left() - 38\n"
        "            self.scene.addLine(x_dim2, top_rect.top(), x_dim2, top_rect.bottom(), dim_pen)\n"
        "            dim_label(f\"D = {D:.0f} mm\", x_dim2 - 6, top_rect.center().y() - 12)\n"
        "\n"
        "            all_rect = front_rect.united(top_rect).adjusted",
        out,
        flags=re.S
    )

    return out

def main():
    txt = FILE.read_text(encoding="utf-8", errors="ignore")
    new_txt = patch(txt)
    if new_txt == txt:
        print("NO_CHANGES")
        return
    FILE.write_text(new_txt, encoding="utf-8")
    print("PATCHED:", str(FILE))

if __name__ == "__main__":
    main()
