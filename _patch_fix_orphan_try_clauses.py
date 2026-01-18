import os
from pathlib import Path

MOD = os.environ.get("MOD_PATH")
if not MOD:
    raise SystemExit("MOD_PATH env var missing")

p = Path(MOD)
lines = p.read_text(encoding="utf-8", errors="ignore").splitlines(True)

def ind(s: str) -> int:
    return len(s) - len(s.lstrip(" \t"))

def stripped(s: str) -> str:
    return s.lstrip(" \t").rstrip("\r\n")

def is_blank_or_comment(s: str) -> bool:
    t = s.strip()
    return (t == "" or t.startswith("#"))

def is_try(s: str) -> bool:
    t = stripped(s)
    return t == "try:" or t.startswith("try:")

def is_clause(s: str) -> str | None:
    t = stripped(s)
    # match "except ...:" or "finally:" or "else:"
    if t.startswith("except") and t.endswith(":"):
        return "except"
    if t == "finally:":
        return "finally"
    if t == "else:":
        return "else"
    return None

out = []
removed_blocks = 0

# Track active try indents (simple but works for this healing)
active_try = set()

i = 0
prev_indent = 0
while i < len(lines):
    ln = lines[i]
    cur_indent = ind(ln)

    # when indent decreases, drop deeper active tries
    if cur_indent < prev_indent:
        active_try = {tind for tind in active_try if tind <= cur_indent}
    prev_indent = cur_indent

    if is_try(ln):
        active_try.add(cur_indent)
        out.append(ln)
        i += 1
        continue

    clause = is_clause(ln)
    if clause is not None:
        # clause must match an active try at same indent
        if cur_indent not in active_try:
            # orphan clause -> remove this line + its suite
            removed_blocks += 1
            i += 1
            while i < len(lines) and ind(lines[i]) > cur_indent:
                i += 1
            continue

        # valid clause: keep
        out.append(ln)

        # if it's finally: consider try closed at this indent (best-effort)
        if clause == "finally":
            if cur_indent in active_try:
                active_try.remove(cur_indent)

        i += 1
        continue

    out.append(ln)
    i += 1

p.write_text("".join(out), encoding="utf-8")
print("TRY-CLAUSE FIX done: removed_orphan_blocks=", removed_blocks)
