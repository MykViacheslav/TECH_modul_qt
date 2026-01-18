from __future__ import annotations
from pathlib import Path
import re
from datetime import datetime

p = Path(r"""C:\PythonProject\TECH_modul\TECH_modul_qt\src\tabs\module_widget.py""")
txt = p.read_text(encoding="utf-8", errors="ignore")

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
bak2 = p.with_suffix(p.suffix + f".bak_v11_{stamp}")
bak2.write_text(txt, encoding="utf-8")
print(f"Backup v11: {bak2}")

# 1) конкретні рядки з DIAG:
# front_top_strip = QRectF(... top_rect.top() ...)  -> bottom()
# front_strip     = QRectF(... top_rect.top() ...)  -> bottom()
# _rect           = QRectF(... top_rect.top() ...)  -> bottom()
#
# Робимо вузько, тільки для змінних з 'front' у назві або exact patterns.

repls = 0

# front_top_strip line
txt2, n = re.subn(
    r"(?m)^(?P<i>\s*front_top_strip\s*=\s*QtCore\.QRectF\(\s*top_rect\.left\(\)\s*,\s*)top_rect\.top\(\)(\s*,\s*top_rect\.width\(\)\s*,\s*strip_h\s*\)\s*)$",
    r"\g<i>top_rect.bottom()\2",
    txt
)
repls += n
txt = txt2

# front_strip line
txt2, n = re.subn(
    r"(?m)^(?P<i>\s*front_strip\s*=\s*QtCore\.QRectF\(\s*top_rect\.left\(\)\s*,\s*)top_rect\.top\(\)(\s*,\s*top_rect\.width\(\)\s*,\s*strip_h\s*\)\s*)$",
    r"\g<i>top_rect.bottom()\2",
    txt
)
repls += n
txt = txt2

# generic _rect that uses _strip_h (often for front) — patch ONLY if right above/near setData('frontTop') later,
# but we can't parse AST safely here, so we patch only the exact pattern "_rect = QRectF(top_rect.left(), top_rect.top(), top_rect.width(), _strip_h)"
txt2, n = re.subn(
    r"(?m)^(?P<i>\s*_rect\s*=\s*QtCore\.QRectF\(\s*top_rect\.left\(\)\s*,\s*)top_rect\.top\(\)(\s*,\s*top_rect\.width\(\)\s*,\s*_strip_h\s*\)\s*)$",
    r"\g<i>top_rect.bottom()\2",
    txt
)
repls += n
txt = txt2

p.write_text(txt, encoding="utf-8")
print(f"OK: replaced top->bottom in {repls} line(s)")
