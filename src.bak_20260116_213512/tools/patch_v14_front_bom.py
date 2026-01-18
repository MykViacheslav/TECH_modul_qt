from __future__ import annotations
from pathlib import Path
import re

p = Path(r"""C:\PythonProject\TECH_modul\TECH_modul_qt\src\tabs\module_widget.py""")
lines = p.read_text(encoding="utf-8", errors="ignore").splitlines(True)

MARK = "# FRONT BOM v14"
if any(MARK in ln for ln in lines):
    print("SKIP: already patched v14")
    raise SystemExit(0)

def find_class():
    # find first "class ModuleWidget" or any QWidget-like class (we patch methods inside file globally anyway)
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith("class ") and "ModuleWidget" in ln:
            return i
    return None

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

# ---------- helper getters (inject once near _refresh_scene) ----------
refresh_i, refresh_indent = find_def("_refresh_scene")
if refresh_i is None:
    raise SystemExit("ERROR: _refresh_scene not found")

insert_pos = refresh_i

helper = []
helper.append("    " + MARK + " helpers\n")
helper.append("    def _get_dim_mm_v14(self, key: str, default: float = 0.0) -> float:\n")
helper.append("        \"\"\"Best-effort dimension getter (w/h/d).\"\"\"\n")
helper.append("        key = (key or '').lower()\n")
helper.append("        cand = []\n")
helper.append("        # common attribute names\n")
helper.append("        if key in ('w','width','szerokosc','szerokość'):\n")
helper.append("            cand = ['sp_w','sb_w','spin_w','sp_width','sb_width','spin_width','sp_szer','sb_szer','spin_szer']\n")
helper.append("        elif key in ('h','height','wysokosc','wysokość'):\n")
helper.append("            cand = ['sp_h','sb_h','spin_h','sp_height','sb_height','spin_height','sp_wys','sb_wys','spin_wys']\n")
helper.append("        elif key in ('d','depth','glebokosc','głębokość'):\n")
helper.append("            cand = ['sp_d','sb_d','spin_d','sp_depth','sb_depth','spin_depth','sp_gleb','sb_gleb','spin_gleb']\n")
helper.append("        for nm in cand:\n")
helper.append("            w = getattr(self, nm, None)\n")
helper.append("            if w is not None and hasattr(w, 'value'):\n")
helper.append("                try:\n")
helper.append("                    return float(w.value())\n")
helper.append("                except Exception:\n")
helper.append("                    pass\n")
helper.append("        # fallback: scan all widgets by name\n")
helper.append("        for nm, w in self.__dict__.items():\n")
helper.append("            if not isinstance(nm, str):\n")
helper.append("                continue\n")
helper.append("            nml = nm.lower()\n")
helper.append("            if key == 'w' and ('width' in nml or 'szer' in nml):\n")
helper.append("                if hasattr(w, 'value'):\n")
helper.append("                    try: return float(w.value())\n")
helper.append("                    except Exception: pass\n")
helper.append("            if key == 'h' and ('height' in nml or 'wys' in nml):\n")
helper.append("                if hasattr(w, 'value'):\n")
helper.append("                    try: return float(w.value())\n")
helper.append("                    except Exception: pass\n")
helper.append("            if key == 'd' and ('depth' in nml or 'gleb' in nml):\n")
helper.append("                if hasattr(w, 'value'):\n")
helper.append("                    try: return float(w.value())\n")
helper.append("                    except Exception: pass\n")
helper.append("        return float(default)\n\n")

# inject helpers
lines[insert_pos:insert_pos] = helper

# re-find refresh after insertion (line indices shifted)
refresh_i, refresh_indent = find_def("_refresh_scene")
refresh_end = block_end(refresh_i, refresh_indent)

# ---------- find a function that updates materials table ----------
# Strategy: look for a method that has "setRowCount(0)" and references "mat" or "material"
target_def_i = None
target_def_indent = None
target_end = None
tbl_name = None

