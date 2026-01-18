from __future__ import annotations
from pathlib import Path

p = Path(r"""C:\PythonProject\TECH_modul\TECH_modul_qt\src\tabs\module_widget.py""")
lines = p.read_text(encoding="utf-8", errors="ignore").splitlines(True)

def find_refresh_scene():
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith("def _refresh_scene"):
            indent = len(ln) - len(ln.lstrip())
            return i, indent
    return None, None

start, base_indent = find_refresh_scene()
if start is None:
    raise SystemExit("ERROR: def _refresh_scene not found")

# find end by indentation
end = None
for j in range(start+1, len(lines)):
    ln = lines[j]
    if ln.strip() == "":
        continue
    ind = len(ln) - len(ln.lstrip())
    if ind <= base_indent and not ln.lstrip().startswith("#"):
        end = j
        break
if end is None:
    end = len(lines)

# remove previous injected TOP VIEW blocks everywhere (safe)
out = []
skip = False
for ln in lines:
    if ln.lstrip().startswith("# TOP VIEW:"):
        skip = True
    if not skip:
        out.append(ln)
    if skip and ln.strip() == "pass":
        # allow the following blank line(s) to be consumed; stop skipping after first blank line
        continue
    if skip and ln.strip() == "" and (len(out) == 0 or out[-1].strip() == ""):
        # end of injected block
        skip = False

lines = out

# recompute _refresh_scene range after removal
start, base_indent = find_refresh_scene()
if start is None:
    raise SystemExit("ERROR: def _refresh_scene not found after cleanup")
end = None
for j in range(start+1, len(lines)):
    ln = lines[j]
    if ln.strip() == "":
        continue
    ind = len(ln) - len(ln.lstrip())
    if ind <= base_indent and not ln.lstrip().startswith("#"):
        end = j
        break
if end is None:
    end = len(lines)

# find LAST fitInView inside _refresh_scene
fit_idx = None
for j in range(start, end):
    if "fitInView(" in lines[j]:
        fit_idx = j
if fit_idx is None:
    raise SystemExit("ERROR: No fitInView(...) inside _refresh_scene")

indent = lines[fit_idx].split("self.view.fitInView")[0]  # keep exact indent

