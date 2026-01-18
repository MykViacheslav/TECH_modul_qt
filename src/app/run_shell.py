from __future__ import annotations

import sys
from pathlib import Path

# Dodajemy src do sys.path (gdy uruchamiamy jako plik)
SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6 import QtWidgets

from app.context_factory import build_ctx
from app.main_window import MainWindow

# PL + theme (jeśli są)
try:
    from ui.i18n import apply_polish_i18n
except Exception:
    apply_polish_i18n = None

try:
    from ui.theme import apply_theme
except Exception:
    apply_theme = None


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)

    if apply_polish_i18n:
        apply_polish_i18n(app)
    if apply_theme:
        apply_theme(app)

    ctx = build_ctx()
    win = MainWindow(ctx)
    win.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
