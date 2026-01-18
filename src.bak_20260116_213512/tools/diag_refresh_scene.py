from __future__ import annotations
from pathlib import Path

p = Path(r"""C:\PythonProject\TECH_modul\TECH_modul_qt\src\tabs\module_widget.py""")
lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()

def find_refresh_scene():
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith("def _refresh_scene") or ln.lstrip().startswith("def _refresh_scene("):
            indent = len(ln) - len(ln.lstrip())
            return i, indent
    return None, None

start, indent = find_refresh_scene()
print(f"_refresh_scene: start={start+1 if start is not None else None}, indent={indent}")

if start is None:
    raise SystemExit("ERROR: def _refresh_scene not found")

# find end by indentation
end = None
for j in range(start+1, len(lines)):
    ln = lines[j]
    if ln.strip() == "":
        continue
    ind = len(ln) - len(ln.lstrip())
    if ind <= indent and not ln.lstrip().startswith("#"):
        end = j
        break
if end is None:
    end = len(lines)

chunk = lines[start:end]
fit = [ (start+k+1, ln.strip()) for k, ln in enumerate(chunk) if "fitInView(" in ln ]
print(f"fitInView occurrences inside _refresh_scene: {len(fit)}")
for (lnno, txt) in fit[-10:]:
    print(f"  line {lnno}: {txt}")

# show possible top rect names
candidates = []
for k, ln in enumerate(chunk):
    if "RectF" in ln and "=" in ln and ("top" in ln.lower() or "rzut" in ln.lower()):
        candidates.append((start+k+1, ln.strip()))
print("RectF assignments with 'top/rzut' keywords (last 15):")
for lnno, txt in candidates[-15:]:
    print(f"  line {lnno}: {txt}")

# show any mentions of keys frontTop/backTop/plecy/hdf
keys = []
for k, ln in enumerate(chunk):
    if any(s in ln for s in ("frontTop","backTop","plecy","HDF","hdf")):
        keys.append((start+k+1, ln.strip()))
print("Mentions frontTop/backTop/plecy/hdf inside _refresh_scene (last 25):")
for lnno, txt in keys[-25:]:
    print(f"  line {lnno}: {txt}")
