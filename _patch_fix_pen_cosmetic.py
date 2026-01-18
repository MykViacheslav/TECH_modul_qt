import os, re
from pathlib import Path

MOD = os.environ.get("MOD_PATH")
if not MOD:
    raise SystemExit("MOD_PATH env var missing")

p = Path(MOD)
txt = p.read_text(encoding="utf-8", errors="ignore")

# find PartRectItem._update_pen block
m = re.search(r"(?ms)(class\s+PartRectItem\b.*?)(\nclass\s+|\Z)", txt)
if not m:
    raise SystemExit("Cannot find class PartRectItem block")

block = m.group(1)

m2 = re.search(r"(?ms)(def\s+_update_pen\(self\):\s*\n)(.*?)(\n\s*def\s+|\Z)", block)
if not m2:
    raise SystemExit("Cannot find _update_pen in PartRectItem")

head = m2.group(1)
body = m2.group(2)
tail = m2.group(3)

# 1) remove ALL existing pen.setCosmetic(True) inside _update_pen (we'll re-add safely once)
body2 = re.sub(r"(?m)^\s*pen\.setCosmetic\(True\)\s*\n", "", body)

# 2) insert pen.setCosmetic(True) immediately before self.setPen(pen)
def inject(match):
    indent = match.group(1)
    return f"{indent}pen.setCosmetic(True)\n{indent}self.setPen(pen)\n"

body3, n = re.subn(r"(?m)^(\s*)self\.setPen\(pen\)\s*$", inject, body2, count=1)
if n != 1:
    raise SystemExit("Could not find 'self.setPen(pen)' in _update_pen to inject cosmetic")

new_block = block.replace(head + body + tail, head + body3 + tail)
txt2 = txt.replace(block, new_block)

p.write_text(txt2, encoding="utf-8")
print("OK: fixed pen cosmetic placement in PartRectItem._update_pen")
