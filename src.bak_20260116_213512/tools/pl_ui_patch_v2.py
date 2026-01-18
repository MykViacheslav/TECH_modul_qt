from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

PROJ = Path(__file__).resolve().parents[1].parent
SRC  = Path(__file__).resolve().parents[1]
TARGET = SRC / "main.py"   # zaczynamy prosto: Moduł masz w src/main.py (u Ciebie patch poszedł właśnie tam)

# Mapowanie (możemy poszerzać)
MAP: Dict[str, str] = {
    # wymiary
    "W": "Szerokość",
    "H": "Wysokość",
    "D": "Głębokość",
    "Width": "Szerokość",
    "Height": "Wysokość",
    "Depth": "Głębokość",

    # elementy
    "Doors": "Drzwi",
    "Door": "Drzwi",
    "Drawers": "Szuflady",
    "Drawer": "Szuflada",
    "Count": "Ilość",
    "Qty": "Ilość",

    # parametry
    "Inset": "Wpuszczenie",
    "Gap": "Szczelina",

    "Handles": "Uchwyty",
    "Handle": "Uchwyt",

    "Material": "Materiał",
    "Materials": "Materiały",
    "Edge": "Krawędź",
    "Edgeband": "Krawędź",

    "Front": "Front",
    "Top": "Blat",

    # akcje
    "Save": "Zapisz",
    "Load": "Wczytaj",
    "Reset": "Resetuj",
    "Clear": "Wyczyść",
    "Apply": "Zastosuj",
    "Calculate": "Oblicz",
    "Total": "Razem",
    "Price": "Cena",
}

SAFE_CALLS = [
    "QLabel",
    "QGroupBox",
    "QPushButton",
    "setText",
    "setTitle",
    "setWindowTitle",
    "addTab",
]

# łapiemy: CALL("...") lub CALL('...')
# i podmieniamy tylko literal w pierwszym argumencie (dla addTab: drugi argument)
RE_CALL_1 = re.compile(rf"(?P<call>{'|'.join(SAFE_CALLS)})\(\s*(?P<q>['\"])(?P<s>.*?)(?P=q)\s*\)", re.DOTALL)
RE_ADDTAB = re.compile(r"addTab\(\s*.+?,\s*(?P<q>['\"])(?P<s>.*?)(?P=q)\s*\)", re.DOTALL)

@dataclass
class Change:
    old: str
    new: str
    count: int

def translate(text: str) -> str:
    s = text

    # proste przypadki z ":" na końcu
    if s.endswith(":"):
        core = s[:-1].strip()
        if core in MAP:
            return MAP[core] + ":"

    # przypadki typu "W (mm)" / "Width (mm)"
    m = re.match(r"^(?P<head>[A-Za-z])(\s*\(.*\))$", s)
    if m and m.group("head") in MAP:
        return MAP[m.group("head")] + m.group(2)

    m2 = re.match(r"^(?P<head>[A-Za-z]+)\s*(\(.+\))$", s)
    if m2 and m2.group("head") in MAP:
        return MAP[m2.group("head")] + " " + m2.group(2)

    # exact match
    if s in MAP:
        return MAP[s]

    return s

def backup(p: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = p.with_suffix(p.suffix + f".plui2.bak_{stamp}")
    bak.write_text(p.read_text(encoding="utf-8", errors="ignore"), encoding="utf-8")
    return bak

def patch_file(p: Path) -> List[Change]:
    txt = p.read_text(encoding="utf-8", errors="ignore")
    changes: Dict[Tuple[str, str], int] = {}

    # 1-arg calls
    def repl(m: re.Match) -> str:
        s0 = m.group("s")
        s1 = translate(s0)
        if s1 != s0:
            changes[(s0, s1)] = changes.get((s0, s1), 0) + 1
        return f"{m.group('call')}({m.group('q')}{s1}{m.group('q')})"

    out = RE_CALL_1.sub(repl, txt)

    # addTab second arg
    def repl_tab(m: re.Match) -> str:
        s0 = m.group("s")
        s1 = translate(s0)
        if s1 != s0:
            changes[(s0, s1)] = changes.get((s0, s1), 0) + 1
        return m.group(0).replace(f"{m.group('q')}{s0}{m.group('q')}", f"{m.group('q')}{s1}{m.group('q')}", 1)

    out2 = RE_ADDTAB.sub(repl_tab, out)

    if out2 != txt:
        b = backup(p)
        p.write_text(out2, encoding="utf-8")
        print(f"PATCHED: {p}")
        print(f"BACKUP : {b}")
    else:
        print(f"NO_CHANGES: {p}")

    return [Change(old=k[0], new=k[1], count=v) for k, v in sorted(changes.items(), key=lambda x: -x[1])]

def main():
    if not TARGET.exists():
        raise SystemExit(f"Target not found: {TARGET}")

    ch = patch_file(TARGET)
    for c in ch[:50]:
        print(f"  {c.old} -> {c.new} (x{c.count})")

if __name__ == "__main__":
    main()
