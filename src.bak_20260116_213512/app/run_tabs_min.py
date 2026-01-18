from __future__ import annotations

import sys
from pathlib import Path

# IMPORTANT: uruchamiamy jako plik -> dodajemy katalog "src" do sys.path
SRC_DIR = Path(__file__).resolve().parents[1]  # ...\src
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6 import QtWidgets

from PySide6 import QtCore

# HOTFIX: Software OpenGL (avoid GPU driver crashes)
QtCore.QCoreApplication.setAttribute(QtCore.Qt.ApplicationAttribute.AA_UseSoftwareOpenGL, True)

from app.context_factory import build_ctx
from tabs.tab_module import Tab as ModuleTab

# opcjonalnie i18n/theme
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

    win = QtWidgets.QMainWindow()
    win.setWindowTitle("TECH — Moduł (test zakładki)")

    tabs = QtWidgets.QTabWidget()
    win.setCentralWidget(tabs)

    mod = ModuleTab(ctx)
    tabs.addTab(mod, mod.TAB_TITLE_PL)

    win.resize(1200, 800)
    win.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
