from __future__ import annotations
from pathlib import Path
import re

p = Path(r"""C:\PythonProject\TECH_modul\TECH_modul_qt\src\tabs\module_widget.py""")
txt = p.read_text(encoding="utf-8", errors="ignore").splitlines(True)

if any("PÓŁKI v13" in ln for ln in txt):
    print("SKIP: already patched v13")
    raise SystemExit(0)

def find_def(name: str):
    for i, ln in enumerate(txt):
        if ln.lstrip().startswith(f"def {name}("):
            indent = len(ln) - len(ln.lstrip())
            return i, indent
    return None, None

def block_end(start: int, base_indent: int):
    for j in range(start+1, len(txt)):
        ln = txt[j]
        if ln.strip() == "":
            continue
        ind = len(ln) - len(ln.lstrip())
        if ind <= base_indent and not ln.lstrip().startswith("#"):
            return j
    return len(txt)

# ---------------------------
# 1) Add helper to get shelves count (best effort)
# Insert small method near other helpers (before _refresh_scene if exists)
# ---------------------------
refresh_i, refresh_indent = find_def("_refresh_scene")
if refresh_i is None:
    raise SystemExit("ERROR: _refresh_scene not found")

insert_pos = refresh_i
base = " " * 4  # class indent assumed
helper = []
helper.append(f"{base}# PÓŁKI v13: helper count\n")
helper.append(f"{base}def _get_shelves_count(self) -> int:\n")
helper.append(f"{base}    \"\"\"Zwraca ilość półek (0 = brak). Best-effort: widget/state.\"\"\"\n")
helper.append(f"{base}    # 1) szukaj spinboxa po nazwie atrybutu\n")
helper.append(f"{base}    for _nm in ('sp_shelves','sb_shelves','spin_shelves','sp_polki','sb_polki','spin_polki'):\n")
helper.append(f"{base}        _w = getattr(self, _nm, None)\n")
helper.append(f"{base}        if _w is not None and hasattr(_w, 'value'):\n")
helper.append(f"{base}            try:\n")
helper.append(f"{base}                return int(_w.value())\n")
helper.append(f"{base}            except Exception:\n")
helper.append(f"{base}                pass\n")
helper.append(f"{base}    # 2) przeszukaj wszystkie atrybuty (shelf/polk)\n")
helper.append(f"{base}    for _nm, _w in self.__dict__.items():\n")
helper.append(f"{base}        if not isinstance(_nm, str):\n")
helper.append(f"{base}            continue\n")
helper.append(f"{base}        nml = _nm.lower()\n")
helper.append(f"{base}        if ('shelf' in nml) or ('polk' in nml):\n")
helper.append(f"{base}            if hasattr(_w, 'value'):\n")
helper.append(f"{base}                try:\n")
helper.append(f"{base}                    return int(_w.value())\n")
helper.append(f"{base}                except Exception:\n")
helper.append(f"{base}                    pass\n")
helper.append(f"{base}    # 3) state/dict\n")
helper.append(f"{base}    st = getattr(self, 'state', None)\n")
helper.append(f"{base}    if isinstance(st, dict):\n")
helper.append(f"{base}        for k in ('shelves','polki','półki','shelf_count'):\n")
helper.append(f"{base}            if k in st:\n")
helper.append(f"{base}                try:\n")
helper.append(f"{base}                    return int(st.get(k) or 0)\n")
helper.append(f"{base}                except Exception:\n")
helper.append(f"{base}                    pass\n")
helper.append(f"{base}    return 0\n\n")

txt[insert_pos:insert_pos] = helper

# re-find refresh after insertion
refresh_i, refresh_indent = find_def("_refresh_scene")
refresh_end = block_end(refresh_i, refresh_indent)
chunk = txt[refresh_i:refresh_end]

# ---------------------------
# 2) Inject shelves rendering near end of _refresh_scene, BEFORE fitInView(all_rect...)
# We'll draw as thin rectangles inside front_rect and top_rect.
# ---------------------------
fit_rel = None
for k, ln in enumerate(chunk):
    if "fitInView(" in ln:
        fit_rel = k
        break
if fit_rel is None:
    raise SystemExit("ERROR: fitInView not found inside _refresh_scene")

indent = chunk[fit_rel].split("self.view.fitInView")[0]

