from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]   # src/
PROJ = ROOT.parent
OUT_JSON = PROJ / "module_candidate.json"

tabs_dir = ROOT / "tabs"
app_dir  = ROOT / "app"

def rel_import_from_path(py_path: Path) -> str:
    # convert src\foo\bar.py -> foo.bar
    rel = py_path.relative_to(ROOT).with_suffix("")
    return ".".join(rel.parts)

def main():
    data = json.loads(OUT_JSON.read_text(encoding="utf-8", errors="ignore"))
    best = data.get("best") or {}

    path = best.get("path")
    cls  = best.get("class")

    if not path:
        raise SystemExit("Nie znaleziono kandydata modułu. Otwórz module_candidate.json i zobacz top10.")
    py_path = Path(path)

    mod = rel_import_from_path(py_path)

    # --- tab adapter ---
    tab_file = tabs_dir / "tab_module.py"
    tab_file.parent.mkdir(parents=True, exist_ok=True)

    # Jeśli nie mamy klasy (cls None) — robimy placeholder i wypisujemy ścieżkę.
    if not cls:
        tab_code = f'''from __future__ import annotations

from typing import Any, Dict
from PySide6.QtWidgets import QVBoxLayout, QLabel
from .base import BaseTab


class Tab(BaseTab):
    TAB_KEY = "module"
    TAB_TITLE_PL = "Moduł"

    def __init__(self, ctx, parent=None) -> None:
        super().__init__(ctx, parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Moduł: nie znaleziono klasy QWidget/QMainWindow automatycznie."))
        layout.addWidget(QLabel("Najlepszy plik kandydata: {py_path.as_posix()}"))
        layout.addStretch(1)

    def export_state(self) -> Dict[str, Any]:
        return {{"title": self.TAB_TITLE_PL, "ready": False}}
'''
        tab_file.write_text(tab_code, encoding="utf-8")
    else:
        tab_code = f'''from __future__ import annotations

from typing import Any, Dict
from PySide6.QtWidgets import QVBoxLayout, QWidget, QLabel

from .base import BaseTab

# Auto-detected module entry:
from {mod} import {cls} as ModuleWidget


class Tab(BaseTab):
    TAB_KEY = "module"
    TAB_TITLE_PL = "Moduł"

    def __init__(self, ctx, parent=None) -> None:
        super().__init__(ctx, parent)
        layout = QVBoxLayout(self)

        # Instantiate existing Module UI
        obj = ModuleWidget()

        # If it's QMainWindow-like, try to embed its centralWidget
        cw = None
        if hasattr(obj, "centralWidget"):
            try:
                cw = obj.centralWidget()
            except Exception:
                cw = None

        if isinstance(cw, QWidget):
            layout.addWidget(cw)
        elif isinstance(obj, QWidget):
            layout.addWidget(obj)
        else:
            layout.addWidget(QLabel("Nie udało się osadzić modułu jako QWidget (nietypowa klasa)."))

    def export_state(self) -> Dict[str, Any]:
        return {{"title": self.TAB_TITLE_PL, "ready": True}}
'''
        tab_file.write_text(tab_code, encoding="utf-8")

    # --- module-only runner (to test quickly) ---
    run_file = app_dir / "run_module_only.py"
    run_code = f'''from __future__ import annotations

import sys
from PySide6 import QtWidgets

# Optional theme/i18n (if you already have them)
try:
    from ui.i18n import apply_polish_i18n
except Exception:
    apply_polish_i18n = None

try:
    from ui.theme import apply_theme
except Exception:
    apply_theme = None

# Auto-detected module entry:
from {mod} import {cls if cls else "None"} as ModuleEntry


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)

    if apply_polish_i18n:
        apply_polish_i18n(app)
    if apply_theme:
        apply_theme(app)

    if ModuleEntry is None:
        raise SystemExit("ModuleEntry not detected. Check module_candidate.json")

    w = ModuleEntry()

    # If it looks like QMainWindow: show it
    if hasattr(w, "show"):
        w.show()
    else:
        # fallback
        win = QtWidgets.QMainWindow()
        if isinstance(w, QtWidgets.QWidget):
            win.setCentralWidget(w)
        win.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
'''
    run_file.write_text(run_code, encoding="utf-8")

    print(f"OK: wrote {tab_file}")
    print(f"OK: wrote {run_file}")

if __name__ == "__main__":
    main()