inject = []
inject.append(f"{indent}# TOP VIEW: FRONT (dół) + PLECY/HDF (góra) — poza korpusem, na samym końcu\n")
inject.append(f"{indent}try:\n")
inject.append(f"{indent}    # znajdź rect widoku z góry (różne nazwy)\n")
inject.append(f"{indent}    _top = None\n")
inject.append(f"{indent}    for _nm in ('top_rect','rect_top','topViewRect','topview_rect','r_top','topR'):\n")
inject.append(f"{indent}        if _nm in locals() and locals().get(_nm) is not None:\n")
inject.append(f"{indent}            _top = locals().get(_nm)\n")
inject.append(f"{indent}            break\n")
inject.append(f"{indent}    if _top is not None:\n")
inject.append(f"{indent}        # top/bottom niezależnie od orientacji\n")
inject.append(f"{indent}        y1 = float(_top.top()); y2 = float(_top.bottom())\n")
inject.append(f"{indent}        y_top = min(y1, y2); y_bot = max(y1, y2)\n")
inject.append(f"{indent}        area = QtCore.QRectF(_top.left(), y_top, _top.width(), (y_bot - y_top))\n")
inject.append(f"{indent}\n")
inject.append(f"{indent}        # checkboxy: front / plecy (best-effort)\n")
inject.append(f"{indent}        _front_on = False\n")
inject.append(f"{indent}        _front_chk = getattr(self, 'ck_front', None)\n")
inject.append(f"{indent}        if _front_chk is not None and hasattr(_front_chk, 'isChecked'):\n")
inject.append(f"{indent}            _front_on = _front_chk.isChecked()\n")
inject.append(f"{indent}\n")
inject.append(f"{indent}        _back_on = False\n")
inject.append(f"{indent}        for _nm in ('ck_back','ck_plecy','ck_hdf','ck_backpanel','ck_plecy_hdf'):\n")
inject.append(f"{indent}            _w = getattr(self, _nm, None)\n")
inject.append(f"{indent}            if _w is not None and hasattr(_w, 'isChecked'):\n")
inject.append(f"{indent}                _back_on = _w.isChecked(); break\n")
inject.append(f"{indent}\n")
inject.append(f"{indent}        _hide_front = False\n")
inject.append(f"{indent}        for _nm in ('ck_hide_fronts','ck_hide_front','ck_front_hide','ck_fronts_hide','ck_hide_front_view'):\n")
inject.append(f"{indent}            _w = getattr(self, _nm, None)\n")
inject.append(f"{indent}            if _w is not None and hasattr(_w, 'isChecked') and _w.isChecked():\n")
inject.append(f"{indent}                _hide_front = True; break\n")
inject.append(f"{indent}\n")
inject.append(f"{indent}        # usuń stare front/plecy wewnątrz top_rect (żeby nie nakładały)\n")
inject.append(f"{indent}        for it in list(self.scene.items()):\n")
inject.append(f"{indent}            try:\n")
inject.append(f"{indent}                key = it.data(0)\n")
inject.append(f"{indent}            except Exception:\n")
inject.append(f"{indent}                key = None\n")
inject.append(f"{indent}            if isinstance(key, str):\n")
inject.append(f"{indent}                k = key.lower()\n")
inject.append(f"{indent}                if ('front' in k) or ('plecy' in k) or ('back' in k) or ('hdf' in k):\n")
inject.append(f"{indent}                    try:\n")
inject.append(f"{indent}                        if hasattr(it, 'rect') and QtCore.QRectF(it.rect()).intersects(area):\n")
inject.append(f"{indent}                            self.scene.removeItem(it)\n")
inject.append(f"{indent}                    except Exception:\n")
inject.append(f"{indent}                        pass\n")
inject.append(f"{indent}\n")
inject.append(f"{indent}        # rysuj PLECY/HDF na górze (poza korpusem)\n")
inject.append(f"{indent}        strip_h = max(10.0, min(18.0, float(_top.height()) * 0.10))\n")
inject.append(f"{indent}        if _back_on:\n")
inject.append(f"{indent}            back_rect = QtCore.QRectF(_top.left(), y_top - strip_h, _top.width(), strip_h)\n")
inject.append(f"{indent}            b = QtWidgets.QGraphicsRectItem(back_rect)\n")
inject.append(f"{indent}            b.setZValue(2500)\n")
inject.append(f"{indent}            try:\n")
inject.append(f"{indent}                b.setPen(QtGui.QPen(QtGui.QColor('#334155'), 1))\n")
inject.append(f"{indent}                b.setBrush(QtGui.QBrush(QtGui.QColor('#CBD5E1')))\n")
inject.append(f"{indent}                b.setData(0, 'backTop')\n")
inject.append(f"{indent}            except Exception:\n")
inject.append(f"{indent}                pass\n")
inject.append(f"{indent}            self.scene.addItem(b)\n")
inject.append(f"{indent}\n")
inject.append(f"{indent}        # rysuj FRONT na dole (poza korpusem)\n")
inject.append(f"{indent}        if _front_on and not _hide_front:\n")
inject.append(f"{indent}            front_rect = QtCore.QRectF(_top.left(), y_bot, _top.width(), strip_h)\n")
inject.append(f"{indent}            f = QtWidgets.QGraphicsRectItem(front_rect)\n")
inject.append(f"{indent}            f.setZValue(2500)\n")
inject.append(f"{indent}            try:\n")
inject.append(f"{indent}                f.setPen(QtGui.QPen(QtGui.QColor('#334155'), 1))\n")
inject.append(f"{indent}                f.setBrush(QtGui.QBrush(QtGui.QColor('#E2E8F0')))\n")
inject.append(f"{indent}                f.setData(0, 'frontTop')\n")
inject.append(f"{indent}            except Exception:\n")
inject.append(f"{indent}                pass\n")
inject.append(f"{indent}            self.scene.addItem(f)\n")
inject.append(f"{indent}except Exception:\n")
inject.append(f"{indent}    pass\n\n")

# insert before last fitInView
new_lines = lines[:fit_idx] + inject + lines[fit_idx:]
p.write_text("".join(new_lines), encoding="utf-8")
print("OK: v10 inserted at end of _refresh_scene (before LAST fitInView).")
