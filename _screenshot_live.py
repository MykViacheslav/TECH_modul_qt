"""
Live screenshot — bez offscreen, z prawdziwym renderem czcionek.
"""
from __future__ import annotations
import os
import sys

os.environ["TECH_MODUL_TESTING"] = "1"
sys.path.insert(0, r"C:\PythonProject\TECH_modul")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

app = QApplication(sys.argv)

from src.tabs.zamowienie.tab_nowe_zamowienie import TabNoweZamowienie

widget = TabNoweZamowienie()
widget.resize(1280, 860)
widget.setWindowTitle("TECH_modul — live screenshot")
widget.show()
app.processEvents()

OUT_DIR = r"C:\PythonProject\TECH_modul\_screenshots_live"
os.makedirs(OUT_DIR, exist_ok=True)

steps = {
    0: "01_Klient",
    1: "02_Zamowienie",
    2: "03_Pozycje_do_wyceny",
    3: "04_Zalaczniki",
    4: "05_Podsumowanie",
}

def take_screenshots():
    for idx, name in steps.items():
        widget.workflow_tabs.setCurrentIndex(idx)
        app.processEvents()
        pixmap = widget.grab()
        path = os.path.join(OUT_DIR, f"{name}.png")
        pixmap.save(path, "PNG")
        print(f"Saved: {path}")
    print("Done.")
    app.quit()

QTimer.singleShot(400, take_screenshots)
app.exec()
