import os, re
from pathlib import Path

MOD = os.environ.get("MOD_PATH")
if not MOD:
    raise SystemExit("MOD_PATH env var missing")

p = Path(MOD)
txt = p.read_text(encoding="utf-8", errors="ignore")

changed = 0

# 1) Fix accidental \" in QColor calls (safe global)
#    QtGui.QColor(\"#0f172a\")  -> QtGui.QColor("#0f172a")
new = re.sub(r'QtGui\.QColor\(\\"(#?[0-9A-Fa-f]{3,8})\\"\)', r'QtGui.QColor("\1")', txt)
if new != txt:
    txt = new
    changed += 1

# 2) In _refresh_scene(): after self.scene.clear() add auto-rebuild if parts missing
if "def _refresh_scene" not in txt:
    raise SystemExit("Cannot find def _refresh_scene in file")

if "AUTO_REBUILD_PARTS_IF_EMPTY" not in txt:
    # insert right after first occurrence of "self.scene.clear()"
    m = re.search(r'(?m)^(?P<i>\s*)self\.scene\.clear\(\)\s*$', txt)
    if not m:
        raise SystemExit("Patch failed: cannot find 'self.scene.clear()' line")
    ind = m.group("i")
    insert = (
        f"{ind}# AUTO_REBUILD_PARTS_IF_EMPTY\n"
        f"{ind}if not getattr(self, 'parts', None):\n"
        f"{ind}    try:\n"
        f"{ind}        self._rebuild_parts()\n"
        f"{ind}    except Exception:\n"
        f"{ind}        pass\n"
    )
    txt = txt[:m.end()] + "\n" + insert + txt[m.end():]
    changed += 1

# 3) Hard-connect toggles for main carcass checkboxes (so recalc always triggers)
# Insert before first btn_reset.clicked.connect(...) line in _build_ui
if "HARD_CONNECT_CARCASS_TOGGLES" not in txt:
    m = re.search(r'(?m)^(?P<i>\s*)self\.btn_reset\.clicked\.connect\(self\._on_reset\)\s*$', txt)
    if not m:
        raise SystemExit("Patch failed: cannot find 'self.btn_reset.clicked.connect(self._on_reset)'")
    ind = m.group("i")
    block = (
        f"{ind}# HARD_CONNECT_CARCASS_TOGGLES\n"
        f"{ind}for _w in (\n"
        f"{ind}    getattr(self, 'ck_side_left', None),\n"
        f"{ind}    getattr(self, 'ck_side_right', None),\n"
        f"{ind}    getattr(self, 'ck_top', None),\n"
        f"{ind}    getattr(self, 'ck_bottom', None),\n"
        f"{ind}    getattr(self, 'ck_front', None),\n"
        f"{ind}    getattr(self, 'ck_back', None),\n"
        f"{ind}    getattr(self, 'ck_middle', None),\n"
        f"{ind}    getattr(self, 'ck_shelves', None),\n"
        f"{ind}):\n"
        f"{ind}    if _w is None:\n"
        f"{ind}        continue\n"
        f"{ind}    try:\n"
        f"{ind}        if hasattr(_w, 'toggled'):\n"
        f"{ind}            _w.toggled.connect(self._on_recalc)\n"
        f"{ind}        elif hasattr(_w, 'stateChanged'):\n"
        f"{ind}            _w.stateChanged.connect(self._on_recalc)\n"
        f"{ind}    except Exception:\n"
        f"{ind}        pass\n"
    )
    txt = txt[:m.start()] + block + txt[m.start():]
    changed += 1

p.write_text(txt, encoding="utf-8")
print("PATCH restore views OK. changed_blocks =", changed)
