from __future__ import annotations
from pathlib import Path
import re

FILE = Path(r"""C:\PythonProject\TECH_modul\TECH_modul_qt\src\tabs\module_widget.py""")

def subn(txt: str, pat: str, repl: str, flags=re.S, count=0):
    return re.subn(pat, repl, txt, flags=flags, count=count)

def ensure_drawer_helper(txt: str) -> tuple[str,int]:
    out = txt
    changed = 0

    helper = (
        "def _drawer_std_length(depth_mm: float) -> int:\n"
        "    \"\"\"Długość szuflady: luz z tyłu = 10 mm, dobór standardu <= (D-10).\"\"\"\n"
        "    usable = max(0.0, float(depth_mm) - 10.0)\n"
        "    std = [250, 270, 300, 350, 400, 450, 500, 550, 600]\n"
        "    ok = [x for x in std if x <= usable]\n"
        "    return int(ok[-1]) if ok else 0\n\n"
    )

    if "def _drawer_std_length" in out:
        # replace body robustly
        pat = r"def\s+_drawer_std_length\([^\)]*\)\s*->\s*int\s*:\s*\n(?:\s+.*\n)+?(?=\n\S|\Z)"
        m = re.search(pat, out, flags=re.S)
        if m:
            out = out[:m.start()] + helper + out[m.end():]
            changed += 1
    else:
        # inject near top after imports
        out2, n = subn(out, r"(^from __future__.*?\n)(.*?)(\n\n)", r"\1\2\3"+helper, flags=re.S, count=1)
        if n:
            out = out2
            changed += 1

    return out, changed

def patch_drawer_calcs(txt: str) -> tuple[str,int]:
    out = txt
    changed = 0

    # 1) Replace any drawer-related "- 50" to "- 10" (only lines containing 'drawer' or 'szufl')
    lines = out.splitlines(True)
    new_lines = []
    local = 0
    for ln in lines:
        low = ln.lower()
        if ("drawer" in low or "szufl" in low) and re.search(r"-\s*50\b", ln):
            ln2 = re.sub(r"-\s*50\b", "- 10", ln)
            if ln2 != ln:
                local += 1
            ln = ln2
        new_lines.append(ln)
    if local:
        out = "".join(new_lines)
        changed += local

    # 2) Replace common assignment to use helper
    # drawer_len = D - 10 / int(D-10) -> _drawer_std_length(D)
    before = out
    out = re.sub(r"\bdrawer_len\b\s*=\s*int\(\s*D\s*-\s*10\s*\)", "drawer_len = _drawer_std_length(D)", out)
    out = re.sub(r"\bdrawer_len\b\s*=\s*D\s*-\s*10\b", "drawer_len = _drawer_std_length(D)", out)

    # Some code uses drawer_depth or box_depth as drawer length; patch common patterns:
    out = re.sub(r"\b(drawer_depth|drawer_length|len_drawer)\b\s*=\s*int\(\s*D\s*-\s*10\s*\)", r"\1 = _drawer_std_length(D)", out)
    out = re.sub(r"\b(drawer_depth|drawer_length|len_drawer)\b\s*=\s*D\s*-\s*10\b", r"\1 = _drawer_std_length(D)", out)

    if out != before:
        changed += 1

    return out, changed

def patch_top_view_front(txt: str) -> tuple[str,int]:
    """
    Ensure top view shows a front strip.
    Important: key must NOT start with 'front_' (because hide_fronts filters front_*).
    We'll draw with key 'frontTop' and style can be same as other parts.
    """
    out = txt
    changed = 0

    if "frontTop" in out and "front strip in TOP VIEW" in out:
        return out, changed

    # Find place after top_rect creation
    pat = r"(top_rect\s*=\s*QtCore\.QRectF\([^\n]*\)\s*\n)"
    m = re.search(pat, out)
    if not m:
        return out, changed

    inject = (
        m.group(1)
        + "            # front strip in TOP VIEW (front widoczny z góry)\n"
        + "            front_chk = getattr(self, 'ck_front', None)\n"
        + "            front_on2 = front_chk.isChecked() if front_chk is not None else False\n"
        + "            if front_on2:\n"
        + "                strip_h = max(8.0, min(14.0, top_rect.height() * 0.08))\n"
        + "                front_strip = QtCore.QRectF(top_rect.left(), top_rect.top(), top_rect.width(), strip_h)\n"
        + "                add_part('frontTop', front_strip)\n"
    )
    out = out[:m.start()] + inject + out[m.end():]
    changed += 1
    return out, changed

