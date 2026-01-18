from __future__ import annotations
from pathlib import Path
import re

FILE = Path(r"""C:\PythonProject\TECH_modul\TECH_modul_qt\src\tabs\module_widget.py""")

def main():
    txt = FILE.read_text(encoding="utf-8", errors="ignore")

    # Remove previous injected blocks (v7/v8) to avoid duplicates
    txt = re.sub(r"(?ms)^[ \t]*# TOP VIEW: front pasek.*?^[ \t]*pass\s*\n\s*\n", "", txt)
    txt = re.sub(r"(?ms)^[ \t]*# TOP VIEW: front na DOLE.*?^[ \t]*pass\s*\n\s*\n", "", txt)
    txt = re.sub(r"(?ms)^[ \t]*# TOP VIEW: front pasek \(manual.*?^[ \t]*pass\s*\n\s*\n", "", txt)
    txt = re.sub(r"(?ms)^[ \t]*# TOP VIEW: front\s+pasek.*?^[ \t]*pass\s*\n\s*\n", "", txt)

    # Find insertion point: before the first fitInView
    m = re.search(r"(?m)^(?P<indent>[ \t]*)self\.view\.fitInView\(", txt)
    if not m:
        raise SystemExit("ERROR: Nie znaleziono self.view.fitInView(...) w module_widget.py")

    indent = m.group("indent")

    inject = (
        f"{indent}# TOP VIEW: FRONT (dół) + PLECY/HDF (góra) — bez nakładania na korpus\n"
        f"{indent}try:\n"
        f"{indent}    # Checkboxy (best-effort)\n"
        f"{indent}    _front_chk = getattr(self, 'ck_front', None)\n"
        f"{indent}    _front_on = _front_chk.isChecked() if _front_chk is not None else False\n"
        f"{indent}\n"
        f"{indent}    _back_on = False\n"
        f"{indent}    for _nm in ('ck_back','ck_plecy','ck_hdf','ck_backpanel','ck_plecy_hdf'):\n"
        f"{indent}        _w = getattr(self, _nm, None)\n"
        f"{indent}        if _w is not None and hasattr(_w, 'isChecked'):\n"
        f"{indent}            _back_on = _w.isChecked()\n"
        f"{indent}            break\n"
        f"{indent}\n"
        f"{indent}    # Ukryj fronty? (best-effort)\n"
        f"{indent}    _hide_front = False\n"
        f"{indent}    for _nm in ('ck_hide_fronts','ck_hide_front','ck_front_hide','ck_fronts_hide','ck_hide_front_view'):\n"
        f"{indent}        _w = getattr(self, _nm, None)\n"
        f"{indent}        if _w is not None and hasattr(_w, 'isChecked') and _w.isChecked():\n"
        f"{indent}            _hide_front = True\n"
        f"{indent}            break\n"
        f"{indent}\n"
        f"{indent}    # Głębokość korpusu D (nie zmieniamy!)\n"
        f"{indent}    _D = None\n"
        f"{indent}    if 'D' in locals():\n"
        f"{indent}        try: _D = float(D)\n"
        f"{indent}        except Exception: _D = None\n"
        f"{indent}    if _D is None:\n"
        f"{indent}        for _nm in ('in_d','sp_d','spin_d','inp_d'):\n"
        f"{indent}            _wd = getattr(self, _nm, None)\n"
        f"{indent}            if _wd is not None and hasattr(_wd, 'value'):\n"
        f"{indent}                try:\n"
        f"{indent}                    _D = float(_wd.value())\n"
        f"{indent}                    break\n"
        f"{indent}                except Exception:\n"
        f"{indent}                    pass\n"
        f"{indent}\n"
        f"{indent}    # Grubość frontu Tf (fallback 18)\n"
        f"{indent}    _Tf = 18.0\n"
        f"{indent}    for _nm in ('in_front_thk','sp_front_thk','spin_front_thk','front_thk','front_thickness'):\n"
        f"{indent}        _wf = getattr(self, _nm, None)\n"
        f"{indent}        if _wf is not None and hasattr(_wf, 'value'):\n"
        f"{indent}            try:\n"
        f"{indent}                _Tf = float(_wf.value())\n"
        f"{indent}                break\n"
        f"{indent}            except Exception:\n"
        f"{indent}                pass\n"
        f"{indent}\n"
        f"{indent}    # Jeśli mamy top_rect — działamy\n"
        f"{indent}    if 'top_rect' in locals() and top_rect is not None:\n"
        f"{indent}        # Ustal co jest \"górą\" i \"dołem\" niezależnie od orientacji\n"
        f"{indent}        y1 = float(top_rect.top()); y2 = float(top_rect.bottom())\n"
        f"{indent}        y_top = min(y1, y2)\n"
        f"{indent}        y_bot = max(y1, y2)\n"
        f"{indent}\n"
        f"{indent}        # 1) Usuń stare front/back, które są W ŚRODKU top_rect (żeby nie nakładało)\n"
        f"{indent}        area = QtCore.QRectF(top_rect.left(), y_top, top_rect.width(), (y_bot - y_top))\n"
        f"{indent}        for it in list(self.scene.items()):\n"
        f"{indent}            try:\n"
        f"{indent}                key = it.data(0)\n"
        f"{indent}            except Exception:\n"
        f"{indent}                key = None\n"
        f"{indent}            if not isinstance(key, str):\n"
        f"{indent}                continue\n"
        f"{indent}            k = key.lower()\n"
        f"{indent}            if ('front' in k) or ('plecy' in k) or ('back' in k) or ('hdf' in k):\n"
        f"{indent}                try:\n"
        f"{indent}                    if hasattr(it, 'rect'):\n"
        f"{indent}                        r = it.rect()\n"
        f"{indent}                        # tylko jeśli jest w obszarze top_rect\n"
        f"{indent}                        if QtCore.QRectF(r).intersects(area):\n"
        f"{indent}                            self.scene.removeItem(it)\n"
        f"{indent}                except Exception:\n"
        f"{indent}                    pass\n"
        f"{indent}\n"
        f"{indent}        # 2) Podpisy głębokości\n"
        f"{indent}        if _D is not None:\n"
        f"{indent}            t1 = QtWidgets.QGraphicsSimpleTextItem(f\"Głębokość korpusu (D): {int(round(_D))} mm\")\n"
        f"{indent}            t1.setZValue(2000)\n"
        f"{indent}            t1.setPos(top_rect.right() + 12, (y_top + y_bot) / 2 - 18)\n"
        f"{indent}            self.scene.addItem(t1)\n"
        f"{indent}\n"
        f"{indent}        # 3) PLECY/HDF na górze (poza korpusem)\n"
        f"{indent}        if _back_on:\n"
        f"{indent}            strip_h = max(10.0, min(18.0, float(top_rect.height()) * 0.10))\n"
        f"{indent}            back_rect = QtCore.QRectF(top_rect.left(), y_top - strip_h, top_rect.width(), strip_h)\n"
        f"{indent}            b = QtWidgets.QGraphicsRectItem(back_rect)\n"
        f"{indent}            b.setZValue(1500)\n"
        f"{indent}            try:\n"
        f"{indent}                b.setPen(QtGui.QPen(QtGui.QColor('#334155'), 1))\n"
        f"{indent}                b.setBrush(QtGui.QBrush(QtGui.QColor('#CBD5E1')))\n"
        f"{indent}                b.setData(0, 'backTop')\n"
        f"{indent}            except Exception:\n"
        f"{indent}                pass\n"
        f"{indent}            self.scene.addItem(b)\n"
        f"{indent}\n"
        f"{indent}        # 4) FRONT na dole (poza korpusem)\n"
        f"{indent}        if _front_on and not _hide_front:\n"
        f"{indent}            strip_h = max(10.0, min(18.0, float(top_rect.height()) * 0.10))\n"
        f"{indent}            front_rect = QtCore.QRectF(top_rect.left(), y_bot, top_rect.width(), strip_h)\n"
        f"{indent}            f = QtWidgets.QGraphicsRectItem(front_rect)\n"
        f"{indent}            f.setZValue(1500)\n"
        f"{indent}            try:\n"
        f"{indent}                f.setPen(QtGui.QPen(QtGui.QColor('#334155'), 1))\n"
        f"{indent}                f.setBrush(QtGui.QBrush(QtGui.QColor('#E2E8F0')))\n"
        f"{indent}                f.setData(0, 'frontTop')\n"
        f"{indent}            except Exception:\n"
        f"{indent}                pass\n"
        f"{indent}            self.scene.addItem(f)\n"
        f"{indent}\n"
        f"{indent}            if _D is not None:\n"
        f"{indent}                t2 = QtWidgets.QGraphicsSimpleTextItem(\n"
        f"{indent}                    f\"Z frontem: {int(round(_D + _Tf))} mm (Tf={int(round(_Tf))} mm)\"\n"
        f"{indent}                )\n"
        f"{indent}                t2.setZValue(2000)\n"
        f"{indent}                t2.setPos(top_rect.right() + 12, (y_top + y_bot) / 2 + 2)\n"
        f"{indent}                self.scene.addItem(t2)\n"
        f"{indent}except Exception:\n"
        f"{indent}    pass\n\n"
    )

    txt = txt[:m.start()] + inject + txt[m.start():]
    FILE.write_text(txt, encoding="utf-8")
    print("OK: v9 applied (TopView front bottom + back top, no overlay).")

if __name__ == "__main__":
    main()
