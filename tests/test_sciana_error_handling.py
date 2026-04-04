from PyQt6.QtWidgets import QApplication


def test_tab_sciana_save_new_shows_error_when_store_raises(monkeypatch):
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    import src.tabs.sciana.tab_sciana as tab_sciana

    w = tab_sciana.TabSciana()
    w.ed_name.setText("KOMPLET_ERR_SAVE")

    messages: list[str] = []

    def _fake_critical(_parent, _title, text):
        messages.append(str(text))
        return tab_sciana.QMessageBox.StandardButton.Ok

    def _raise_save(_assembly):
        raise RuntimeError("komplet save exploded")

    monkeypatch.setattr(tab_sciana.QMessageBox, "critical", _fake_critical)
    monkeypatch.setattr(w._assembly_store, "save_new", _raise_save)

    w._on_save_new()

    assert messages
    assert "komplet save exploded" in messages[0]
    assert "komplet save exploded" in w.lab_store_status.text()


def test_tab_sciana_overwrite_shows_error_when_store_raises(monkeypatch):
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    import src.tabs.sciana.tab_sciana as tab_sciana

    w = tab_sciana.TabSciana()
    w.ed_name.setText("KOMPLET_ERR_OVERWRITE")

    messages: list[str] = []

    def _fake_critical(_parent, _title, text):
        messages.append(str(text))
        return tab_sciana.QMessageBox.StandardButton.Ok

    def _raise_overwrite(_assembly):
        raise RuntimeError("komplet overwrite exploded")

    monkeypatch.setattr(tab_sciana.QMessageBox, "critical", _fake_critical)
    monkeypatch.setattr(w._assembly_store, "overwrite", _raise_overwrite)

    w._on_overwrite()

    assert messages
    assert "komplet overwrite exploded" in messages[0]
    assert "komplet overwrite exploded" in w.lab_store_status.text()


def test_tab_sciana_load_shows_error_when_dialog_raises(monkeypatch):
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    import src.tabs.sciana.tab_sciana as tab_sciana

    w = tab_sciana.TabSciana()

    messages: list[str] = []

    def _fake_critical(_parent, _title, text):
        messages.append(str(text))
        return tab_sciana.QMessageBox.StandardButton.Ok

    def _raise_dialog(*_args, **_kwargs):
        raise RuntimeError("komplet load exploded")

    monkeypatch.setattr(tab_sciana.QMessageBox, "critical", _fake_critical)
    monkeypatch.setattr(tab_sciana, "LoadAssemblyDialog", _raise_dialog)

    w._on_load()

    assert messages
    assert "komplet load exploded" in messages[0]
    assert "komplet load exploded" in w.lab_store_status.text()


def test_tab_sciana_layout_save_new_shows_error_when_store_raises(monkeypatch):
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    import src.tabs.sciana.tab_sciana_layout as tab_sciana_layout

    w = tab_sciana_layout.TabScianaLayout()
    w.ed_name.setText("SCIANA_ERR_SAVE")

    messages: list[str] = []

    def _fake_critical(_parent, _title, text):
        messages.append(str(text))
        return tab_sciana_layout.QMessageBox.StandardButton.Ok

    def _raise_save(_wall):
        raise RuntimeError("sciana save exploded")

    monkeypatch.setattr(tab_sciana_layout.QMessageBox, "critical", _fake_critical)
    monkeypatch.setattr(w._store, "save_new", _raise_save)

    w._on_save_new()

    assert messages
    assert "sciana save exploded" in messages[0]
    assert "sciana save exploded" in w.lab_store_status.text()


def test_tab_sciana_layout_overwrite_shows_error_when_store_raises(monkeypatch):
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    import src.tabs.sciana.tab_sciana_layout as tab_sciana_layout

    w = tab_sciana_layout.TabScianaLayout()
    w.ed_name.setText("SCIANA_ERR_OVERWRITE")

    messages: list[str] = []

    def _fake_critical(_parent, _title, text):
        messages.append(str(text))
        return tab_sciana_layout.QMessageBox.StandardButton.Ok

    def _raise_overwrite(_wall):
        raise RuntimeError("sciana overwrite exploded")

    monkeypatch.setattr(tab_sciana_layout.QMessageBox, "critical", _fake_critical)
    monkeypatch.setattr(w._store, "overwrite", _raise_overwrite)

    w._on_overwrite()

    assert messages
    assert "sciana overwrite exploded" in messages[0]
    assert "sciana overwrite exploded" in w.lab_store_status.text()


def test_tab_sciana_layout_load_shows_error_when_dialog_raises(monkeypatch):
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    import src.tabs.sciana.tab_sciana_layout as tab_sciana_layout

    w = tab_sciana_layout.TabScianaLayout()

    messages: list[str] = []

    def _fake_critical(_parent, _title, text):
        messages.append(str(text))
        return tab_sciana_layout.QMessageBox.StandardButton.Ok

    def _raise_dialog(*_args, **_kwargs):
        raise RuntimeError("sciana load exploded")

    monkeypatch.setattr(tab_sciana_layout.QMessageBox, "critical", _fake_critical)
    monkeypatch.setattr(tab_sciana_layout, "LoadWallDialog", _raise_dialog)

    w._on_load()

    assert messages
    assert "sciana load exploded" in messages[0]
    assert "sciana load exploded" in w.lab_store_status.text()
