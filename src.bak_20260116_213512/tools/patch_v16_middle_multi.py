from __future__ import annotations
from pathlib import Path
import re

p = Path(r"""C:\PythonProject\TECH_modul\TECH_modul_qt\src\tabs\module_widget.py""")
txt = p.read_text(encoding="utf-8", errors="ignore")

MARK = "# MIDDLE MULTI v16"
if MARK in txt:
    print("SKIP: v16 already applied")
    raise SystemExit(0)

# ---------------------------------------------------------------------
# 1) UI: dodaj in_middle_count + in_middle_offsets obok ck_middle
# ---------------------------------------------------------------------
# Szukamy miejsca gdzie tworzysz:
# self.ck_middle     = chk("Środkowa ścianka", False)
# i wstawiamy po tym dwie kontrolki + opis.
ui_pat = r'(self\.ck_middle\s*=\s*chk\("Środkowa ścianka",\s*False\)\s*\n)'
m = re.search(ui_pat, txt)
if not m:
    raise SystemExit("ERROR: Nie znalazłem self.ck_middle = chk(...) w _build_ui")

ui_insert = m.group(1) + (
    "        " + MARK + " UI\n"
    "        self.in_middle_count = QtWidgets.QSpinBox(); self.in_middle_count.setRange(1, 10); self.in_middle_count.setValue(1); prep_spin(self.in_middle_count)\n"
    "        self.in_middle_offsets = QtWidgets.QLineEdit(); self.in_middle_offsets.setPlaceholderText('Ofsety mm: np. 200,380 (od lewego wew. boku)')\n"
)

txt = txt[:m.end()] + ui_insert + txt[m.end():]

# W gridzie dodajemy je w wierszu ck_middle (żeby było czytelnie)
# Szukamy: grid.addWidget(self.ck_middle,     3, 0)
grid_pat = r'(grid\.addWidget\(self\.ck_middle,\s*3,\s*0\)\s*\n)'
m = re.search(grid_pat, txt)
if not m:
    raise SystemExit("ERROR: Nie znalazłem grid.addWidget(self.ck_middle, 3, 0)")

grid_insert = (
    m.group(1) +
    "        grid.addWidget(QtWidgets.QLabel('Ilość:'), 3, 1)\n"
    "        grid.addWidget(self.in_middle_count, 3, 2)\n"
    "        grid.addWidget(self.in_middle_offsets, 4, 0, 1, 3)\n"
)
txt = txt[:m.start()] + grid_insert + txt[m.end():]

#  Hook signals: dopisz do listy hook(w) zestaw
hook_pat = r'(self\.ck_side_left,\s*self\.ck_side_right,\s*self\.ck_top,\s*self\.ck_bottom,\s*self\.ck_front,\s*self\.ck_back,\s*self\.ck_middle,\s*self\.ck_shelves,)'
txt = re.sub(hook_pat, r'\1' + "\n            self.in_middle_count, self.in_middle_offsets,", txt, count=1)

# ---------------------------------------------------------------------
# 2) State load/save: dopisz middle_count + middle_offsets
# ---------------------------------------------------------------------
load_pat = r'(self\.ck_middle\.setChecked\(b\("part_middle",\s*"false"\)\)\s*\n)'
m = re.search(load_pat, txt)
if not m:
    raise SystemExit("ERROR: Nie znalazłem miejsca po ck_middle.setChecked(...) w _load_state")

load_insert = m.group(1) + (
    "            " + MARK + " state load\n"
    "            if hasattr(self, 'in_middle_count'):\n"
    "                self.in_middle_count.setValue(safe_int(s.value('middle_count', 1), 1))\n"
    "            if hasattr(self, 'in_middle_offsets'):\n"
    "                self.in_middle_offsets.setText(str(s.value('middle_offsets', '')))\n"
)
txt = txt[:m.end()] + load_insert + txt[m.end():]

save_pat = r'(s\.setValue\("part_middle",\s*"true"\s*if\s*self\.ck_middle\.isChecked\(\)\s*else\s*"false"\)\s*\n)'
m = re.search(save_pat, txt)
if not m:
    raise SystemExit("ERROR: Nie znalazłem miejsca po part_middle w _save_state")

save_insert = m.group(1) + (
    "            " + MARK + " state save\n"
    "            if hasattr(self, 'in_middle_count'):\n"
    "                s.setValue('middle_count', int(self.in_middle_count.value()))\n"
    "            if hasattr(self, 'in_middle_offsets'):\n"
    "                s.setValue('middle_offsets', self.in_middle_offsets.text())\n"
)
txt = txt[:m.end()] + save_insert + txt[m.end():]

# ---------------------------------------------------------------------
# 3) _rebuild_parts: generuj middle_1..middle_n + zapisz pozycje X do rysunku
# ---------------------------------------------------------------------
# Wstawimy pomocniczy parser offsetów i listę self._middle_xs_mm
# Szukamy: middle_on = bool(self.ck_middle.isChecked())
rb_pat = r'(middle_on\s*=\s*bool\(self\.ck_middle\.isChecked\(\)\)\s*\n)'
m = re.search(rb_pat, txt)
if not m:
    raise SystemExit("ERROR: Nie znalazłem middle_on = bool(self.ck_middle...) w _rebuild_parts")

