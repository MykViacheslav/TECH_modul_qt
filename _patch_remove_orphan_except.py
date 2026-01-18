import os
from pathlib import Path

MOD = os.environ.get("MOD_PATH")
if not MOD:
    raise SystemExit("MOD_PATH env var missing")

p = Path(MOD)
lines = p.read_text(encoding="utf-8", errors="ignore").splitlines(True)

def ind(s: str) -> int:
    return len(s) - len(s.lstrip(" \t"))

def sstrip(s: str) -> str:
    return s.lstrip(" \t").rstrip("\r\n")

def is_try(s: str) -> bool:
    t = sstrip(s)
    return t == "try:" or t.startswith("try:")

def is_clause(s: str) -> bool:
    t = sstrip(s)
    if t == "finally:" or t == "else:":
        return True
    if t.startswith("except") and t.endswith(":"):
        return True
    return False

out = []
active_try = set()  # indents where "try:" exists and is still open
removed = 0

i = 0
prev_indent = 0
while i < len(lines):
    ln = lines[i]
    cur_indent = ind(ln)

    # when indent decreases, close tries deeper than current indent
    if cur_indent < prev_indent:
        active_try = {x for x in active_try if x <= cur_indent}
    prev_indent = cur_indent

    if is_try(ln):
        active_try.add(cur_indent)
        out.append(ln)
        i += 1
        continue

    if is_clause(ln):
        # clause is valid only if we have a try at same indent
        if cur_indent not in active_try:
            # orphan clause -> drop this line and its indented suite
            removed += 1
            i += 1
            while i < len(lines) and ind(lines[i]) > cur_indent:
                i += 1
            continue

        # keep clause
        out.append(ln)

        # finally closes the try at this indent (best effort)
        if sstrip(ln) == "finally:":
            active_try.discard(cur_indent)

        i += 1
        continue

    out.append(ln)
    i += 1

p.write_text("".join(out), encoding="utf-8")
print("ORPHAN-EXCEPT FIX done: removed_blocks=", removed)
