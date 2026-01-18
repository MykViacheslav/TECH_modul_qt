from __future__ import annotations
from pathlib import Path
from datetime import datetime

p = Path(r"""C:\PythonProject\TECH_modul\TECH_modul_qt\src\tabs\module_widget.py""")
txt = p.read_text(encoding="utf-8", errors="ignore").splitlines(True)

MARK = "# UI COMPACT v12"

if any(MARK in ln for ln in txt):
    print("SKIP: already patched (UI COMPACT v12).")
    raise SystemExit(0)

# helpers: find function block by indent
def find_def(name: str):
    for i, ln in enumerate(txt):
        if ln.lstrip().startswith(f"def {name}("):
            indent = len(ln) - len(ln.lstrip())
            return i, indent
    return None, None

def find_block_end(start: int, base_indent: int):
    for j in range(start + 1, len(txt)):
        ln = txt[j]
        if ln.strip() == "":
            continue
        ind = len(ln) - len(ln.lstrip())
        if ind <= base_indent and not ln.lstrip().startswith("#"):
            return j
    return len(txt)

init_i, init_indent = find_def("__init__")
if init_i is None:
    raise SystemExit("ERROR: def __init__ not found in module_widget.py")

init_end = find_block_end(init_i, init_indent)
block = txt[init_i:init_end]

# 1) Insert view alignment center right after QGraphicsView creation (best-effort)
inserted_align = 0
for k in range(len(block)):
    ln = block[k]
    if "QGraphicsView" in ln and ("self.view" in ln or ".view" in ln) and ("=" in ln):
        # insert after this line (and possibly after a couple of immediate config lines)
        # But safest: immediate insert next line.
        base = " " * (init_indent + 4)
        add = [
            f"{base}{MARK}\n",
            f"{base}try:\n",
            f"{base}    self.view.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)\n",
            f"{base}except Exception:\n",
            f"{base}    pass\n",
        ]
        # inject into txt using absolute index
        abs_pos = init_i + k + 1
        txt[abs_pos:abs_pos] = add
        inserted_align = 1
        break

# 2) Insert compact QSS once, right after first self._refresh_scene() call in __init__
# If not found, append near end of __init__.
qss_lines = []
base = " " * (init_indent + 4)
qss_lines.append(f"{base}{MARK} (styles)\n")
qss_lines.append(f"{base}try:\n")
qss_lines.append(f"{base}    _qss = \"\"\"\n")
qss_lines.append(f"{base}    /* compact inputs */\n")
qss_lines.append(f"{base}    QLineEdit, QSpinBox, QDoubleSpinBox {{\n")
qss_lines.append(f"{base}        min-width: 70px;\n")
qss_lines.append(f"{base}        max-width: 95px;\n")
qss_lines.append(f"{base}        padding: 2px 6px;\n")
qss_lines.append(f"{base}    }}\n")
qss_lines.append(f"{base}    QSpinBox, QDoubleSpinBox {{\n")
qss_lines.append(f"{base}        padding-right: 4px;\n")
qss_lines.append(f"{base}    }}\n")
qss_lines.append(f"{base}    /* bigger checkbox indicator */\n")
qss_lines.append(f"{base}    QCheckBox::indicator {{\n")
qss_lines.append(f"{base}        width: 18px;\n")
qss_lines.append(f"{base}        height: 18px;\n")
qss_lines.append(f"{base}    }}\n")
qss_lines.append(f"{base}    \"\"\"\n")
qss_lines.append(f"{base}    self.setStyleSheet((self.styleSheet() or \"\") + _qss)\n")
qss_lines.append(f"{base}except Exception:\n")
qss_lines.append(f"{base}    pass\n")

insert_pos = None
for k in range(len(block)):
    if "self._refresh_scene" in block[k]:
        insert_pos = init_i + k + 1
        break

if insert_pos is None:
    insert_pos = init_end - 1

txt[insert_pos:insert_pos] = qss_lines

p.write_text("".join(txt), encoding="utf-8")
print("OK: patched UI compact + centered view (v12).")
