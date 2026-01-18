from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # src/
KEYWORDS = [
    "W", "H", "D",
    "doors", "drawers",
    "inset", "gap",
    "handle", "handles",
    "material", "materials",
    "edge", "edgeband",
    "front", "top",
]

# w PL czasem:
KEYWORDS_PL = ["drzwi", "szuflady", "uchwyt", "materiał", "krawędź", "wpuść", "szczelina"]

def score_text(text: str) -> int:
    t = text.lower()
    s = 0
    for k in KEYWORDS:
        if k.lower() in t:
            s += 3
    for k in KEYWORDS_PL:
        if k.lower() in t:
            s += 4
    return s

def inherits_qt(base: ast.expr) -> bool:
    # QWidget / QMainWindow / QtWidgets.QWidget etc.
    if isinstance(base, ast.Name):
        return base.id in ("QWidget", "QMainWindow", "QDialog")
    if isinstance(base, ast.Attribute):
        return base.attr in ("QWidget", "QMainWindow", "QDialog")
    return False

def analyze_file(p: Path) -> dict | None:
    try:
        code = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None

    # quick reject
    if p.name.startswith("_"):
        pass

    text_score = score_text(code)
    if text_score == 0:
        # still could be module, but keep low
        text_score = 0

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return {"path": str(p), "error": "SyntaxError", "text_score": text_score}

    best = None
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            if any(inherits_qt(b) for b in node.bases):
                cls = node.name
                # method hints
                cls_score = 10 + text_score
                # if class name looks like module/window
                low = cls.lower()
                if "module" in low or "modul" in low:
                    cls_score += 8
                if "main" in low or "window" in low:
                    cls_score += 4
                best = max(best or {"score": -1}, {"path": str(p), "class": cls, "score": cls_score}, key=lambda x: x["score"])

    if best:
        return best

    # fallback: if file mentions a lot of keywords, keep as candidate without class
    if text_score >= 10:
        return {"path": str(p), "class": None, "score": text_score}

    return None

def main():
    src = ROOT
    py_files = [p for p in src.rglob("*.py") if "site-packages" not in str(p)]
    candidates = []
    for p in py_files:
        info = analyze_file(p)
        if info:
            candidates.append(info)

    candidates.sort(key=lambda x: x.get("score", 0), reverse=True)
    best = candidates[0] if candidates else None

    out = {
        "best": best,
        "top10": candidates[:10],
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