for i, ln in enumerate(lines):
    if ln.lstrip().startswith("def "):
        di = i
        indent = len(ln) - len(ln.lstrip())
        end = block_end(di, indent)
        chunk = "".join(lines[di:end]).lower()
        if "setrowcount(0)" in chunk and ("mater" in chunk or "material" in chunk or "tbl_mat" in chunk or "tbl_material" in chunk):
            # guess table attribute name inside this function
            m = re.search(r"self\.(tbl_[a-zA-Z0-9_]*mat[a-zA-Z0-9_]*)", "".join(lines[di:end]))
            if not m:
                m = re.search(r"self\.(tbl_[a-zA-Z0-9_]*material[a-zA-Z0-9_]*)", "".join(lines[di:end]))
            if not m:
                m = re.search(r"self\.(table_[a-zA-Z0-9_]*mat[a-zA-Z0-9_]*)", "".join(lines[di:end]))
            if m:
                tbl_name = m.group(1).split(".")[1]  # tbl attr only
            target_def_i, target_def_indent, target_end = di, indent, end
            break

if target_def_i is None:
    print("WARN: materials-table update function not found. Will patch _on_recalc instead (minimal).")

# ---------- injection block: add front row after materials rows filled ----------
inject = []
inject.append("        " + MARK + " add FRONT row if enabled\n")
inject.append("        try:\n")
inject.append("            _front_on = False\n")
inject.append("            _chk = getattr(self, 'ck_front', None)\n")
inject.append("            if _chk is not None and hasattr(_chk, 'isChecked'):\n")
inject.append("                _front_on = bool(_chk.isChecked())\n")
inject.append("            if _front_on:\n")
inject.append("                W = self._get_dim_mm_v14('w', 0.0)\n")
inject.append("                H = self._get_dim_mm_v14('h', 0.0)\n")
inject.append("                area_m2 = max(0.0, (W/1000.0) * (H/1000.0))\n")
inject.append("                # insert row into materials table (best effort)\n")
inject.append("                tbl = None\n")
if tbl_name:
    inject.append(f"                tbl = getattr(self, '{tbl_name}', None)\n")
else:
    inject.append("                # try common names\n")
    inject.append("                for _nm in ('tbl_mat','tbl_materials','tbl_material','table_materials','table_mat'):\n")
    inject.append("                    _t = getattr(self, _nm, None)\n")
    inject.append("                    if _t is not None and hasattr(_t, 'rowCount'):\n")
    inject.append("                        tbl = _t; break\n")
inject.append("                if tbl is not None:\n")
inject.append("                    from PySide6.QtWidgets import QTableWidgetItem\n")
inject.append("                    r = tbl.rowCount()\n")
inject.append("                    tbl.insertRow(r)\n")
inject.append("                    cols = int(getattr(tbl, 'columnCount')()) if hasattr(tbl, 'columnCount') else 1\n")
inject.append("                    # col0: name, col1: qty/area, col2: unit\n")
inject.append("                    if cols >= 1:\n")
inject.append("                        tbl.setItem(r, 0, QTableWidgetItem('Front'))\n")
inject.append("                    if cols >= 2:\n")
inject.append("                        tbl.setItem(r, 1, QTableWidgetItem(f\"{area_m2:.3f}\"))\n")
inject.append("                    if cols >= 3:\n")
inject.append("                        tbl.setItem(r, 2, QTableWidgetItem('m²'))\n")
inject.append("        except Exception:\n")
inject.append("            pass\n")

if target_def_i is not None:
    # insert near end of that function (before return / end)
    # place it just before last non-empty line to avoid breaking indentation
    indent = " " * (target_def_indent + 4)
    # find safe insertion point: before final blank line / before 'return' if present
    ins = target_end - 1
    for j in range(target_end-1, target_def_i, -1):
        if lines[j].strip().startswith("return"):
            ins = j
            break
        if lines[j].strip() != "":
            ins = j + 1
            break
    # indent inject properly
    inj2 = [indent + ln if ln.strip() else ln for ln in inject]
    lines[ins:ins] = inj2
    print(f"OK: inserted FRONT row into materials update function at line ~{ins+1}")
else:
    # fallback: patch _on_recalc (after refreshing tables if exists)
    on_i, on_indent = find_def("_on_recalc")
    if on_i is None:
        raise SystemExit("ERROR: neither materials update func nor _on_recalc found")
    on_end = block_end(on_i, on_indent)
    # insert before end of _on_recalc
    ins = on_end - 1
    indent = " " * (on_indent + 4)
    inj2 = [indent + ln if ln.strip() else ln for ln in inject]
    lines[ins:ins] = inj2
    print("OK: inserted FRONT row into _on_recalc fallback")

p.write_text("".join(lines), encoding="utf-8")
print("DONE: v14 applied.")
