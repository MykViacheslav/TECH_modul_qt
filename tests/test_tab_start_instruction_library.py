from __future__ import annotations

from PyQt6.QtWidgets import QApplication

from src.domain.instruction_models import InstructionCardDef
from src.storage.instruction_store_json import InstructionStoreJson
from src.tabs.start.tab_start import TabStart


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_tab_start_instruction_library_lists_and_filters_cards(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    store = InstructionStoreJson(path=tmp_path / "instruction_cards.json")
    add_result = store.save_new(
        InstructionCardDef(
            category="okucia",
            title="Test okucia",
            when_to_use="Przy kompletacji okuc",
            impact="Jakosc montazu",
            steps="Sprawdz ilosc i rozstaw.",
            visualization_path="",
        )
    )
    assert add_result.ok is True

    app = _app()
    tab = TabStart()

    assert tab.lst_instruction_cards.count() >= 1
    item_texts = [tab.lst_instruction_cards.item(i).text() for i in range(tab.lst_instruction_cards.count())]
    assert any("Test okucia" in text for text in item_texts)

    idx = tab.cb_instruction_filter.findData("okucia")
    assert idx >= 0
    tab.cb_instruction_filter.setCurrentIndex(idx)
    filtered_texts = [tab.lst_instruction_cards.item(i).text() for i in range(tab.lst_instruction_cards.count())]
    assert all("[OKUCIA]" in text for text in filtered_texts)

    tab.close()
    app.processEvents()
