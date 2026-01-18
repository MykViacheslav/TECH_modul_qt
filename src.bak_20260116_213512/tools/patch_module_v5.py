from __future__ import annotations
from pathlib import Path
import re

FILE = Path(r"""C:\PythonProject\TECH_modul\TECH_modul_qt\src\tabs\module_widget.py""")

def subn(text: str, pattern: str, repl: str, flags=re.S):
    return re.subn(pattern, repl, text, flags=flags)

def patch_scale(txt: str) -> tuple[str,int]:
    # remove our previous line: self.view.scale(1.25, 1.25)
    # (back to "jedynka" after fitInView)
    out, n = subn(txt, r"(?m)^\s*self\.view\.scale\(\s*1\.25\s*,\s*1\.25\s*\)\s*\r?\n", "")
    # also remove any scale(1.35...) variants we might have tried
    out, n2 = subn(out, r"(?m)^\s*self\.view\.scale\(\s*1\.\d+\s*,\s*1\.\d+\s*\)\s*\r?\n", "")
    return out, (n + n2)

def patch_shelves_rule(txt: str) -> tuple[str,int]:
    out = txt
    changed = 0
    # revert forced min=1 variants back to "value or 0"
    out2 = out.replace(
        "shelves_cnt = max(1, int(self.in_shelves.value())) if shelves_on else 0",
        "shelves_cnt = int(self.in_shelves.value()) if shelves_on else 0"
    )
    if out2 != out:
        changed += 1
        out = out2
    out2 = out.replace(
        "shelves_cnt = max(1, int(self.in_shelves.value())) if self.ck_shelves.isChecked() else 0",
        "shelves_cnt = int(self.in_shelves.value()) if self.ck_shelves.isChecked() else 0"
    )
    if out2 != out:
        changed += 1
        out = out2
    return out, changed

def patch_drawer_std(txt: str) -> tuple[str,int]:
    # ensure helper exists and uses correct standard list (includes 500) + clearance 10mm
    out = txt
    changed = 0

    if "def _drawer_std_length" in out:
        # replace function body robustly
        pat = r"def\s+_drawer_std_length\([^\)]*\)\s*->\s*int\s*:\s*\n(?:\s+.*\n)+?(?=\n\S|\Z)"
        m = re.search(pat, out, flags=re.S)
        if m:
            repl = (
                "def _drawer_std_length(depth_mm: float) -> int:\n"
                "    \"\"\"Dobór długości szuflady: luz z tyłu 10 mm, standardy (PL/UE).\"\"\"\n"
                "    usable = max(0.0, float(depth_mm) - 10.0)\n"
                "    std = [250, 270, 300, 350, 400, 450, 500, 550, 600]\n"
                "    ok = [x for x in std if x <= usable]\n"
                "    return int(ok[-1]) if ok else 0\n\n"
            )
            out = out[:m.start()] + repl + out[m.end():]
            changed += 1
    else:
        # inject near top (after imports) - safe
        out, n = subn(
            out,
            r"(^from __future__.*?\n)(.*?)(\n\n)",
            r"\1\2\3"
            "def _drawer_std_length(depth_mm: float) -> int:\n"
            "    \"\"\"Dobór długości szuflady: luz z tyłu 10 mm, standardy (PL/UE).\"\"\"\n"
            "    usable = max(0.0, float(depth_mm) - 10.0)\n"
            "    std = [250, 270, 300, 350, 400, 450, 500, 550, 600]\n"
            "    ok = [x for x in std if x <= usable]\n"
            "    return int(ok[-1]) if ok else 0\n\n",
            flags=re.S
        )
        if n:
            changed += 1

    # replace common drawer length assignments
    before = out
    out = re.sub(r"\bdrawer_len\b\s*=\s*int\(\s*D\s*-\s*50\s*\)", "drawer_len = _drawer_std_length(D)", out)
    out = re.sub(r"\bdrawer_len\b\s*=\s*int\(\s*D\s*-\s*10\s*\)", "drawer_len = _drawer_std_length(D)", out)
    out = re.sub(r"\bdrawer_len\b\s*=\s*D\s*-\s*50\b", "drawer_len = _drawer_std_length(D)", out)
    out = re.sub(r"\bdrawer_len\b\s*=\s*D\s*-\s*10\b", "drawer_len = _drawer_std_length(D)", out)
    if out != before:
        changed += 1

    return out, changed

