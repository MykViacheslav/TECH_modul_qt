from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from src.app.main_window import MainWindow


def test_main_window_has_start_order_quote_calendar_worktime_modul_komplet_sciana_bazy_and_ustawienia_tabs(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    w = MainWindow()

    titles = list(w._tabs_by_title.keys())
    for expected in [
        "Start", "Nowe zamowienie", "Wycena",
        "Kalendarz", "Czas pracy",
        "Modul", "Komplet", "Sciana",
        "Bazy", "Ustawienia",
    ]:
        assert expected in titles, f'Brak zakładki: "{expected}"'

    assert w.tabs.currentWidget() is w._tabs_by_title["Start"]
    assert w.btn_nav_back.isEnabled() is False
    assert w.btn_nav_forward.isEnabled() is False
    assert w.btn_nav_home.isEnabled() is False


def test_main_window_applies_accessible_ui_scale_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])
    app.setProperty("_tech_modul_accessible_scale_applied", False)
    app.setStyleSheet("")

    w = MainWindow()

    assert bool(app.property("_tech_modul_accessible_scale_applied")) is True
    assert w.width() == 1560
    assert w.height() == 980
    assert "QTabBar::tab" in app.styleSheet()


def test_main_window_can_open_assembly_from_bazy_signal(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.assembly_models import FurnitureAssemblyDef
    from src.storage.assembly_store_json import AssemblyStoreJson

    assembly_store = AssemblyStoreJson(path=tmp_path / "assemblies.json")
    assembly_store.save_new(FurnitureAssemblyDef(name="KOMPLET_MAIN", client_name="Klient M"))

    w = MainWindow()
    tab_bazy = w._tabs_by_title["Bazy"]
    tab_komplet = w._tabs_by_title["Komplet"]

    tab_bazy.sig_open_assembly_requested.emit("KOMPLET_MAIN")

    assert getattr(tab_komplet, "ed_name").text() == "KOMPLET_MAIN"
    assert getattr(tab_komplet, "ed_client").text() == "Klient M"
    assert w.tabs.currentWidget() is tab_komplet


def test_main_window_start_new_order_button_opens_dedicated_order_tab(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    w = MainWindow()
    tab_start = w._tabs_by_title["Start"]
    tab_order = w._tabs_by_title["Nowe zamowienie"]

    QTest.mouseClick(tab_start.btn_new_order, Qt.MouseButton.LeftButton)

    assert w.tabs.currentWidget() is tab_order
    assert tab_order.ed_order_code.text() == ""
    assert tab_order.cb_client_name.currentText() == ""


def test_main_window_start_calendar_button_opens_calendar_tab(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    w = MainWindow()
    tab_start = w._tabs_by_title["Start"]
    tab_calendar = w._tabs_by_title["Kalendarz"]

    QTest.mouseClick(tab_start.btn_calendar, Qt.MouseButton.LeftButton)

    assert w.tabs.currentWidget() is tab_calendar


def test_main_window_navigation_buttons_track_history(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    w = MainWindow()
    tab_modul = w._tabs_by_title["Modul"]
    tab_bazy = w._tabs_by_title["Bazy"]
    tab_start = w._tabs_by_title["Start"]

    w.tabs.setCurrentWidget(tab_modul)
    w.tabs.setCurrentWidget(tab_bazy)

    assert w.tabs.currentWidget() is tab_bazy
    assert w.btn_nav_back.isEnabled() is True
    assert w.btn_nav_home.isEnabled() is True

    QTest.mouseClick(w.btn_nav_back, Qt.MouseButton.LeftButton)
    assert w.tabs.currentWidget() is tab_modul
    assert w.btn_nav_forward.isEnabled() is True

    QTest.mouseClick(w.btn_nav_forward, Qt.MouseButton.LeftButton)
    assert w.tabs.currentWidget() is tab_bazy

    QTest.mouseClick(w.btn_nav_home, Qt.MouseButton.LeftButton)
    assert w.tabs.currentWidget() is tab_start


def test_main_window_can_toggle_left_application_sidebar(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    w = MainWindow()
    w.show()
    app.processEvents()

    assert w._sidebar.isHidden() is False
    assert w.btn_sidebar_toggle.text() == "◀"

    QTest.mouseClick(w.btn_sidebar_toggle, Qt.MouseButton.LeftButton)
    assert w._sidebar.isHidden() is True
    assert w.btn_sidebar_toggle.text() == "▶"

    QTest.mouseClick(w.btn_sidebar_toggle, Qt.MouseButton.LeftButton)
    assert w._sidebar.isHidden() is False
    assert w.btn_sidebar_toggle.text() == "◀"


def test_main_window_passes_new_order_context_into_sciana(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    w = MainWindow()
    tab_order = w._tabs_by_title["Nowe zamowienie"]
    tab_sciana = w._tabs_by_title["Sciana"]

    tab_order.cb_client_name.setCurrentText("Klient Kontekst")
    tab_order.ed_client_phone.setText("500-500-500")
    tab_order.cb_worker_name.setCurrentText("Jan Kontekst")
    tab_order.ed_worker_role.setText("Pomiar")
    tab_order.ed_order_code.setText("ORDER-KONTEKST")
    tab_order.cb_order_status.setCurrentText("Nowe")
    tab_order.ed_order_address.setText("Warszawa, Prosta 1")

    QTest.mouseClick(tab_order.btn_go_to_sciana, Qt.MouseButton.LeftButton)

    assert w.tabs.currentWidget() is tab_sciana
    assert "Klient Kontekst" in (tab_sciana.cb_client.currentData() or "")
    assert tab_sciana.cb_order.currentData() == "ORDER-KONTEKST"
    assert tab_sciana.cb_worker.currentData() == "Jan Kontekst"
    assert "Klient Kontekst" in tab_sciana.lab_summary.text()
    assert "Zamowienie: ORDER-KONTEKST" in tab_sciana.lab_summary.text()
    assert "Pracownik: Jan Kontekst" in tab_sciana.lab_summary.text()


def test_main_window_can_open_quote_item_from_order_as_sciana(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    w = MainWindow()
    tab_order = w._tabs_by_title["Nowe zamowienie"]
    tab_sciana = w._tabs_by_title["Sciana"]

    tab_order.cb_client_name.setCurrentText("Klient Oferta")
    tab_order.cb_worker_name.setCurrentText("Jan Oferta")
    tab_order.ed_order_code.setText("ORDER-OFERTA-1")
    tab_order.cb_order_status.setCurrentText("Wycena")
    tab_order.ed_order_address.setText("Warszawa, Testowa 10")
    tab_order.ed_order_notes.setPlainText("Uwagi inwestora")
    tab_order._current_order_calendar_note = "Pomiar wstepny"
    tab_order.ed_quote_item_name.setText("RTV salon")
    tab_order.cb_quote_item_kind.setCurrentText("RTV")
    tab_order.ed_quote_item_description.setText("Niska zabudowa + panel")
    QTest.mouseClick(tab_order.btn_add_quote_item, Qt.MouseButton.LeftButton)
    tab_order.tbl_quote_items.selectRow(0)

    QTest.mouseClick(tab_order.btn_quote_to_sciana, Qt.MouseButton.LeftButton)

    assert w.tabs.currentWidget() is tab_sciana
    assert tab_sciana.ed_name.text() == "RTV salon"
    assert tab_sciana.cb_client.currentData() == "Klient Oferta"
    assert tab_sciana.cb_order.currentData() == "ORDER-OFERTA-1"
    assert tab_sciana.cb_worker.currentData() == "Jan Oferta"
    notes = tab_sciana.ed_notes.toPlainText()
    assert "Niska zabudowa + panel" in notes
    assert "Uwagi inwestora" in notes
    assert "Pomiar wstepny" in notes


def test_main_window_can_open_quote_item_from_order_as_komplet(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    w = MainWindow()
    tab_order = w._tabs_by_title["Nowe zamowienie"]
    tab_komplet = w._tabs_by_title["Komplet"]

    tab_order.cb_client_name.setCurrentText("Klient Oferta")
    tab_order.cb_worker_name.setCurrentText("Anna Oferta")
    tab_order.ed_order_code.setText("ORDER-OFERTA-2")
    tab_order.cb_order_status.setCurrentText("Wycena")
    tab_order.ed_order_address.setText("Krakow, Startowa 3")
    tab_order.ed_quote_item_name.setText("Szafa wejscie")
    tab_order.cb_quote_item_kind.setCurrentText("Szafa")
    tab_order.ed_quote_item_description.setText("Szafa wnekowa pod sufit")
    QTest.mouseClick(tab_order.btn_add_quote_item, Qt.MouseButton.LeftButton)
    tab_order.tbl_quote_items.selectRow(0)

    QTest.mouseClick(tab_order.btn_quote_to_komplet, Qt.MouseButton.LeftButton)

    assert w.tabs.currentWidget() is tab_komplet
    assert tab_komplet.ed_name.text() == "Szafa wejscie"
    assert tab_komplet.ed_client.text() == "Klient Oferta"
    assert tab_komplet.ed_order.text() == "ORDER-OFERTA-2"
    assert tab_komplet.cb_worker.currentData() == "Anna Oferta"
    assert "Status zamowienia: Wycena" in tab_komplet.lab_summary.text()
    assert "Adres realizacji:" in tab_komplet.lab_summary.text()
    assert "Startowa 3" in tab_komplet.lab_summary.text()
    assert "Krakow" in tab_komplet.lab_summary.text()


def test_main_window_passes_sciana_context_into_komplet(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    w = MainWindow()
    tab_order = w._tabs_by_title["Nowe zamowienie"]
    tab_sciana = w._tabs_by_title["Sciana"]
    tab_komplet = w._tabs_by_title["Komplet"]

    tab_order.cb_client_name.setCurrentText("Klient Sciana")
    tab_order.ed_client_phone.setText("500-600-700")
    tab_order.cb_worker_name.setCurrentText("Anna Sciana")
    tab_order.ed_worker_role.setText("Projekt")
    tab_order.ed_order_code.setText("ORDER-SCIANA-KOMPLET")
    tab_order.cb_order_status.setCurrentText("Nowe")
    tab_order.ed_order_address.setText("Poznan, Testowa 7")

    QTest.mouseClick(tab_order.btn_go_to_sciana, Qt.MouseButton.LeftButton)

    assert w.tabs.currentWidget() is tab_sciana
    tab_sciana.ed_name.setText("SCIANA-KONTEKST")

    QTest.mouseClick(tab_sciana.btn_go_to_komplet, Qt.MouseButton.LeftButton)

    assert w.tabs.currentWidget() is tab_komplet
    assert tab_komplet.cb_wall.currentData() == "SCIANA-KONTEKST"
    assert "Klient Sciana" in tab_komplet.ed_client.text()
    assert tab_komplet.ed_order.text() == "ORDER-SCIANA-KOMPLET"
    assert tab_komplet.cb_worker.currentData() == "Anna Sciana"
    assert "Powiazana sciana: SCIANA-KONTEKST" in tab_komplet.lab_summary.text()
    assert "Klient Sciana" in tab_komplet.lab_summary.text()
    assert "Zamowienie: ORDER-SCIANA-KOMPLET" in tab_komplet.lab_summary.text()
    assert "Pracownik: Anna Sciana" in tab_komplet.lab_summary.text()


def test_main_window_can_return_from_komplet_to_order_with_context(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    w = MainWindow()
    tab_order = w._tabs_by_title["Nowe zamowienie"]
    tab_sciana = w._tabs_by_title["Sciana"]
    tab_komplet = w._tabs_by_title["Komplet"]

    tab_order.cb_client_name.setCurrentText("Klient Powrot")
    tab_order.ed_client_phone.setText("555-111-222")
    tab_order.ed_client_email.setText("powrot@test.pl")
    tab_order.ed_client_city.setText("Krakow")
    tab_order.ed_client_notes.setPlainText("Notatka klienta")
    tab_order.cb_worker_name.setCurrentText("Pracownik Powrot")
    tab_order.ed_worker_role.setText("Projektant")
    tab_order.ed_worker_phone.setText("600-700-800")
    tab_order.ed_worker_email.setText("pracownik@test.pl")
    tab_order.ed_worker_notes.setPlainText("Notatka pracownika")
    tab_order.ed_order_code.setText("ORDER-POWROT-01")
    tab_order.cb_order_status.setCurrentText("Wycena")
    tab_order.ed_order_address.setText("Lodz, Powrotna 7")
    tab_order.ed_order_notes.setPlainText("Notatka zamowienia")

    QTest.mouseClick(tab_order.btn_go_to_sciana, Qt.MouseButton.LeftButton)

    assert w.tabs.currentWidget() is tab_sciana
    tab_sciana.ed_name.setText("SCIANA-POWROT")

    QTest.mouseClick(tab_sciana.btn_go_to_komplet, Qt.MouseButton.LeftButton)

    assert w.tabs.currentWidget() is tab_komplet

    QTest.mouseClick(tab_komplet.btn_back_to_order, Qt.MouseButton.LeftButton)

    assert w.tabs.currentWidget() is tab_order
    assert "Klient Powrot" in tab_order.cb_client_name.currentText()
    assert tab_order.ed_order_code.text() == "ORDER-POWROT-01"
    assert tab_order.cb_worker_name.currentText() == "Pracownik Powrot"
    assert tab_order.cb_order_status.currentText() == "Wycena"
    assert "Powrotna 7" in tab_order.ed_order_address.text()
