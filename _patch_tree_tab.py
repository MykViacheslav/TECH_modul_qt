import os
from pathlib import Path

MOD = os.environ.get("MOD_PATH")
if not MOD:
    raise SystemExit("MOD_PATH env var missing")

p = Path(MOD)
txt = p.read_text(encoding="utf-8", errors="ignore")

# TODO: put your patch logic here
# txt = txt.replace("AAA", "BBB")

p.write_text(txt, encoding="utf-8")
print("PATCH OK")
