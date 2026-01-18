from __future__ import annotations
from pathlib import Path
import re

FILE = Path(r"""C:\PythonProject\TECH_modul\TECH_modul_qt\src\tabs\module_widget.py""")

def main():
    txt = FILE.read_text(encoding="utf-8", errors="ignore")

    # 1) Remove ANY previous injected frontTop blocks (add_part or comments)
    # remove blocks that mention "front strip in TOP VIEW"
    txt = re.sub(
        r"(?ms)^[ \t]*#\s*front\s+strip\s+in\s+TOP\s+VIEW.*?\n(?:^[ \t].*\n){0,80}?",
        "",
        txt
    )
    # remove any direct add_part('frontTop', ...)
    txt = re.sub(r"(?m)^[ \t]*add_part\(\s*['\"]frontTop['\"].*$\n", "", txt)
    # remove any standalone mentions of frontTop injected earlier
    txt = re.sub(r"(?m)^.*frontTop.*$\n", lambda m: "" if "frontTop" in m.group(0) and "def " not in m.group(0) else m.group(0), txt)

    # 2) Insert a safe manual front strip RIGHT BEFORE the first fitInView
    m = re.search(r"(?m)^(?P<indent>[ \t]*)self\.view\.fitInView\(", txt)
    if not m:
        raise SystemExit("ERROR: Nie znaleziono self.view.fitInView(...) w module_widget.py")

    indent = m.group("indent")

    inject = (
        f"{indent}# TOP VIEW: front pasek (manual, zawsze widoczny) — bez add_part\n"
        f"{indent}try:\n"
        f"{indent}    # front włączony?\n"
        f"{indent}    _front_chk = getattr(self, 'ck_front', None)\n"
        f"{indent}    _front_on = _front_chk.isChecked() if _front_chk is not None else False\n"
        f"{indent}\n"
        f"{indent}    # ukryj fronty? (best-effort: różne nazwy)\n"
        f"{indent}    _hide = False\n"
        f"{indent}    for _nm in ('ck_hide_fronts','ck_hide_front','ck_front_hide','ck_fronts_hide','ck_hide_front_view'):\n"
        f"{indent}        _w = getattr(self, _nm, None)\n"
        f"{indent}        if _w is not None and hasattr(_w, 'isChecked') and _w.isChecked():\n"
        f"{indent}            _hide = True\n"
        f"{indent}            break\n"
        f"{indent}\n"
        f"{indent}    if _front_on and not _hide:\n"
        f"{indent}        # top_rect powinien istnieć w tej funkcji; jeśli nie, to skip\n"
        f"{indent}        if 'top_rect' in locals():\n"
        f"{indent}            _strip_h = max(10.0, min(18.0, float(top_rect.height()) * 0.10))\n"
        f"{indent}            _rect = QtCore.QRectF(top_rect.left(), top_rect.top(), top_rect.width(), _strip_h)\n"
        f"{indent}            _it = QtWidgets.QGraphicsRectItem(_rect)\n"
        f"{indent}            try:\n"
        f"{indent}                _it.setPen(QtGui.QPen(QtGui.QColor('#334155'), 1))\n"
        f"{indent}                _it.setBrush(QtGui.QBrush(QtGui.QColor('#E2E8F0')))\n"
        f"{indent}            except Exception:\n"
        f"{indent}                pass\n"
        f"{indent}            _it.setZValue(999)\n"
        f"{indent}            # oznaczamy klucz (dla debug/klików jeśli potrzebne)\n"
        f"{indent}            try:\n"
        f"{indent}                _it.setData(0, 'frontTop')\n"
        f"{indent}            except Exception:\n"
        f"{indent}                pass\n"
        f"{indent}            self.scene.addItem(_it)\n"
        f"{indent}except Exception:\n"
        f"{indent}    pass\n\n"
    )

    txt = txt[:m.start()] + inject + txt[m.start():]
    FILE.write_text(txt, encoding="utf-8")
    print("OK: TOP VIEW front strip inserted (manual item).")

if __name__ == "__main__":
    main()
