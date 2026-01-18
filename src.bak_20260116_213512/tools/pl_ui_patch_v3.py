from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

PROJ = Path(__file__).resolve().parents[1].parent
SRC  = Path(__file__).resolve().parents[1]
CAND = PROJ / "module_candidate.json"

# --------------------------
# MAPA EN -> PL (rozszerzona)
# --------------------------
MAP: Dict[str, str] = {
    # wymiary
    "W": "Szerokość",
    "H": "Wysokość",
    "D": "Głębokość",
    "Width": "Szerokość",
    "Height": "Wysokość",
    "Depth": "Głębokość",
    "Length": "Długość",

    # elementy
    "Doors": "Drzwi",
    "Door": "Drzwi",
    "Drawers": "Szuflady",
    "Drawer": "Szuflada",
    "Shelves": "Półki",
    "Shelf": "Półka",

    "Count": "Ilość",
    "Qty": "Ilość",
    "Quantity": "Ilość",

    # parametry
    "Inset": "Wpuszczenie",
    "Gap": "Szczelina",
    "Offset": "Odsunięcie",
    "Thickness": "Grubość",

    "Handles": "Uchwyty",
    "Handle": "Uchwyt",

    "Material": "Materiał",
    "Materials": "Materiały",
    "Board": "Płyta",
    "Boards": "Płyty",

    "Edge": "Krawędź",
    "Edges": "Krawędzie",
    "Edgeband": "Okleina",
    "Edge band": "Okleina",

    "Front": "Front",
    "Top": "Blat",
    "Front + Top": "Front + Blat",
    "Front/Top": "Front/Blat",

    # akcje
    "Save": "Zapisz",
    "Load": "Wczytaj",
    "Reset": "Resetuj",
    "Clear": "Wyczyść",
    "Apply": "Zastosuj",
    "Calculate": "Oblicz",
    "Recalculate": "Przelicz",
    "Export": "Eksportuj",
    "Import": "Importuj",

    "Total": "Razem",
    "Price": "Cena",
    "Cost": "Koszt",
    "Summary": "Podsumowanie",

    "Yes": "Tak",
    "No": "Nie",
}

# Dodatkowe mapowania fragmentów (np. "Width (mm)" itp.)
PARTS_MAP: Dict[str, str] = {
    "mm": "mm",
    "cm": "cm",
    "pcs": "szt.",
    "pc": "szt.",
    "piece": "szt.",
    "pieces": "szt.",
}

# --------------------------
# Jakie wywołania uznajemy za "UI strings"
# --------------------------
CALLS_1ARG = [
    "QLabel", "QGroupBox", "QPushButton", "QCheckBox", "QRadioButton",
    "setText", "setTitle", "setWindowTitle",
    "setPlaceholderText", "setToolTip", "setWhatsThis", "setStatusTip",
    "setPrefix", "setSuffix",
]

# addTab(widget, "title") / addItem("text") / setItemText(i, "text")
# setHorizontalHeaderLabels([...]) / setHeaderLabels([...])
# Wymagają specjalnej obsługi (string nie zawsze 1. argument)
# --------------------------

@dataclass
class Change:
    old: str
    new: str
    count: int

def pick_target_file() -> Path:
    # prefer module_candidate.json jeśli to poprawny JSON
    if CAND.exists():
        try:
            data = json.loads(CAND.read_text(encoding="utf-8", errors="ignore"))
            best = data.get("best") or {}
            p = best.get("path")
            if p:
                pp = Path(p)
                if pp.exists():
                    return pp
        except Exception:
            pass
    # fallback: src/main.py
    return SRC / "main.py"

