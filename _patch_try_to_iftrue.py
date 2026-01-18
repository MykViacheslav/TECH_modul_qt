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

def is_try_line(s: str) -> bool:
    t = stripped(s)
    return t == "try:" or t.startswith("try:")

def is_clause_line(s: str) -> bool:
    t = stripped(s)
    if t == "finally:" or t == "else:":
        return True
    if t.startswith("except") and t.endswith(":"):
        return True
    return False

changed = 0
i = 0
while i < len(lines):
    ln = lines[i]
    if not is_try_line(ln):
        i += 1
        continue

    base = ind(ln)

    # find end of try-suite (first non-blank/comment line with indent <= base)
    j = i + 1
    while j < len(lines):
        t = lines[j]
        if is_blank_or_comment(t):
            j += 1
            continue
        if ind(t) <= base:
            break
        j += 1

    # if next meaningful line at indent==base is not a clause -> orphan try
    orphan = False
    if j >= len(lines):
        orphan = True
    else:
        if ind(lines[j]) == base and not is_clause_line(lines[j]):
            orphan = True
        # also orphan if indent < base (we exited block without clause)
        if ind(lines[j]) < base:
            orphan = True

    if orphan:
        # replace "try:" with "if True:"
        prefix = ln[:len(ln) - len(ln.lstrip(" \t"))]
        lines[i] = prefix + "if True:\n"
        changed += 1

        # if suite is empty (next meaningful line is <= base), add pass
        k = i + 1
        while k < len(lines) and is_blank_or_comment(lines[k]):
            k += 1
        if k >= len(lines) or ind(lines[k]) <= base:
            lines.insert(i + 1, " " * (base + 4) + "pass\n")
        # continue scanning after this line
    i += 1

p.write_text("".join(lines), encoding="utf-8")
print("TRY->IFTRUE fix done: changed_try_lines=", changed)
