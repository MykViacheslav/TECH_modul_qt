from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from src.tabs.start.tab_start import TabStart


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_tab_start_instruction_toggle_and_onboarding_progress(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = _app()
    tab = TabStart()

    events: list[bool] = []
    tab.sig_instruction_mode_toggled.connect(events.append)

    assert "0/5" in tab.lab_onboarding_progress.text()
    assert tab.btn_instruction_mode.isChecked() is False

    QTest.mouseClick(tab.btn_instruction_mode, Qt.MouseButton.LeftButton)
    assert tab.btn_instruction_mode.isChecked() is True
    assert "WLACZONY" in tab.btn_instruction_mode.text()

    tab._onboarding_checks[0].setChecked(True)
    assert "1/5" in tab.lab_onboarding_progress.text()
    assert "nieaktywny" in tab.lab_onboarding_global_status.text().lower()

    tab.set_onboarding_status(active=True, current_step=2, total_steps=7, current_title="Wycena")
    assert "krok 2/7" in tab.lab_onboarding_global_status.text().lower()
    assert tab.btn_onboarding_start.isEnabled() is False
    assert tab.btn_onboarding_next.isEnabled() is True
    assert tab.btn_onboarding_stop.isEnabled() is True

    tab.set_onboarding_status(active=False, current_step=0, total_steps=7, current_title="")
    assert tab.btn_onboarding_start.isEnabled() is True
    assert tab.btn_onboarding_next.isEnabled() is False
    assert tab.btn_onboarding_stop.isEnabled() is False

    QTest.mouseClick(tab.btn_instruction_mode, Qt.MouseButton.LeftButton)
    assert tab.btn_instruction_mode.isChecked() is False
    assert "WYLACZONY" in tab.btn_instruction_mode.text()
    assert events == [True, False]

    tab.close()
    app.processEvents()
