import os, re
from pathlib import Path

MOD = os.environ.get("MOD_PATH")
if not MOD:
    raise SystemExit("MOD_PATH env var missing")

p = Path(MOD)
txt = p.read_text(encoding="utf-8", errors="ignore")

# Find PartRectItem class block
m = re.search(r"(?ms)(class\s+PartRectItem\b.*?)(\nclass\s+|\Z)", txt)
if not m:
    raise SystemExit("Cannot find class PartRectItem")
cls = m.group(1)

# Find def _update_pen inside the class and replace it entirely
pat = re.compile(
    r"(?ms)^(?P<indent>[ \t]+)def\s+_update_pen\(self\):\s*\n"
    r"(?P<body>.*?)(?=^(?P=indent)def\s+|\Z)",
    re.MULTILINE,
)
m2 = pat.search(cls)
if not m2:
    raise SystemExit("Cannot find _update_pen inside PartRectItem")

indent = m2.group("indent")

new_block = (
f"{indent}def _update_pen(self):\n"
f"{indent}    # Always assign pen (prevents UnboundLocalError)\n"
f"{indent}    if getattr(self, '_selected', False):\n"
f"{indent}        pen = QtGui.QPen(QtGui.QColor('#DC2626'), 2.4)\n"
f"{indent}    elif getattr(self, '_hover', False):\n"
f"{indent}        pen = QtGui.QPen(QtGui.QColor('#2563EB'), 2.0)\n"
f"{indent}    else:\n"
f"{indent}        pen = QtGui.QPen(QtGui.QColor('#111827'), 1.4)\n"
f"{indent}    try:\n"
f"{indent}        pen.setCosmetic(True)\n"
f"{indent}    except Exception:\n"
f"{indent}        pass\n"
f"{indent}    self.setPen(pen)\n"
f"{indent}    self.setBrush(QtCore.Qt.BrushStyle.NoBrush)\n"
)

cls2 = cls[:m2.start()] + new_block + cls[m2.end():]
txt2 = txt.replace(cls, cls2)

p.write_text(txt2, encoding="utf-8")
print("OK: PartRectItem._update_pen replaced safely")
