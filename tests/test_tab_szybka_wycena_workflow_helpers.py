from datetime import datetime

import pytest
from PyQt6.QtWidgets import QApplication


def test_tab_szybka_wycena_discount_helpers():
    from src.tabs.szybka_wycena.tab_szybka_wycena import TabSzybkaWycena

    assert TabSzybkaWycena._parse_percent("12.5") == 12.5
    assert TabSzybkaWycena._parse_percent("-7") == 0.0
    assert TabSzybkaWycena._parse_percent("120") == 95.0

    assert TabSzybkaWycena._apply_discount(1000.0, 10.0) == 900.0
    assert TabSzybkaWycena._apply_discount(1000.0, 0.0) == 1000.0
    assert TabSzybkaWycena._apply_discount(1000.0, 95.0) == pytest.approx(50.0, rel=1e-9)


def test_tab_szybka_wycena_build_quote_id_is_unique_for_same_timestamp():
    from src.tabs.szybka_wycena.tab_szybka_wycena import TabSzybkaWycena

    fixed = datetime(2026, 4, 3, 10, 15, 16)
    entries = [{"id": "Q20260403_101516"}]
    next_id = TabSzybkaWycena._build_quote_id(entries, now_dt=fixed)
    assert next_id == "Q20260403_101516_02"

    entries.append({"id": "Q20260403_101516_02"})
    next_id_2 = TabSzybkaWycena._build_quote_id(entries, now_dt=fixed)
    assert next_id_2 == "Q20260403_101516_03"


def test_tab_szybka_wycena_export_current_quote_pdf_creates_file(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    app = QApplication.instance() or QApplication([])

    from src.tabs.szybka_wycena import tab_szybka_wycena as mod
    from src.tabs.szybka_wycena.tab_szybka_wycena import TabSzybkaWycena
    from src.tabs.baza_szybkich_wycen.tab_baza_szybkich_wycen import quick_quote_export_dir

    info_calls: list[tuple] = []
    monkeypatch.setattr(mod.QMessageBox, "warning", lambda *args, **kwargs: None)
    monkeypatch.setattr(mod.QMessageBox, "critical", lambda *args, **kwargs: None)
    monkeypatch.setattr(mod.QMessageBox, "information", lambda *args, **kwargs: info_calls.append(args))

    w = TabSzybkaWycena()
    w.cb_client_selector.clear()
    w.cb_client_selector.addItem("Klient PDF", "Klient PDF")
    w.cb_client_selector.setCurrentIndex(0)
    w.ed_offer_title.setText("Oferta PDF test")
    w.ed_discount_pct.setText("10")
    monkeypatch.setattr(
        w,
        "_collect_sections_summary",
        lambda: ([{"id": "SW001", "title": "Sekcja 1", "price": "1000.00 zl"}], 1200.0),
    )
    monkeypatch.setattr(w, "_load_quote_archive", lambda: [])
    monkeypatch.setattr(w, "_build_quote_id", lambda entries, now_dt=None: "QTESTPDF")

    w._export_current_quote_pdf()
    w._export_current_quote_pdf()

    export_dir = quick_quote_export_dir()
    exported = sorted(export_dir.glob("QTESTPDF_Oferta_PDF_test*.pdf"))
    assert [p.name for p in exported] == ["QTESTPDF_Oferta_PDF_test.pdf", "QTESTPDF_Oferta_PDF_test_02.pdf"]
    assert exported[0].stat().st_size > 0
    assert len(info_calls) == 2
