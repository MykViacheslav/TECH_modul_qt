from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget


class _FakeDailyBriefingWidget(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(kwargs.get("parent"))
        self._date_lbl = QLabel("Piatek, 3 kwietnia 2026", self)
        self._user_lbl = QLabel("Jan - Biuro", self)
        self._content = QVBoxLayout()
        self._content.addWidget(QLabel("Terminy (7 dni)"))
        self._content.addWidget(QLabel("ORD-001 / Klient A Montaz dzis"))
        self._refresh_calls = 0

    def refresh(self) -> None:
        self._refresh_calls += 1

    def set_current_user(self, worker_name: str, role: str) -> None:
        self._user_lbl.setText(f"{worker_name} - {role}")


def test_tab_briefing_builds_telegram_text_from_widget_labels(monkeypatch):
    app = QApplication.instance() or QApplication([])

    import src.tabs.briefing.tab_briefing as briefing_module

    monkeypatch.setattr(briefing_module, "DailyBriefingWidget", _FakeDailyBriefingWidget)
    w = briefing_module.TabBriefing()

    text = w._build_briefing_text_for_telegram()

    assert "TECH_modul - Briefing dnia" in text
    assert "Piatek, 3 kwietnia 2026" in text
    assert "Jan - Biuro" in text
    assert "Terminy (7 dni)" in text
    assert "ORD-001 / Klient A Montaz dzis" in text


def test_tab_briefing_refresh_button_calls_briefing_refresh(monkeypatch):
    app = QApplication.instance() or QApplication([])

    import src.tabs.briefing.tab_briefing as briefing_module

    monkeypatch.setattr(briefing_module, "DailyBriefingWidget", _FakeDailyBriefingWidget)
    w = briefing_module.TabBriefing()
    fake = w._briefing

    before = int(getattr(fake, "_refresh_calls", 0))
    w._refresh()
    after = int(getattr(fake, "_refresh_calls", 0))

    assert after == before + 1
