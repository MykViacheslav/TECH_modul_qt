from PyQt6.QtWidgets import QApplication


def test_on_save_new_shows_error_when_store_raises(monkeypatch):
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    import src.tabs.modul.tab_modul as tab_modul

    w = tab_modul.TabModul()
    w.dim.ed_name.setText("MOD_ERR_SAVE")

    messages: list[str] = []

    def _fake_critical(_parent, _title, text):
        messages.append(str(text))
        return tab_modul.QMessageBox.StandardButton.Ok

    def _raise_save(_draft):
        raise RuntimeError("save exploded")

    monkeypatch.setattr(tab_modul.QMessageBox, "critical", _fake_critical)
    monkeypatch.setattr(w._store, "save_new", _raise_save)

    w._on_save_new()

    assert messages
    assert "save exploded" in messages[0]


def test_on_overwrite_shows_error_when_store_raises(monkeypatch):
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    import src.tabs.modul.tab_modul as tab_modul

    w = tab_modul.TabModul()
    w.dim.ed_name.setText("MOD_ERR_OVERWRITE")

    messages: list[str] = []

    def _fake_critical(_parent, _title, text):
        messages.append(str(text))
        return tab_modul.QMessageBox.StandardButton.Ok

    def _raise_overwrite(_draft):
        raise RuntimeError("overwrite exploded")

    monkeypatch.setattr(tab_modul.QMessageBox, "critical", _fake_critical)
    monkeypatch.setattr(w._store, "overwrite", _raise_overwrite)

    w._on_overwrite()

    assert messages
    assert "overwrite exploded" in messages[0]


def test_on_load_shows_error_when_store_raises(monkeypatch):
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    import src.tabs.modul.tab_modul as tab_modul

    w = tab_modul.TabModul()
    w.dim.ed_name.setText("MOD_ERR_LOAD")

    messages: list[str] = []

    def _fake_critical(_parent, _title, text):
        messages.append(str(text))
        return tab_modul.QMessageBox.StandardButton.Ok

    def _raise_get(_name):
        raise RuntimeError("load exploded")

    monkeypatch.setattr(tab_modul.QMessageBox, "critical", _fake_critical)
    monkeypatch.setattr(w._store, "get", _raise_get)

    w._on_load()

    assert messages
    assert "load exploded" in messages[0]
