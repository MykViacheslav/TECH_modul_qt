from __future__ import annotations
from pathlib import Path
import re

FILE = Path(r"""C:\PythonProject\TECH_modul\TECH_modul_qt\src\tabs\module_widget.py""")

def main():
    txt = FILE.read_text(encoding="utf-8", errors="ignore")

    # Replace the injected block from v7 (manual top front) with a new block.
    # We look for the marker line and replace until the following blank line after "pass".
    pat = r"(?ms)^[ \t]*# TOP VIEW: front pasek \(manual, zawsze widoczny\).*?^[ \t]*pass\s*\n\s*\n"
    m = re.search(pat, txt)
    if not m:
        raise SystemExit("ERROR: Nie znaleziono bloku v7 '# TOP VIEW: front pasek (manual...)' do podmiany.")

    # New block: draw front BELOW top_rect, and write depth labels (korpus / z frontem).
    repl = (
        "            # TOP VIEW: front na DOLE (pod korpusem) + opis głębokości\n"
        "            try:\n"
        "                # front włączony?\n"
        "                _front_chk = getattr(self, 'ck_front', None)\n"
        "                _front_on = _front_chk.isChecked() if _front_chk is not None else False\n"
        "\n"
        "                # ukryj fronty? (best-effort)\n"
        "                _hide = False\n"
        "                for _nm in ('ck_hide_fronts','ck_hide_front','ck_front_hide','ck_fronts_hide','ck_hide_front_view'):\n"
        "                    _w = getattr(self, _nm, None)\n"
        "                    if _w is not None and hasattr(_w, 'isChecked') and _w.isChecked():\n"
        "                        _hide = True\n"
        "                        break\n"
        "\n"
        "                # głębokość korpusu D\n"
        "                _D = None\n"
        "                if 'D' in locals():\n"
        "                    try: _D = float(D)\n"
        "                    except Exception: _D = None\n"
        "                if _D is None:\n"
        "                    for _nm in ('in_d','sp_d','spin_d','inp_d'):\n"
        "                        _wd = getattr(self, _nm, None)\n"
        "                        if _wd is not None and hasattr(_wd, 'value'):\n"
        "                            try:\n"
        "                                _D = float(_wd.value())\n"
        "                                break\n"
        "                            except Exception:\n"
        "                                pass\n"
        "\n"
        "                # grubość frontu Tf (z bazy/spinbox jeśli jest; fallback 18)\n"
        "                _Tf = 18.0\n"
        "                for _nm in ('in_front_thk','sp_front_thk','spin_front_thk','front_thk','front_thickness'):\n"
        "                    _wf = getattr(self, _nm, None)\n"
        "                    if _wf is not None and hasattr(_wf, 'value'):\n"
        "                        try:\n"
        "                            _Tf = float(_wf.value())\n"
        "                            break\n"
        "                        except Exception:\n"
        "                            pass\n"
        "\n"
        "                # jeśli mamy top_rect, to rysujemy\n"
        "                if 'top_rect' in locals() and top_rect is not None:\n"
        "                    # 1) podpis głębokości (korpus)\n"
        "                    if _D is not None:\n"
        "                        t1 = QtWidgets.QGraphicsSimpleTextItem(f\"Głębokość korpusu: {int(round(_D))} mm\")\n"
        "                        t1.setZValue(1000)\n"
        "                        # po prawej stronie widoku z góry\n"
        "                        t1.setPos(top_rect.right() + 12, top_rect.center().y() - 16)\n"
        "                        self.scene.addItem(t1)\n"
        "\n"
        "                    # 2) front jako pasek POD korpusem (nie nakładamy)\n"
        "                    if _front_on and not _hide:\n"
        "                        strip_h = max(10.0, min(18.0, float(top_rect.height()) * 0.10))\n"
        "                        # front na dole: startuje od bottom top_rect i idzie w dół\n"
        "                        front_rect = QtCore.QRectF(top_rect.left(), top_rect.bottom(), top_rect.width(), strip_h)\n"
        "                        it = QtWidgets.QGraphicsRectItem(front_rect)\n"
        "                        try:\n"
        "                            it.setPen(QtGui.QPen(QtGui.QColor('#334155'), 1))\n"
        "                            it.setBrush(QtGui.QBrush(QtGui.QColor('#E2E8F0')))\n"
        "                        except Exception:\n"
        "                            pass\n"
        "                        it.setZValue(999)\n"
        "                        try:\n"
        "                            it.setData(0, 'frontTop')\n"
        "                        except Exception:\n"
        "                            pass\n"
        "                        self.scene.addItem(it)\n"
        "\n"
        "                        # podpis: głębokość z frontem\n"
        "                        if _D is not None:\n"
        "                            t2 = QtWidgets.QGraphicsSimpleTextItem(\n"
        "                                f\"Z frontem: {int(round(_D + _Tf))} mm (Tf={int(round(_Tf))} mm)\"\n"
        "                            )\n"
        "                            t2.setZValue(1000)\n"
        "                            t2.setPos(top_rect.right() + 12, top_rect.center().y() + 2)\n"
        "                            self.scene.addItem(t2)\n"
        "\n"
        "            except Exception:\n"
        "                pass\n\n"
    )

    txt = txt[:m.start()] + repl + txt[m.end():]
    FILE.write_text(txt, encoding=\"utf-8\")
    print(\"OK: v8 applied (front under top view + depth labels).\")

if __name__ == \"__main__\":\n    main()\n
