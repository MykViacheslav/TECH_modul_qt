from __future__ import annotations
from pathlib import Path
import re

FILE = Path(r"""C:\PythonProject\TECH_modul\TECH_modul_qt\src\tabs\module_widget.py""")

def main():
    txt = FILE.read_text(encoding="utf-8", errors="ignore")

    # 1) remove early injected block (anywhere) that contains "front strip in TOP VIEW" and add_part('frontTop', ...)
    # keep it robust with DOTALL and non-greedy
    rm_pat = r"""
(?P<block>
^[ \t]*\#\s*front\s+strip\s+in\s+TOP\s+VIEW.*\n
(?:.*\n){0,40}?
^[ \t]*add_part\(\s*['"]frontTop['"]\s*,\s*front_strip\s*\)\s*\n
)
"""
    txt2, n = re.subn(rm_pat, "", txt, flags=re.MULTILINE | re.VERBOSE)
    if n:
        txt = txt2

    # If there are still direct calls to add_part('frontTop'...) anywhere, remove them too (safety)
    txt = re.sub(r"(?m)^[ \t]*add_part\(\s*['\"]frontTop['\"].*$\n", "", txt)

    # 2) insert safe block just before FIRST self.view.fitInView(...)
    m = re.search(r"(?m)^(?P<indent>[ \t]*)self\.view\.fitInView\(", txt)
    if not m:
        raise SystemExit("ERROR: Nie znaleziono self.view.fitInView(...) w module_widget.py")

    indent = m.group("indent")

    inject = (
        f"{indent}# front strip in TOP VIEW (front widoczny z góry) — safe place\n"
        f"{indent}front_chk = getattr(self, 'ck_front', None)\n"
        f"{indent}front_on2 = front_chk.isChecked() if front_chk is not None else False\n"
        f"{indent}if front_on2:\n"
        f"{indent}    try:\n"
        f"{indent}        strip_h = max(8.0, min(14.0, top_rect.height() * 0.08))\n"
        f"{indent}        front_strip = QtCore.QRectF(top_rect.left(), top_rect.top(), top_rect.width(), strip_h)\n"
        f"{indent}        add_part('frontTop', front_strip)\n"
        f"{indent}    except Exception:\n"
        f"{indent}        pass\n"
        f"\n"
    )

    txt = txt[:m.start()] + inject + txt[m.start():]

    FILE.write_text(txt, encoding="utf-8")
    print("OK: patched frontTop placement (no more UnboundLocalError).")

if __name__ == "__main__":
    main()
