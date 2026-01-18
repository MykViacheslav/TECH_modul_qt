from __future__ import annotations
from pathlib import Path
import re

p = Path(r"""C:\PythonProject\TECH_modul\TECH_modul_qt\src\tabs\module_widget.py""")
txt = p.read_text(encoding="utf-8", errors="ignore")

MARK = "# FRONT BOM v15"
if MARK in txt:
    print("SKIP: already patched v15")
    raise SystemExit(0)

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
    raise SystemExit("ERROR: def _on_recalc not found")

on_end = block_end(on_i, on_indent)

# 1) spróbuj wstrzyknąć zaraz po nagłówku BOM: lines.append("Moduł: ...")
insert_at = None
for j in range(on_i, on_end):
    ln = lines[j]
    if "lines.append" in ln and ("Modu" in ln or "Moduł" in ln):
        insert_at = j + 1
        break

# 2) fallback: przed txt_bom.setPlainText / setText
if insert_at is None:
    for j in range(on_i, on_end):
        ln = lines[j]
        if ("txt_bom" in ln) and (".setPlainText(" in ln or ".setText(" in ln):
            insert_at = j
            break

# 3) last resort: koniec funkcji
if insert_at is None:
    insert_at = on_end - 1

indent = " " * (on_indent + 4)

inject = []
inject.append(indent + MARK + "\n")
inject.append(indent + "try:\n")
inject.append(indent + "    _front_on = False\n")
inject.append(indent + "    if hasattr(self, 'ck_front') and self.ck_front is not None:\n")
inject.append(indent + "        try:\n")
inject.append(indent + "            _front_on = bool(self.ck_front.isChecked())\n")
inject.append(indent + "        except Exception:\n")
inject.append(indent + "            _front_on = False\n")
inject.append(indent + "\n")
inject.append(indent + "    if _front_on:\n")
inject.append(indent + "        W = float(self.in_W.value()) if hasattr(self, 'in_W') else 0.0\n")
inject.append(indent + "        H = float(self.in_H.value()) if hasattr(self, 'in_H') else 0.0\n")
inject.append(indent + "        area_m2 = max(0.0, (W/1000.0) * (H/1000.0))\n")
inject.append(indent + "        cnt = int(self.in_front_count.value()) if hasattr(self, 'in_front_count') else 1\n")
inject.append(indent + "        mat = ''\n")
inject.append(indent + "        if hasattr(self, 'cb_front_mat') and self.cb_front_mat is not None:\n")
inject.append(indent + "            try:\n")
inject.append(indent + "                mat = self.cb_front_mat.currentText().strip()\n")
inject.append(indent + "            except Exception:\n")
inject.append(indent + "                mat = ''\n")
inject.append(indent + "        lines.append(f\"Front: {area_m2:.3f} m2  | szt: {cnt}  | mat: {mat or '-'}\")\n")
inject.append(indent + "except Exception:\n")
inject.append(indent + "    pass\n\n")

lines[insert_at:insert_at] = inject
p.write_text("".join(lines), encoding="utf-8")

print("OK: v15 injected at line ~{}".format(insert_at + 1))