def backup(p: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = p.with_suffix(p.suffix + f".plui3.bak_{stamp}")
    bak.write_text(p.read_text(encoding="utf-8", errors="ignore"), encoding="utf-8")
    return bak

def translate_exact(s: str) -> str:
    return MAP.get(s, s)

def translate_common(s: str) -> str:
    """
    Tłumaczenie bezpieczne:
    - exact match w MAP
    - warianty z ":" na końcu
    - warianty typu "W (mm)", "Width (mm)", "Gap:", itd.
    - NIE ruszamy długich zdań (żeby nie popsuć sensu) – tylko proste frazy
    """
    if not s:
        return s

    s_strip = s.strip()

    # Exact
    if s_strip in MAP:
        return MAP[s_strip]

    # końcówka ":"
    if s_strip.endswith(":"):
        core = s_strip[:-1].strip()
        if core in MAP:
            return MAP[core] + ":"

    # "W (mm)" / "Width (mm)"
    m = re.match(r"^(?P<head>[A-Za-z]{1,20})\s*(?P<unit>\(.+?\))\s*$", s_strip)
    if m:
        head = m.group("head")
        unit = m.group("unit")
        if head in MAP:
            return f"{MAP[head]} {unit}"

    # "W:" / "H:" / "D:"
    m2 = re.match(r"^(?P<head>[A-Za-z]{1,3})\s*:\s*$", s_strip)
    if m2:
        head = m2.group("head")
        if head in MAP:
            return MAP[head] + ":"

    # krótkie 1-2 słowa: spróbuj tłumaczyć tokeny
    tokens = re.split(r"(\s+|/|\+|-)", s_strip)
    if len([t for t in tokens if t.strip()]) <= 5:
        out = []
        for t in tokens:
            tt = t.strip()
            if not tt:
                out.append(t)
                continue
            out.append(MAP.get(tt, t))
        joined = "".join(out)
        return joined

    return s

def sub_string_literals_in_calls(text: str) -> Tuple[str, Dict[Tuple[str, str], int]]:
    changes: Dict[Tuple[str, str], int] = {}

    # 1) CALL("...") / CALL('...')
    calls = "|".join(map(re.escape, CALLS_1ARG))
    re_call_1 = re.compile(rf"(?P<call>{calls})\(\s*(?P<q>['\"])(?P<s>.*?)(?P=q)\s*\)", re.DOTALL)

    def repl_1(m: re.Match) -> str:
        s0 = m.group("s")
        s1 = translate_common(s0)
        if s1 != s0:
            changes[(s0, s1)] = changes.get((s0, s1), 0) + 1
        return f"{m.group('call')}({m.group('q')}{s1}{m.group('q')})"

    out = re_call_1.sub(repl_1, text)

    # 2) addTab(widget, "title")
    re_addtab = re.compile(r"addTab\(\s*.+?,\s*(?P<q>['\"])(?P<s>.*?)(?P=q)\s*\)", re.DOTALL)
    def repl_addtab(m: re.Match) -> str:
        s0 = m.group("s")
        s1 = translate_common(s0)
        if s1 != s0:
            changes[(s0, s1)] = changes.get((s0, s1), 0) + 1
        return m.group(0).replace(f"{m.group('q')}{s0}{m.group('q')}", f"{m.group('q')}{s1}{m.group('q')}", 1)
    out = re_addtab.sub(repl_addtab, out)

    # 3) addItem("text") / setItemText(i, "text")
    re_additem = re.compile(r"(addItem|setItemText)\(\s*(?:\d+\s*,\s*)?(?P<q>['\"])(?P<s>.*?)(?P=q)\s*\)", re.DOTALL)
    def repl_item(m: re.Match) -> str:
        s0 = m.group("s")
        s1 = translate_common(s0)
        if s1 != s0:
            changes[(s0, s1)] = changes.get((s0, s1), 0) + 1
        return m.group(0).replace(f"{m.group('q')}{s0}{m.group('q')}", f"{m.group('q')}{s1}{m.group('q')}", 1)
    out = re_additem.sub(repl_item, out)

    # 4) setHorizontalHeaderLabels([...]) / setVerticalHeaderLabels([...]) / setHeaderLabels([...])
    #    zamieniamy elementy listy: ["A","B",...]
    re_headers = re.compile(r"(setHorizontalHeaderLabels|setVerticalHeaderLabels|setHeaderLabels)\(\s*(?P<lst>\[.*?\])\s*\)", re.DOTALL)
    str_lit = re.compile(r"(?P<q>['\"])(?P<s>.*?)(?P=q)", re.DOTALL)

    def repl_headers(m: re.Match) -> str:
        lst = m.group("lst")
        def repl_str(mm: re.Match) -> str:
            s0 = mm.group("s")
            s1 = translate_common(s0)
            if s1 != s0:
                changes[(s0, s1)] = changes.get((s0, s1), 0) + 1
            return f"{mm.group('q')}{s1}{mm.group('q')}"
        new_lst = str_lit.sub(repl_str, lst)
        return f"{m.group(1)}({new_lst})"

    out = re_headers.sub(repl_headers, out)

    return out, changes

def main():
    target = pick_target_file()
    if not target.exists():
        raise SystemExit(f"Target not found: {target}")

    txt = target.read_text(encoding="utf-8", errors="ignore")
    out, ch = sub_string_literals_in_calls(txt)

    if out == txt:
        print(f"NO_CHANGES: {target}")
        return

    bak = backup(target)
    target.write_text(out, encoding="utf-8")
    print(f"PATCHED: {target}")
    print(f"BACKUP : {bak}")

    # raport top 60 zmian
    items = sorted(((k[0], k[1], v) for k, v in ch.items()), key=lambda x: -x[2])
    for old, new, cnt in items[:60]:
        print(f"  {old} -> {new} (x{cnt})")

if __name__ == "__main__":
    main()