inject = []
inject.append(f"{indent}# PÓŁKI v13: rysowanie półek + podpórki\n")
inject.append(f"{indent}try:\n")
inject.append(f"{indent}    shelves_n = int(self._get_shelves_count())\n")
inject.append(f"{indent}except Exception:\n")
inject.append(f"{indent}    shelves_n = 0\n")
inject.append(f"{indent}if shelves_n < 0:\n")
inject.append(f"{indent}    shelves_n = 0\n")
inject.append(f"{indent}\n")
inject.append(f"{indent}# usuń stare półki z sceny\n")
inject.append(f"{indent}for it in list(self.scene.items()):\n")
inject.append(f"{indent}    try:\n")
inject.append(f"{indent}        key = it.data(0)\n")
inject.append(f"{indent}    except Exception:\n")
inject.append(f"{indent}        key = None\n")
inject.append(f"{indent}    if isinstance(key, str) and key.startswith('shelf_'):\n")
inject.append(f"{indent}        try:\n")
inject.append(f"{indent}            self.scene.removeItem(it)\n")
inject.append(f"{indent}        except Exception:\n")
inject.append(f"{indent}            pass\n")
inject.append(f"{indent}\n")
inject.append(f"{indent}if shelves_n > 0:\n")
inject.append(f"{indent}    # front_rect i top_rect powinny istnieć (jak w DIAG)\n")
inject.append(f"{indent}    try:\n")
inject.append(f"{indent}        _fr = front_rect\n")
inject.append(f"{indent}    except Exception:\n")
inject.append(f"{indent}        _fr = None\n")
inject.append(f"{indent}    try:\n")
inject.append(f"{indent}        _tr = top_rect\n")
inject.append(f"{indent}    except Exception:\n")
inject.append(f"{indent}        _tr = None\n")
inject.append(f"{indent}\n")
inject.append(f"{indent}    # rozmieść półki równomiernie w korpusie\n")
inject.append(f"{indent}    if _fr is not None:\n")
inject.append(f"{indent}        for i in range(shelves_n):\n")
inject.append(f"{indent}            # y w środku, z marginesami\n")
inject.append(f"{indent}            t = (i + 1) / (shelves_n + 1)\n")
inject.append(f"{indent}            y = _fr.top() + t * _fr.height()\n")
inject.append(f"{indent}            h = max(2.0, _fr.height() * 0.012)\n")
inject.append(f"{indent}            rect = QtCore.QRectF(_fr.left(), y - h/2.0, _fr.width(), h)\n")
inject.append(f"{indent}            sh = QtWidgets.QGraphicsRectItem(rect)\n")
inject.append(f"{indent}            sh.setZValue(1600)\n")
inject.append(f"{indent}            try:\n")
inject.append(f"{indent}                sh.setPen(QtGui.QPen(QtGui.QColor('#334155'), 1))\n")
inject.append(f"{indent}                sh.setBrush(QtGui.QBrush(QtGui.QColor('#E5E7EB')))\n")
inject.append(f"{indent}                sh.setData(0, f'shelf_{i}')\n")
inject.append(f"{indent}            except Exception:\n")
inject.append(f"{indent}                pass\n")
inject.append(f"{indent}            self.scene.addItem(sh)\n")
inject.append(f"{indent}\n")
inject.append(f"{indent}    if _tr is not None:\n")
inject.append(f"{indent}        for i in range(shelves_n):\n")
inject.append(f"{indent}            # w top view pokaż jako cienką linię poprzeczną\n")
inject.append(f"{indent}            t = (i + 1) / (shelves_n + 1)\n")
inject.append(f"{indent}            x = _tr.left() + t * _tr.width()\n")
inject.append(f"{indent}            w = max(2.0, _tr.width() * 0.010)\n")
inject.append(f"{indent}            rect = QtCore.QRectF(x - w/2.0, _tr.top(), w, _tr.height())\n")
inject.append(f"{indent}            sh = QtWidgets.QGraphicsRectItem(rect)\n")
inject.append(f"{indent}            sh.setZValue(900)\n")
inject.append(f"{indent}            try:\n")
inject.append(f"{indent}                sh.setPen(QtGui.QPen(QtGui.QColor('#94A3B8'), 1))\n")
inject.append(f"{indent}                sh.setBrush(QtGui.QBrush(QtGui.QColor('#F1F5F9')))\n")
inject.append(f"{indent}                sh.setData(0, f'shelf_{i}_top')\n")
inject.append(f"{indent}            except Exception:\n")
inject.append(f"{indent}                pass\n")
inject.append(f"{indent}            self.scene.addItem(sh)\n")
inject.append(f"{indent}\n")
inject.append(f"{indent}# podpórki: 4 szt na półkę (do listy okuć, jeśli jest)\n")
inject.append(f"{indent}try:\n")
inject.append(f"{indent}    # jeżeli masz tabelę/sekcję okuć (często: self.tbl_fittings / self.tbl_okucia)\n")
inject.append(f"{indent}    holders = shelves_n * 4\n")
inject.append(f"{indent}    if holders > 0:\n")
inject.append(f"{indent}        # spróbuj wpiąć w istniejący mechanizm 'extras/okucia'\n")
inject.append(f"{indent}        # 1) jeśli masz słownik ilości okuć\n")
inject.append(f"{indent}        d = getattr(self, 'fittings_qty', None)\n")
inject.append(f"{indent}        if isinstance(d, dict):\n")
inject.append(f"{indent}            d['Podpórka półki'] = holders\n")
inject.append(f"{indent}        # 2) jeśli masz listę wyników\n")
inject.append(f"{indent}        lst = getattr(self, 'computed_fittings', None)\n")
inject.append(f"{indent}        if isinstance(lst, list):\n")
inject.append(f"{indent}            # usuń stare\n")
inject.append(f"{indent}            lst[:] = [x for x in lst if not (isinstance(x, dict) and x.get('name') == 'Podpórka półki')]\n")
inject.append(f"{indent}            lst.append({'name':'Podpórka półki','qty':holders})\n")
inject.append(f"{indent}except Exception:\n")
inject.append(f"{indent}    pass\n\n")

# inject before fitInView
abs_fit = refresh_i + fit_rel
txt[abs_fit:abs_fit] = inject

p.write_text("".join(txt), encoding="utf-8")
print("OK: v13 shelves render + shelf supports qty added.")
