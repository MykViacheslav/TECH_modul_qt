from __future__ import annotations

import ast
import json
from pathlib import Path

PROJ = Path(__file__).resolve().parents[1].parent
SRC  = Path(__file__).resolve().parents[1]
OUT  = PROJ / "module_candidate.json"

KEYWORDS = [
    "W", "H", "D", "width", "height", "depth",
    "doors", "drawers", "inset", "gap",
    "handle", "materials", "material", "edge",
    "front", "top",
    "szerokość", "wysokość", "głębokość",
    "drzwi", "szuflady", "wpuszczenie", "szczelina",
    "uchwyt", "materiał", "krawędź",
]

def score_text(text: str) -> int:
    t = text.lower()
    s = 0
    for k in KEYWORDS:
        if k.lower() in t:
            s += 2
    return s

def inherits_qt(base: ast.expr) -> bool:
    if isinstance(base, ast.Name):
        return base.id in ("QWidget", "QMainWindow", "QDialog")
    if isinstance(base, ast.Attribute):
        return base.attr in ("QWidget", "QMainWindow", "QDialog")
    return False

def analyze_file(p: Path):
    try:
        code = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None

    txt_score = score_text(code)
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return {"path": str(p), "class": None, "score": txt_score, "error": "SyntaxError"}

    best = None
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and any(inherits_qt(b) for b in node.bases):
            sc = 10 + txt_score
            low = node.name.lower()
            if "module" in low or "modul" in low:
                sc += 10
            if "main" in low or "window" in low:
                sc += 4
            cand = {"path": str(p), "class": node.name, "score": sc}
            best = cand if not best or cand["score"] > best["score"] else best

    if best:
        return best
    if txt_score >= 12:
        return {"path": str(p), "class": None, "score": txt_score}
    return None

def main():
    files = [p for p in SRC.rglob("*.py") if "site-packages" not in str(p)]
    cands = []
    for f in files:
        r = analyze_file(f)
        if r:
            cands.append(r)
    cands.sort(key=lambda x: x.get("score", 0), reverse=True)
    OUT.write_text(json.dumps({"best": (cands[0] if cands else None), "top10": cands[:10]}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote: {OUT}")

if __name__ == "__main__":
    main()
