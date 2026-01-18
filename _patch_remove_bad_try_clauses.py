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

def is_blank_or_comment(s: str) -> bool:
    t = s.strip()
    return (t == "" or t.startswith("#"))

def clause_kind(s: str):
    t = sstrip(s)
    if t == "finally:":
        return "finally"
    if t == "else:":
        return "else"
    if t.startswith("except") and t.endswith(":"):
        return "except"
    # also handle one-liners like: except Exception: pass
    if t.startswith("except") and ":" in t:
        return "except"
    return None

def is_try_line(s: str) -> bool:
    t = sstrip(s)
    return t == "try:" or t.startswith("try:")

def is_prev_clause_line(s: str) -> bool:
    # previous clause in same try-chain
    t = sstrip(s)
    if t == "else:" or t == "finally:":
        return True
    if t.startswith("except") and ":" in t:
        return True
    return False

out = []
removed = 0
i = 0

while i < len(lines):
    ln = lines[i]
    kind = clause_kind(ln)
    if kind is None:
        out.append(ln)
        i += 1
        continue

    cur_indent = ind(ln)

    # Look backwards for the "anchor" line at the SAME indent that should be try:/except:/else:
    k = len(out) - 1

    # skip blank/comment
    while k >= 0 and is_blank_or_comment(out[k]):
        k -= 1

    # if we're right after suite (indented lines), walk back to the line at same indent
    while k >= 0 and ind(out[k]) > cur_indent:
        k -= 1
        while k >= 0 and is_blank_or_comment(out[k]):
            k -= 1

    ok = False
    if k >= 0 and ind(out[k]) == cur_indent:
        if is_try_line(out[k]) or is_prev_clause_line(out[k]):
            ok = True

    if not ok:
        # BAD clause -> drop it and its suite (if any)
        removed += 1
        i += 1
        while i < len(lines) and ind(lines[i]) > cur_indent:
            i += 1
        continue

    # good clause
    out.append(ln)
    i += 1

p.write_text("".join(out), encoding="utf-8")
print("BAD-CLAUSE FIX done: removed_blocks=", removed)
