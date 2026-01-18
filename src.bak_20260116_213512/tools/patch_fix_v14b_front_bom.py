from __future__ import annotations
from pathlib import Path
import re

p = Path(r"""C:\PythonProject\TECH_modul\TECH_modul_qt\src\tabs\module_widget.py""")
txt = p.read_text(encoding="utf-8", errors="ignore")

# -----------------------------
# 1) CLEANUP: remove previous v14 blocks that may break indentation
# -----------------------------
# remove helper method block (class-level)
txt2 = re.sub(
    r'(?ms)^[ \t]*# FRONT BOM v14 helpers\s*\n^[ \t]*def _get_dim_mm_v14\(.*?\n(?=^[ \t]*def |\Z)',
    '',
    txt
)

# remove injected block (method-level) starting with marker and ending with "except...pass"
txt2 = re.sub(
    r'(?ms)^[ \t]*# FRONT BOM v14 add FRONT row if enabled\s*\n.*?^[ \t]*except Exception:\s*\n^[ \t]*pass\s*\n',
    '',
    txt2
)

# if nothing changed, keep going (we still reinject clean)
txt = txt2

lines = txt.splitlines(True)

def find_def(name: str):
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith(f"def {name}("):
            indent = len(ln) - len(ln.lstrip())
            return i, indent
    return None, None

def block_end(start: int, base_indent: int):
    for j in range(start+1, len(lines)):
        ln = lines[j]
        if ln.strip() == "":
            continue
        ind = len(ln) - len(ln.lstrip())
        if ind <= base_indent and not ln.lstrip().startswith("#"):
            return j
    return len(lines)

on_i, on_indent = find_def("_on_recalc")
if on_i is None:
    raise SystemExit("ERROR: def _on_recalc not found (cannot attach front->BOM)")

on_end = block_end(on_i, on_indent)

# insertion point: before last non-empty line inside _on_recalc (or before return)
ins = on_end - 1
for j in range(on_end-1, on_i, -1):
    s = lines[j].strip()
    if s.startswith("return"):
        ins = j
        break
    if s != "":
        ins = j + 1
        break

indent = " " * (on_indent + 4)

# -----------------------------
# 2) REINJECT: clean & correct indent block (NO hardcoded leading spaces)
# -----------------------------
inject = []
inject.append(indent + "# FRONT BOM v14 add FRONT row if enabled\n")
inject.append(indent + "try:\n")
inject.append(indent + "    # FRONT enabled?\n")
inject.append(indent + "    _front_on = False\n")
inject.append(indent + "    _chk = getattr(self, 'ck_front', None)\n")
inject.append(indent + "    if _chk is not None and hasattr(_chk, 'isChecked'):\n")
inject.append(indent + "        _front_on = bool(_chk.isChecked())\n")
inject.append(indent + "\n")
inject.append(indent + "    if _front_on:\n")
inject.append(indent + "        # best-effort dimension getter\n")
inject.append(indent + "        def _dim_mm(_key: str, _default: float = 0.0) -> float:\n")
inject.append(indent + "            k = (_key or '').lower()\n")
inject.append(indent + "            # try common spinboxes by attribute name\n")
inject.append(indent + "            candidates = []\n")
inject.append(indent + "            if k in ('w','width','szer','szerokosc','szerokość'):\n")
inject.append(indent + "                candidates = ['sp_w','sb_w','spin_w','sp_width','sb_width','spin_width','sp_szer','sb_szer','spin_szer']\n")
inject.append(indent + "            elif k in ('h','height','wys','wysokosc','wysokość'):\n")
inject.append(indent + "                candidates = ['sp_h','sb_h','spin_h','sp_height','sb_height','spin_height','sp_wys','sb_wys','spin_wys']\n")
inject.append(indent + "            elif k in ('d','depth','gleb','glebokosc','głębokość'):\n")
inject.append(indent + "                candidates = ['sp_d','sb_d','spin_d','sp_depth','sb_depth','spin_depth','sp_gleb','sb_gleb','spin_gleb']\n")
inject.append(indent + "            for nm in candidates:\n")
inject.append(indent + "                w = getattr(self, nm, None)\n")
inject.append(indent + "                if w is not None and hasattr(w, 'value'):\n")
inject.append(indent + "                    try:\n")
inject.append(indent + "                        return float(w.value())\n")
inject.append(indent + "                    except Exception:\n")
inject.append(indent + "                        pass\n")
inject.append(indent + "            # fallback: scan all attributes\n")
inject.append(indent + "            for nm, w in self.__dict__.items():\n")
inject.append(indent + "                if not isinstance(nm, str):\n")
inject.append(indent + "                    continue\n")
inject.append(indent + "                nml = nm.lower()\n")
inject.append(indent + "                if k == 'w' and ('width' in nml or 'szer' in nml):\n")
inject.append(indent + "                    if hasattr(w, 'value'):\n")
inject.append(indent + "                        try: return float(w.value())\n")
inject.append(indent + "                        except Exception: pass\n")
inject.append(indent + "                if k == 'h' and ('height' in nml or 'wys' in nml):\n")
inject.append(indent + "                    if hasattr(w, 'value'):\n")
inject.append(indent + "                        try: return float(w.value())\n")
inject.append(indent + "                        except Exception: pass\n")
inject.append(indent + "                if k == 'd' and ('depth' in nml or 'gleb' in nml):\n")
inject.append(indent + "                    if hasattr(w, 'value'):\n")
inject.append(indent + "                        try: return float(w.value())\n")
inject.append(indent + "                        except Exception: pass\n")
inject.append(indent + "            return float(_default)\n")
inject.append(indent + "\n")
inject.append(indent + "        W = _dim_mm('w', 0.0)\n")
inject.append(indent + "        H = _dim_mm('h', 0.0)\n")
inject.append(indent + "        area_m2 = max(0.0, (W/1000.0) * (H/1000.0))\n")
inject.append(indent + "\n")
inject.append(indent + "        # find materials table (common names)\n")
inject.append(indent + "        tbl = None\n")
inject.append(indent + "        for _nm in ('tbl_mat','tbl_materials','tbl_material','table_materials','table_mat','tbl_bom','tbl_qty'):\n")
inject.append(indent + "            _t = getattr(self, _nm, None)\n")
inject.append(indent + "            if _t is not None and hasattr(_t, 'rowCount') and hasattr(_t, 'insertRow'):\n")
inject.append(indent + "                tbl = _t\n")
inject.append(indent + "                break\n")
inject.append(indent + "\n")
inject.append(indent + "        if tbl is not None:\n")
inject.append(indent + "            from PySide6.QtWidgets import QTableWidgetItem\n")
inject.append(indent + "            r = tbl.rowCount()\n")
inject.append(indent + "            tbl.insertRow(r)\n")
inject.append(indent + "            cols = int(tbl.columnCount()) if hasattr(tbl, 'columnCount') else 1\n")
inject.append(indent + "            if cols >= 1:\n")
inject.append(indent + "                tbl.setItem(r, 0, QTableWidgetItem('Front'))\n")
inject.append(indent + "            if cols >= 2:\n")
inject.append(indent + "                tbl.setItem(r, 1, QTableWidgetItem(f\"{area_m2:.3f}\"))\n")
inject.append(indent + "            if cols >= 3:\n")
inject.append(indent + "                tbl.setItem(r, 2, QTableWidgetItem('m²'))\n")
inject.append(indent + "except Exception:\n")
inject.append(indent + "    pass\n\n")

lines[ins:ins] = inject

p.write_text("".join(lines), encoding="utf-8")
print(f"OK: v14b cleanup + reinject done. Inserted at ~line {ins+1}.")
