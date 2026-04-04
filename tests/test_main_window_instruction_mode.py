from __future__ import annotations

from PyQt6.QtCore import QEvent, QPointF, Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from src.app.main_window import MainWindow


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_main_window_instruction_mode_shows_avatar_hint_on_tab_hover(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = _app()
    w = MainWindow()
    w.show()
    app.processEvents()

    tab_start = w._tabs_by_title["Start"]
    assert w._instruction_mode_enabled is False
    QTest.mouseClick(tab_start.btn_instruction_mode, Qt.MouseButton.LeftButton)
    assert w._instruction_mode_enabled is True

    group_idx = w._tab_title_to_group["Start"]
    local_idx = w._tab_title_to_local_idx["Start"]
    tab_bar = w._group_tabwidgets[group_idx].tabBar()
    rect = tab_bar.tabRect(local_idx)
    local_pos = rect.center()
    global_pos = tab_bar.mapToGlobal(local_pos)
    move_event = QMouseEvent(
        QEvent.Type.MouseMove,
        QPointF(float(local_pos.x()), float(local_pos.y())),
        QPointF(float(global_pos.x()), float(global_pos.y())),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    w.eventFilter(tab_bar, move_event)
    app.processEvents()

    assert "Start" in w._instruction_hover_tab_title
    bubble_text = w.assistant_avatar._bubble.text()
    assert "Start" in bubble_text
    assert "Co to:" in bubble_text
    assert "Powiazane:" in bubble_text

    w.close()
    app.processEvents()


def test_main_window_instruction_mode_shows_sidebar_group_hint(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = _app()
    w = MainWindow()
    w.show()
    app.processEvents()

    tab_start = w._tabs_by_title["Start"]
    QTest.mouseClick(tab_start.btn_instruction_mode, Qt.MouseButton.LeftButton)

    sidebar_btn = w._group_buttons[0]
    enter_event = QEvent(QEvent.Type.Enter)
    w.eventFilter(sidebar_btn, enter_event)
    app.processEvents()

    assert "group:Sprzedaz" == w._instruction_hover_tab_title
    bubble_text = w.assistant_avatar._bubble.text()
    assert "Grupa: Sprzedaz" in bubble_text
    assert "Zakladki:" in bubble_text

    w.close()
    app.processEvents()


def test_main_window_global_onboarding_moves_between_tabs(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = _app()
    w = MainWindow()
    w.show()
    app.processEvents()

    tab_start = w._tabs_by_title["Start"]
    QTest.mouseClick(tab_start.btn_onboarding_start, Qt.MouseButton.LeftButton)
    app.processEvents()

    assert w._onboarding_active is True
    assert w.tabs.currentWidget() is w._tabs_by_title["Start"]
    assert "krok 1/" in tab_start.lab_onboarding_global_status.text().lower()

    QTest.mouseClick(tab_start.btn_onboarding_next, Qt.MouseButton.LeftButton)
    app.processEvents()
    assert w.tabs.currentWidget() is w._tabs_by_title["Nowe zamowienie"]
    assert w._onboarding_index == 1

    QTest.mouseClick(tab_start.btn_onboarding_stop, Qt.MouseButton.LeftButton)
    app.processEvents()
    assert w._onboarding_active is False
    assert "nieaktywny" in tab_start.lab_onboarding_global_status.text().lower()

    w.close()
    app.processEvents()