def patch_drawer_brands(txt: str) -> tuple[str,int]:
    out = txt
    changed = 0

    # Try to find cb_drawer_brand.addItems([...])
    pat = r"(self\.cb_drawer_brand\.addItems\()\s*\[[^\]]*\]\s*(\))"
    m = re.search(pat, out, flags=re.S)
    brands = ["Blum", "Hettich", "Sevroll", "Strong", "GTV", "Rejs"]
    if m:
        repl = r"\1" + str(brands) + r"\2"
        out2 = re.sub(pat, repl, out, flags=re.S, count=1)
        if out2 != out:
            out = out2
            changed += 1
    else:
        # fallback: if there is a list defined like DRAWER_BRANDS = [...]
        pat2 = r"(DRAWER_BRANDS\s*=\s*)\[[^\]]*\]"
        if re.search(pat2, out):
            out2 = re.sub(pat2, r"\1" + str(brands), out, count=1)
            if out2 != out:
                out = out2
                changed += 1

    return out, changed

def patch_top_front_strip(txt: str) -> tuple[str,int]:
    """
    Add a thin 'front strip' rectangle in TOP VIEW if front exists.
    We inject right after top_rect is computed (best-effort).
    """
    out = txt
    changed = 0

    if "front_top_strip" in out:
        return out, changed

    # Look for "top_rect = QtCore.QRectF(" line and inject after it
    pat = r"(top_rect\s*=\s*QtCore\.QRectF\([^\n]*\)\s*\n)"
    m = re.search(pat, out)
    if not m:
        return out, changed

    inject = (
        m.group(1)
        + "            # front strip in TOP VIEW (żeby front był widoczny z góry)\n"
        + "            try:\n"
        + "                front_on = bool(front_on)\n"
        + "            except Exception:\n"
        + "                front_on = False\n"
        + "            if front_on:\n"
        + "                strip_h = max(8.0, min(14.0, top_rect.height() * 0.08))\n"
        + "                front_top_strip = QtCore.QRectF(top_rect.left(), top_rect.top(), top_rect.width(), strip_h)\n"
        + "                add_part('front_top', front_top_strip)\n"
    )
    out = out[:m.start()] + inject + out[m.end():]
    changed += 1
    return out, changed

