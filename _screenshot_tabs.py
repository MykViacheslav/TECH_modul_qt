"""
Skrypt do screenshotów zakładek TabNoweZamowienie.
Uruchamia się headless (offscreen), nie wymaga monitora.
"""
from __future__ import annotations
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["TECH_MODUL_TESTING"] = "1"

sys.path.insert(0, r"C:\PythonProject\TECH_modul")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

app = QApplication(sys.argv)

from src.tabs.zamowienie.tab_nowe_zamowienie import TabNoweZamowienie

widget = TabNoweZamowienie()
widget.resize(1280, 820)
widget.show()
app.processEvents()

OUT_DIR = r"C:\PythonProject\TECH_modul\_screenshots"
os.makedirs(OUT_DIR, exist_ok=True)

step_names = {
    0: "01_Klient",
    1: "02_Zamowienie",
    2: "03_Pozycje_do_wyceny",
    3: "04_Zalaczniki",
    4: "05_Podsumowanie",
}

for idx, name in step_names.items():
    widget.workflow_tabs.setCurrentIndex(idx)
    app.processEvents()
    pixmap = widget.grab()
    path = os.path.join(OUT_DIR, f"{name}.png")
    pixmap.save(path, "PNG")
    print(f"Saved: {path}")

print("Done.")
sys.exit(0)