def restore_offsets_ui(txt: str) -> tuple[str,int]:
    """
    Restore a compact 'Skrócenia / Offsety' section if missing.
    Best-effort: insert under dimensions group area (after main size inputs).
    """
    out = txt
    changed = 0
    if "Skrócenia / Offsety" in out:
        return out, changed

    # Anchor: after dimensions groupbox is added (often gb_dims or similar)
    # We'll insert after first occurrence of adding the dimensions group to layout.
    anchors = [
        "pl.addWidget(self.gb_dims)\n",
        "pl.addWidget(self.gb_dimensions)\n",
        "pl.addWidget(self.gb_size)\n",
    ]
    anchor_found = None
    for a in anchors:
        if a in out:
            anchor_found = a
            break
    if not anchor_found:
        return out, changed

    block = (
        anchor_found
        + "\n        # Skrócenia / Offsety (przywrócone)\n"
        + "        self.gb_offsets = QtWidgets.QGroupBox(\"Skrócenia / Offsety\")\n"
        + "        fl = QtWidgets.QFormLayout(self.gb_offsets)\n"
        + "        fl.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)\n"
        + "\n"
        + "        def _spin(minv=0, maxv=5000):\n"
        + "            s = QtWidgets.QSpinBox()\n"
        + "            s.setRange(minv, maxv)\n"
        + "            s.setFixedWidth(90)\n"
        + "            return s\n"
        + "\n"
        + "        self.off_side_left_top = _spin(0, 5000)\n"
        + "        self.off_side_left_bot = _spin(0, 5000)\n"
        + "        self.off_side_right_top = _spin(0, 5000)\n"
        + "        self.off_side_right_bot = _spin(0, 5000)\n"
        + "        self.off_mid_top = _spin(0, 5000)\n"
        + "        self.off_mid_bot = _spin(0, 5000)\n"
        + "\n"
        + "        row1 = QtWidgets.QHBoxLayout(); row1.addWidget(QtWidgets.QLabel(\"Bok lewy: góra\")); row1.addWidget(self.off_side_left_top); row1.addSpacing(10); row1.addWidget(QtWidgets.QLabel(\"dół\")); row1.addWidget(self.off_side_left_bot); row1.addStretch(1)\n"
        + "        w1 = QtWidgets.QWidget(); w1.setLayout(row1)\n"
        + "        fl.addRow(w1)\n"
        + "\n"
        + "        row2 = QtWidgets.QHBoxLayout(); row2.addWidget(QtWidgets.QLabel(\"Bok prawy: góra\")); row2.addWidget(self.off_side_right_top); row2.addSpacing(10); row2.addWidget(QtWidgets.QLabel(\"dół\")); row2.addWidget(self.off_side_right_bot); row2.addStretch(1)\n"
        + "        w2 = QtWidgets.QWidget(); w2.setLayout(row2)\n"
        + "        fl.addRow(w2)\n"
        + "\n"
        + "        row3 = QtWidgets.QHBoxLayout(); row3.addWidget(QtWidgets.QLabel(\"Ścianki środkowe: góra\")); row3.addWidget(self.off_mid_top); row3.addSpacing(10); row3.addWidget(QtWidgets.QLabel(\"dół\")); row3.addWidget(self.off_mid_bot); row3.addStretch(1)\n"
        + "        w3 = QtWidgets.QWidget(); w3.setLayout(row3)\n"
        + "        fl.addRow(w3)\n"
        + "\n"
        + "        pl.addWidget(self.gb_offsets)\n"
    )

    out = out.replace(anchor_found, block)
    changed += 1
    return out, changed

