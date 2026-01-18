from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

PROJ = Path(__file__).resolve().parents[1].parent  # project root
SRC  = Path(__file__).resolve().parents[1]         # src
CAND = PROJ / "module_candidate.json"

# Mapowanie UI -> PL (bez zmian w logice)
# Uwaga: krótkie, jednoznaczne. Jeśli masz inne preferencje nazewnictwa, zmienimy.
MAP: Dict[str, str] = {
    "Width": "Szerokość",
    "W": "Szerokość",
    "Height": "Wysokość",
    "H": "Wysokość",
    "Depth": "Głębokość",
    "D": "Głębokość",

    "Doors": "Drzwi",
    "Door": "Drzwi",
    "Drawers": "Szuflady",
    "Drawer": "Szuflada",
    "Count": "Ilość",
    "Qty": "Ilość",

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

    "Save": "Zapisz",
    "Load": "Wczytaj",
    "Reset": "Resetuj",
    "Clear": "Wyczyść",
    "Apply": "Zastosuj",
    "Calculate": "Oblicz",
    "Total": "Razem",
    "Price": "Cena",
}

# Tylko bezpieczne miejsca: QLabel("..."), QGroupBox("..."), QPushButton("..."), setText("..."), setWindowTitle("..."), addTab(..., "...")
PATTERNS: List[Tuple[str, str]] = [
    (r'(QLabel\(\s*[\'"])({old})([\'"]\s*\))', r'\1{new}\3'),
    (r'(QGroupBox\(\s*[\'"])({old})([\'"]\s*\))', r'\1{new}\3'),
    (r'(QPushButton\(\s*[\'"])({old})([\'"]\s*\))', r'\1{new}\3'),
    (r'(setText\(\s*[\'"])({old})([\'"]\s*\))', r'\1{new}\3'),
    (r'(setTitle\(\s*[\'"])({old})([\'"]\s*\))', r'\1{new}\3'),
    (r'(setWindowTitle\(\s*[\'"])({old})([\'"]\s*\))', r'\1{new}\3'),
    (r'(addTab\(\s*.+?,\s*[\'"])({old})([\'"]\s*\))', r'\1{new}\3'),
]

@dataclass
class Change:
    old: str
    new: str
    count: int

def load_target_files() -> List[Path]:
    # Prefer: module_candidate.json best.path
    if CAND.exists():
        try:
            data = json.loads(CAND.read_text(encoding="utf-8", errors="ignore"))
            best = data.get("best") or {}
            p = best.get("path")
            if p:
                pp = Path(p)
                if pp.exists():
                    return [pp]
        except Exception:
            pass

    # Fallback: search files containing W/H/D + Doors/Drawers + Inset/Gap
    needles = ["Doors", "Drawers", "Inset", "Gap"]
    matches: List[Path] = []
    for f in SRC.rglob("*.py"):
        try:
            txt = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if all(n.lower() in txt.lower() for n in needles) and ("W" in txt or "Width" in txt):
            matches.append(f)
    return matches[:3]

def backup_file(p: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = p.with_suffix(p.suffix + f".plui.bak_{stamp}")
    bak.write_text(p.read_text(encoding="utf-8", errors="ignore"), encoding="utf-8")
    return bak

def patch_text(txt: str) -> Tuple[str, List[Change]]:
    changes: List[Change] = []
    out = txt

    # Apply mapping only in safe UI contexts
    for old, new in MAP.items():
        total = 0
        for pat, repl in PATTERNS:
            pattern = pat.format(old=re.escape(old))
            new_out, n = re.subn(pattern, repl.format(new=new), out, flags=re.MULTILINE)
            if n:
                out = new_out
                total += n
        if total:
            changes.append(Change(old=old, new=new, count=total))

    return out, changes

def main():
    targets = load_target_files()
    if not targets:
        print("NO_TARGETS: Nie znaleziono pliku modułu do spolszczenia.")
        return

    for p in targets:
        txt = p.read_text(encoding="utf-8", errors="ignore")
        new_txt, changes = patch_text(txt)

        if new_txt == txt:
            print(f"NO_CHANGES: {p}")
            continue

        bak = backup_file(p)
        p.write_text(new_txt, encoding="utf-8")
        print(f"PATCHED: {p}")
        print(f"BACKUP : {bak}")
        for c in changes:
            print(f"  {c.old} -> {c.new}  (x{c.count})")

if __name__ == "__main__":
    main()
