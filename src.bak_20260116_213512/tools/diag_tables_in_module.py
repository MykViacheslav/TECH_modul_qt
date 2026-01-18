from __future__ import annotations
from pathlib import Path
import re

p = Path(r"""C:\PythonProject\TECH_modul\TECH_modul_qt\src\tabs\module_widget.py""")
txt = p.read_text(encoding="utf-8", errors="ignore")

# znajdź linie typu: self.NAZWA = QTableWidget(...
rows = []
for i, ln in enumerate(txt.splitlines(), start=1):
    m = re.search(r"\bself\.(\w+)\s*=\s*QTableWidget\s*\(", ln)
    if m:
        rows.append((i, m.group(1), ln.strip()))

print("QTableWidget fields in module_widget.py:")
for i, name, line in rows:
    print(f"  line {i}: self.{name} = ...  |  {line}")

print("\nIf you paste these names here, I'll bind FRONT row to the correct table 100%.")