rb_insert = m.group(1) + (
    "        " + MARK + " middle count/offsets\n"
    "        middle_count = 1\n"
    "        if hasattr(self, 'in_middle_count'):\n"
    "            try:\n"
    "                middle_count = max(1, int(self.in_middle_count.value()))\n"
    "            except Exception:\n"
    "                middle_count = 1\n"
    "        raw_off = ''\n"
    "        if hasattr(self, 'in_middle_offsets'):\n"
    "            try:\n"
    "                raw_off = (self.in_middle_offsets.text() or '').strip()\n"
    "            except Exception:\n"
    "                raw_off = ''\n"
    "        offsets = []\n"
    "        if raw_off:\n"
    "            for tok in raw_off.replace(';', ',').split(','):\n"
    "                tok = tok.strip()\n"
    "                if not tok:\n"
    "                    continue\n"
    "                try:\n"
    "                    offsets.append(float(tok))\n"
    "                except Exception:\n"
    "                    pass\n"
    "        self._middle_xs_mm = []  # od LEWEGO wewnętrznego boku\n"
)

txt = txt[:m.end()] + rb_insert + txt[m.end():]

# Teraz podmień blok tworzenia "middle" (single) na pętlę.
# Szukamy fragmentu:
# if middle_on:
#     ensure("middle", ...)
mid_pat = r'(?ms)\n\s*# Środkowa: A=D, B=innerH, T=t\s*\n\s*if middle_on:\s*\n\s*ensure\("middle",\s*"Środkowa ścianka",\s*D,\s*innerH,\s*t,\s*carcass_mat\)\s*\n'
m = re.search(mid_pat, txt)
if not m:
    raise SystemExit("ERROR: Nie znalazłem bloku 'Środkowa' w _rebuild_parts (single).")

mid_repl = (
    "\n        # Środkowe: A=D, B=innerH, T=t (wiele szt.)\n"
    "        if middle_on:\n"
    "            # jeśli podane ofsety – użyj ich (obcięte do zakresu), inaczej rozłóż równomiernie\n"
    "            xs = []\n"
    "            inner_start = (t if has_L else 0.0)\n"
    "            # maks X żeby ścianka się zmieściła\n"
    "            x_min = 0.0\n"
    "            x_max = max(0.0, innerW - t)\n"
    "            if offsets:\n"
    "                for x in offsets[:middle_count]:\n"
    "                    xs.append(clamp(float(x), x_min, x_max))\n"
    "            else:\n"
    "                # równomiernie: dzielimy na (count+1) pól i bierzemy środki przegród\n"
    "                step = (innerW - t) / float(middle_count + 1) if middle_count > 0 else 0.0\n"
    "                for i in range(1, middle_count + 1):\n"
    "                    xs.append(clamp(step * i, x_min, x_max))\n"
    "            # usuń duplikaty blisko siebie\n"
    "            xs2 = []\n"
    "            for x in sorted(xs):\n"
    "                if not xs2 or abs(x - xs2[-1]) > 0.5:\n"
    "                    xs2.append(x)\n"
    "            xs = xs2\n"
    "            self._middle_xs_mm = xs\n"
    "            for i, x in enumerate(xs, start=1):\n"
    "                ensure(f\"middle_{i}\", f\"Środkowa ścianka {i}\", D, innerH, t, carcass_mat)\n"
)
txt = re.sub(mid_pat, mid_repl, txt, count=1)

# ---------------------------------------------------------------------
# 4) _refresh_scene: rysuj middle_1..middle_n na podstawie self._middle_xs_mm
# ---------------------------------------------------------------------
# Zamieniamy dotychczasowe rysowanie pojedynczego "middle"
# Szukamy bloku:
# if middle_on and "middle" in self.parts:
#    x = ...
front_mid_pat = r'(?ms)\n\s*if middle_on and "middle" in self\.parts:\s*\n\s*x = .*?\n\s*y0 = .*?\n\s*r = QtCore\.QRectF\(.*?\)\n\s*add_part\("middle", r\)\s*\n'
m = re.search(front_mid_pat, txt)
if not m:
    raise SystemExit("ERROR: Nie znalazłem rysowania pojedynczego middle w _refresh_scene")

front_mid_repl = (
    "\n            # środkowe ścianki (wiele)\n"
    "            if middle_on:\n"
    "                xs = getattr(self, '_middle_xs_mm', []) or []\n"
    "                y0 = (t if has_T else 0.0)\n"
    "                for i, xrel in enumerate(xs, start=1):\n"
    "                    key = f\"middle_{i}\"\n"
    "                    if key in self.parts:\n"
    "                        x = (t if has_L else 0.0) + float(xrel)\n"
    "                        r = QtCore.QRectF(front_origin.x() + x, front_origin.y() + y0, t, innerH)\n"
    "                        add_part(key, r)\n"
)
txt = re.sub(front_mid_pat, front_mid_repl, txt, count=1)

# top view: też był single middle rect
top_mid_pat = r'(?ms)\n\s*if middle_on and "middle" in self\.parts:\s*\n\s*x = .*?\n\s*self\.scene\.addRect\(QtCore\.QRectF\(top_origin\.x\(\) \+ x, top_origin\.y\(\) \+ 0, t, D\), pen_thin\)\s*\n'
m = re.search(top_mid_pat, txt)
if not m:
    raise SystemExit("ERROR: Nie znalazłem top-view rysowania pojedynczego middle w _refresh_scene")

top_mid_repl = (
    "\n            if middle_on:\n"
    "                xs = getattr(self, '_middle_xs_mm', []) or []\n"
    "                for i, xrel in enumerate(xs, start=1):\n"
    "                    x = (t if has_L else 0.0) + float(xrel)\n"
    "                    self.scene.addRect(QtCore.QRectF(top_origin.x() + x, top_origin.y() + 0, t, D), pen_thin)\n"
)
txt = re.sub(top_mid_pat, top_mid_repl, txt, count=1)

# ---------------------------------------------------------------------
p.write_text(txt, encoding="utf-8")
print("OK: v16 applied (multi-middle walls + offsets).")