def add_multi_midwalls_ui(txt: str) -> tuple[str,int]:
    out = txt
    changed = 0
    if "self.tbl_midwalls" in out:
        return out, changed

    # Insert into elements group (gb_elements etc.)
    anchors = [
        "pl.addWidget(self.gb_elements)\n",
        "pl.addWidget(self.gb_parts)\n",
        "pl.addWidget(self.gb_corpus_parts)\n",
    ]
    anchor_found = None
    for a in anchors:
        if a in out:
            anchor_found = a
            break
    if not anchor_found:
        return out, changed

    block = (
        anchor_found
        + "\n        # Ścianki środkowe (wiele sztuk) - tabela\n"
        + "        self.gb_midwalls = QtWidgets.QGroupBox(\"Ścianki środkowe (lista)\")\n"
        + "        v = QtWidgets.QVBoxLayout(self.gb_midwalls)\n"
        + "        top = QtWidgets.QHBoxLayout()\n"
        + "        top.addWidget(QtWidgets.QLabel(\"Ilość:\"))\n"
        + "        self.in_midwalls_cnt = QtWidgets.QSpinBox(); self.in_midwalls_cnt.setRange(0, 20); self.in_midwalls_cnt.setFixedWidth(70)\n"
        + "        top.addWidget(self.in_midwalls_cnt)\n"
        + "        top.addStretch(1)\n"
        + "        v.addLayout(top)\n"
        + "        self.tbl_midwalls = QtWidgets.QTableWidget(0, 3)\n"
        + "        self.tbl_midwalls.setHorizontalHeaderLabels([\"X od lewej (mm)\", \"Offset od dołu (mm)\", \"Wysokość (mm)\"])\n"
        + "        self.tbl_midwalls.verticalHeader().setVisible(False)\n"
        + "        v.addWidget(self.tbl_midwalls)\n"
        + "        pl.addWidget(self.gb_midwalls)\n"
    )
    out = out.replace(anchor_found, block)
    changed += 1

    # connect valueChanged -> rebuild table rows if we find any recalc hook list
    if "self.in_midwalls_cnt.valueChanged.connect" not in out:
        out = out.replace(
            "self.btn_apply.clicked.connect(self._apply)",
            "self.btn_apply.clicked.connect(self._apply)\n        self.in_midwalls_cnt.valueChanged.connect(self._sync_midwalls_rows)"
        )
        changed += 1

    # add method _sync_midwalls_rows if missing
    if "_sync_midwalls_rows" not in out and "def export_state" in out:
        out = out.replace(
            "    def export_state",
            "    def _sync_midwalls_rows(self, *_args) -> None:\n"
            "        try:\n"
            "            n = int(self.in_midwalls_cnt.value())\n"
            "            self.tbl_midwalls.setRowCount(n)\n"
            "            for r in range(n):\n"
            "                for c in range(3):\n"
            "                    if self.tbl_midwalls.item(r, c) is None:\n"
            "                        self.tbl_midwalls.setItem(r, c, QtWidgets.QTableWidgetItem(\"0\"))\n"
            "        except Exception:\n"
            "            pass\n\n"
            "    def export_state"
        )
        changed += 1

    return out, changed

def use_midwalls_in_drawing(txt: str) -> tuple[str,int]:
    """
    Replace single mid wall add_part('mid_wall', rect) with loop reading table rows.
    Best-effort: find 'add_part('mid_wall'' or 'mid_wall_rect'.
    """
    out = txt
    changed = 0

    if "mid_wall_" in out and "tbl_midwalls" in out and "for r in range(self.tbl_midwalls.rowCount())" in out:
        return out, changed

    # Replace first occurrence of add_part('mid_wall', something)
    pat = r"add_part\(\s*['\"]mid_wall['\"]\s*,\s*(?P<rect>[^\)]+)\)"
    m = re.search(pat, out)
    if not m:
        # maybe key named "mid"
        pat2 = r"add_part\(\s*['\"]mid['\"]\s*,\s*(?P<rect>[^\)]+)\)"
        m = re.search(pat2, out)
        if not m:
            return out, changed
        keyname = "mid"
    else:
        keyname = "mid_wall"

    rect_expr = m.group("rect")

    repl = (
        "for r in range(getattr(self, 'tbl_midwalls', None).rowCount() if getattr(self, 'tbl_midwalls', None) is not None else 1):\n"
        "                # domyślnie: jedna ścianka jak wcześniej\n"
        "                x_off = 0.0\n"
        "                y_off = 0.0\n"
        "                h_custom = 0.0\n"
        "                if getattr(self, 'tbl_midwalls', None) is not None:\n"
        "                    def _cell(rr, cc):\n"
        "                        it = self.tbl_midwalls.item(rr, cc)\n"
        "                        t = (it.text() if it else '0').strip().replace(',', '.')\n"
        "                        try: return float(t)\n"
        "                        except Exception: return 0.0\n"
        "                    x_off = _cell(r, 0)\n"
        "                    y_off = _cell(r, 1)\n"
        "                    h_custom = _cell(r, 2)\n"
        "                rr = " + rect_expr + "\n"
        "                # przesunięcie X (od lewej) + offset od dołu + wysokość\n"
        "                try:\n"
        "                    rr = QtCore.QRectF(rr)\n"
        "                    rr.moveLeft(rr.left() + x_off)\n"
        "                    rr.setBottom(rr.bottom() - y_off)\n"
        "                    if h_custom and h_custom > 0:\n"
        "                        rr.setTop(rr.bottom() - h_custom)\n"
        "                except Exception:\n"
        "                    pass\n"
        "                add_part(f'" + keyname + "_{r}', rr)\n"
    )

    out = out[:m.start()] + repl + out[m.end():]
    changed += 1
    return out, changed

def main():
    txt = FILE.read_text(encoding="utf-8", errors="ignore")
    out = txt
    total = 0

    for fn in [
        ensure_drawer_helper,
        patch_drawer_calcs,
        patch_top_view_front,
        restore_offsets_ui,
        add_multi_midwalls_ui,
        use_midwalls_in_drawing,
    ]:
        out, n = fn(out)
        total += n

    if out == txt:
        print("NO_CHANGES")
        return

    FILE.write_text(out, encoding="utf-8")
    print(f"PATCHED: {FILE} changes={total}")

if __name__ == "__main__":
    main()
