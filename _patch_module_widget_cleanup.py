import os
from pathlib import Path

MOD = os.environ.get("MOD_PATH")
if not MOD:
    raise SystemExit("MOD_PATH env var missing")

p = Path(MOD)
lines = p.read_text(encoding="utf-8", errors="ignore").splitlines(True)

def ind(s: str) -> int:
    return len(s) - len(s.lstrip(" \t"))

def is_blank_or_comment(s: str) -> bool:
    t = s.strip()
    return (t == "" or t.startswith("#"))

removed_toplvl = 0
out = []
for ln in lines:
    # remove ONLY bogus top-level lines like "self...." that must never be at column 0
    if ln and not ln.startswith((" ", "\t")):
        s = ln.lstrip()
        if s.startswith(("self.", "s.setValue(", "middle_on =", "if hasattr(self")):
            removed_toplvl += 1
            continue
    out.append(ln)
lines = out

# remove whole blocks: if hasattr(self, 'in_middle_count'):  (we are disabling middle_count feature)
removed_blocks = 0
out = []
i = 0
while i < len(lines):
    ln = lines[i]
    if "if hasattr(self, 'in_middle_count')" in ln or 'if hasattr(self, "in_middle_count")' in ln:
        base = ind(ln)
        i += 1
        # skip suite lines (more indented)
        while i < len(lines) and ind(lines[i]) > base:
            i += 1
        removed_blocks += 1
        continue
    out.append(ln)
    i += 1
lines = out

# remove direct references to self.in_middle_count if any still exist (non-comment)
removed_refs = 0
out = []
for ln in lines:
    if "self.in_middle_count" in ln and not ln.lstrip().startswith("#"):
        removed_refs += 1
        continue
    out.append(ln)
lines = out

# fix empty try: blocks (try with only comments before except/finally)
inserted_pass = 0
out = []
i = 0
while i < len(lines):
    ln = lines[i]
    if ln.lstrip().startswith("try:"):
        base = ind(ln)
        out.append(ln)
        j = i + 1
        # skip blank/comments
        while j < len(lines) and is_blank_or_comment(lines[j]):
            j += 1
        # if next meaningful line is except/finally at same indent -> empty try-suite
        if j < len(lines) and ind(lines[j]) == base and lines[j].lstrip().startswith(("except", "finally")):
            out.append(" " * (base + 4) + "pass\n")
            inserted_pass += 1
        i += 1
        continue

    out.append(ln)
    i += 1
lines = out

# ensure offsets line exists in hook list as REAL item (not only in commented INDENTFIX line)
inserted_hook = 0
start = None
base = None
for idx, ln in enumerate(lines):
    if "for w in [" in ln:
        start = idx
        base = ind(ln)
        break

if start is not None:
    end = start + 1
    while end < len(lines):
        # end of list is the line that starts with ]:
        if ind(lines[end]) <= base and lines[end].lstrip().startswith("]:"):
            break
        end += 1

    seg = lines[start:end+1]
    has_offsets = any(("self.in_middle_offsets" in x and not x.lstrip().startswith("#")) for x in seg)

    if not has_offsets:
        # choose indentation of list items
        item_indent = " " * (base + 4)
        for j in range(start+1, end):
            if lines[j].strip() and not lines[j].lstrip().startswith("#"):
                item_indent = " " * ind(lines[j])
                break

        # insert after ck_middle line if found; else right after start
        ins = start + 1
        for j in range(start, end):
            if "self.ck_middle" in lines[j]:
                ins = j + 1
                break

        lines.insert(ins, item_indent + "self.in_middle_offsets,\n")
        inserted_hook = 1

p.write_text("".join(lines), encoding="utf-8")

print("CLEANUP2 done:",
      "removed_toplvl=", removed_toplvl,
      "removed_in_middle_count_blocks=", removed_blocks,
      "removed_in_middle_count_refs=", removed_refs,
      "inserted_pass_in_try=", inserted_pass,
      "inserted_hook_offsets=", inserted_hook)
