import os
from pathlib import Path

MOD = os.environ.get("MOD_PATH")
if not MOD:
    raise SystemExit("MOD_PATH env var missing")

p = Path(MOD)
txt = p.read_text(encoding="utf-8", errors="ignore")

before = txt.count('QtGui.QColor(\\"')
txt = txt.replace('QtGui.QColor(\\"', 'QtGui.QColor("')
txt = txt.replace('\\"))', '"))')          # на випадок якщо десь так закрилося
txt = txt.replace('\\"),', '"),')          # на випадок якщо десь так закрилося
txt = txt.replace('\\"),', '"),')          # дубль безпечний

after = txt.count('QtGui.QColor(\\"')

p.write_text(txt, encoding="utf-8")
print("Unescaped QtGui.QColor: fixed =", before - after)