def patch_clickable_elements_list(txt: str) -> tuple[str,int]:
    """
    Add a QListWidget inside 'Elementy korpusu' section and connect click -> select item in scene.
    Best-effort:
    - We inject list widget after groupbox for elements exists (search gb_elements / Elementy korpusu title).
    - We inject helper method _select_part_by_key scanning scene items (PartRectItem has part_key).
    """
    out = txt
    changed = 0

    if "_select_part_by_key" in out and "self.lst_parts" in out:
        return out, changed

    # 1) inject helper method inside class (before export_state or at end of class)
    # best anchor: "def export_state" inside Tab
    if "def export_state" in out and "_select_part_by_key" not in out:
        out = out.replace(
            "    def export_state",
            "    def _select_part_by_key(self, key: str) -> None:\n"
            "        # zaznacz element na rysunku jak po kliknięciu\n"
            "        try:\n"
            "            for it in self.scene.items():\n"
            "                if hasattr(it, 'part_key') and getattr(it, 'part_key') == key:\n"
            "                    it.setSelected(True)\n"
            "                    # przewiń widok do elementu\n"
            "                    try:\n"
            "                        self.view.centerOn(it)\n"
            "                    except Exception:\n"
            "                        pass\n"
            "                    return\n"
            "        except Exception:\n"
            "            pass\n\n"
            "    def export_state"
        )
        changed += 1

    # 2) inject list widget in UI: find a safe place: after the 'elements' groupbox is added to layout
    # We try: "pl.addWidget(self.gb_elements)" or group name variants.
    candidates = [
        "pl.addWidget(self.gb_elements)\n",
        "pl.addWidget(self.gb_parts)\n",
        "pl.addWidget(self.gb_corpus_parts)\n",
    ]
    inserted = False
    for anchor in candidates:
        if anchor in out and "self.lst_parts" not in out:
            insert = (
                anchor
                + "\n        # Elementy klikane (jak klik po rysunku)\n"
                + "        self.lst_parts = QtWidgets.QListWidget()\n"
                + "        self.lst_parts.setMaximumHeight(170)\n"
                + "        self.lst_parts.addItems([\n"
                + "            \"Bok lewy\", \"Bok prawy\", \"Wieniec górny\", \"Wieniec dolny\",\n"
                + "            \"Ścianka środkowa\", \"Półki\", \"Plecy\", \"Front\"\n"
                + "        ])\n"
                + "        self.lst_parts.itemClicked.connect(self._on_part_list_clicked)\n"
                + "        pl.addWidget(self.lst_parts)\n"
            )
            out = out.replace(anchor, insert)
            inserted = True
            changed += 1
            break

    # 3) add handler mapping label->key (best effort keys used in drawing)
    if inserted and "_on_part_list_clicked" not in out:
        out = out.replace(
            "    def export_state",
            "    def _on_part_list_clicked(self, item) -> None:\n"
            "        name = (item.text() or '').strip().lower()\n"
            "        # map UI name -> internal key (best-effort)\n"
            "        mapping = {\n"
            "            'bok lewy': 'side_left',\n"
            "            'bok prawy': 'side_right',\n"
            "            'wieniec górny': 'top',\n"
            "            'wieniec dolny': 'bottom',\n"
            "            'ścianka środkowa': 'mid_wall',\n"
            "            'półki': 'shelf',\n"
            "            'plecy': 'back',\n"
            "            'front': 'front_0',\n"
            "        }\n"
            "        key = mapping.get(name)\n"
            "        if key:\n"
            "            self._select_part_by_key(key)\n\n"
            "    def export_state"
        )
        changed += 1

    return out, changed

def patch_hide_module_qty(txt: str) -> tuple[str,int]:
    """
    Hide 'Ilość modułu' field if present. Best effort:
    - if label text exists, we disable the spinbox next lines if easily detectable.
    """
    out = txt
    changed = 0

    if "Ilość modułu" not in out:
        return out, changed

    # Simple approach: if we see setText("Ilość modułu") or QLabel("Ilość modułu") with a paired widget variable,
    # we can't reliably parse. Instead: just set any spinbox named in_qty_module or similar to 1 and hide it.
    patterns = [
        r"self\.(in_qty_module|sp_qty_module|sb_qty_module)\s*=\s*QtWidgets\.(QSpinBox|QDoubleSpinBox)\(\)",
        r"self\.(in_module_qty|sp_module_qty|sb_module_qty)\s*=\s*QtWidgets\.(QSpinBox|QDoubleSpinBox)\(\)",
    ]
    for pat in patterns:
        if re.search(pat, out):
            # after creation, add config lines
            out = re.sub(
                pat,
                lambda m: m.group(0)
                          + "\n        self." + m.group(1) + ".setValue(1)\n"
                          + "        self." + m.group(1) + ".setEnabled(False)\n"
                          + "        self." + m.group(1) + ".setVisible(False)\n",
                out,
                count=1
            )
            changed += 1
            break

    return out, changed

def main():
    txt = FILE.read_text(encoding="utf-8", errors="ignore")
    out = txt
    total = 0

    for fn in [
        patch_scale,
        patch_shelves_rule,
        patch_drawer_std,
        patch_drawer_brands,
        patch_top_front_strip,
        patch_clickable_elements_list,
        patch_hide_module_qty,
    ]:
        out, n = fn(out)
        total += n

    if out == txt:
        print("NO_CHANGES")
        return

    FILE.write_text(out, encoding="utf-8")
    print(f"PATCHED: {FILE}  changes={total}")

if __name__ == "__main__":
    main()
