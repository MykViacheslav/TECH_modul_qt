from __future__ import annotations

from PyQt6.QtWidgets import QApplication

from src.tabs.qr_telefon.tab_qr_telefon import TabQrTelefon


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_qr_telefon_builds_measure_mobile_url_and_qr(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    app = _app()
    tab = TabQrTelefon()

    tab.ed_base_url.setText("http://10.0.0.5:8000/")
    tab._refresh_urls_from_input()

    assert tab._pack_scanner_url == "http://10.0.0.5:8000/pack-scanner"
    assert tab._time_kiosk_url == "http://10.0.0.5:8000/kiosk-lite"
    assert tab._measure_mobile_url == "http://10.0.0.5:8000/measure-mobile"

    assert tab._measure_url_label is not None
    assert tab._measure_url_label.text() == "http://10.0.0.5:8000/measure-mobile"

    assert tab._measure_qr_label is not None
    pixmap = tab._measure_qr_label.pixmap()
    assert pixmap is not None
    assert not pixmap.isNull()

    tab.close()
    app.processEvents()
