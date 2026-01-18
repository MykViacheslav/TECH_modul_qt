import os, re
from pathlib import Path

MOD = os.environ.get("MOD_PATH")
if not MOD:
    raise SystemExit("MOD_PATH env var missing")

p = Path(MOD)
txt = p.read_text(encoding="utf-8", errors="ignore")

# locate PartRectItem._update_pen and remove ONLY pen.setCosmetic(True) inside it
m = re.search(r"(?ms)(class\s+PartRectItem\b.*?)(\nclass\s+|\Z)", txt)
if not m:
    raise SystemExit("Cannot find class PartRectItem")

cls = m.group(1)

m2 = re.search(r"(?ms)(def\s+_update_pen\(self\):\s*\n)(.*?)(\n\s*def\s+|\Z)", cls)
if not m2:
    raise SystemExit("Cannot find _update_pen in PartRectItem")

head, body, tail = m2.group(1), m2.group(2), m2.group(3)

body2, n = re.subn(r"(?m)^\s*pen\.setCosmetic\(True\)\s*\n", "", body)
if n == 0:
    print("No pen.setCosmetic(True) found inside _update_pen (nothing changed).")
else:
    new_cls = cls.replace(head+body+tail, head+body2+tail)
    txt = txt.replace(cls, new_cls)
    p.write_text(txt, encoding="utf-8")
    print(f"OK: removed {n} line(s) pen.setCosmetic(True) inside PartRectItem._update_pen")
