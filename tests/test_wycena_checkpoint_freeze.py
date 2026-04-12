from pathlib import Path

import pytest
from PyQt6.QtWidgets import QApplication, QTabWidget

from src.tabs.registry import build_tabs
from src.tabs.wycena_hub.tab_wycena_hub import TabWycenaHub


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _find_main_tab_widget(hub: TabWycenaHub) -> QTabWidget:
    for child in hub.findChildren(QTabWidget):
        if child.parent() == hub:
            return child
    raise AssertionError("No main QTabWidget found in TabWycenaHub")


def test_wycena_runtime_path_is_hub(qapp):
    tabs_dict = dict(build_tabs())
    assert "Wycena" in tabs_dict
    assert isinstance(tabs_dict["Wycena"], TabWycenaHub)


def test_wycena_hub_has_six_subtabs(qapp):
    hub = TabWycenaHub()
    tabs = _find_main_tab_widget(hub)
    assert tabs.count() == 6
    expected_core = {"Wycena projektu", "Szybka wycena", "Import 3D", "Rozkrój", "Podsumowanie"}
    actual = {tabs.tabText(i) for i in range(tabs.count())}
    assert expected_core.issubset(actual)


def test_wycena_mode_banner_updates_for_project_and_quick(qapp):
    hub = TabWycenaHub()
    tabs = _find_main_tab_widget(hub)

    tabs.setCurrentIndex(0)
    QApplication.processEvents()
    assert "WYCENA PROJEKTU" in hub.lab_mode_title.text()
    assert "Szybka wycena" in hub.lab_mode_desc.text()

    tabs.setCurrentIndex(1)
    QApplication.processEvents()
    assert "SZYBKA WYCENA" in hub.lab_mode_title.text()
    assert "Wycena projektu" in hub.lab_mode_desc.text()


def test_wycena_rozkroj_is_not_plain_placeholder(qapp):
    hub = TabWycenaHub()
    tabs = _find_main_tab_widget(hub)
    idx = next(i for i in range(tabs.count()) if tabs.tabText(i) == "Rozkrój")
    rozkroj_widget = tabs.widget(idx)

    assert rozkroj_widget is not None
    assert hasattr(rozkroj_widget, "refresh")
    assert hasattr(rozkroj_widget, "_value_labels")
    assert hasattr(rozkroj_widget, "lab_empty")


def test_wycena_rozkroj_has_readonly_metrics_and_empty_state(qapp):
    hub = TabWycenaHub()
    tabs = _find_main_tab_widget(hub)
    idx = next(i for i in range(tabs.count()) if tabs.tabText(i) == "Rozkrój")
    tabs.setCurrentIndex(idx)
    QApplication.processEvents()
    panel = tabs.widget(idx)

    keys = set(getattr(panel, "_value_labels", {}).keys())
    assert {"real_sheets_count", "real_area_m2", "scrap_m2", "utilization_pct", "difference_vs_theory"}.issubset(keys)

    empty_text = str(panel.lab_empty.text() or "")
    assert "Brak danych rozkroju" in empty_text


def test_wycena_rozkroj_placeholder_text_removed_from_source():
    src = Path("src/tabs/wycena_hub/tab_wycena_hub.py").read_text(encoding="utf-8")
    assert 'Rozkrój\\n\\n(w przygotowaniu)' not in src


def test_wycena_context_lock_from_open_assembly_for_pricing(tmp_path, monkeypatch, qapp):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    from src.domain.assembly_models import FurnitureAssemblyDef
    from src.storage.assembly_store_json import AssemblyStoreJson
    from src.tabs.wycena.tab_wycena import TabWycena

    store = AssemblyStoreJson(path=tmp_path / "assemblies.json")
    store.save_new(FurnitureAssemblyDef(name="KOMPLET-A", order_name="ORDER-A", client_name="Klient A"))
    store.save_new(FurnitureAssemblyDef(name="KOMPLET-B", order_name="ORDER-B", client_name="Klient B"))

    tab = TabWycena(assembly_store=store)
    tab.open_assembly_for_pricing("KOMPLET-B")

    assert str(tab.cb_quote_mode.currentData() or "") == "assemblies"
    assert str(tab.cb_order.currentData() or "") == "ORDER-B"
    assert tab.tbl_assemblies.rowCount() == 1
    assert tab.tbl_assemblies.item(0, 0).text() == "KOMPLET-B"


def test_wycena_text_fixes_present_in_source():
    src = Path("src/tabs/wycena/tab_wycena.py").read_text(encoding="utf-8")

    assert "Tryb wyceny:" in src
    assert "Wycena wstępna" in src
    assert "Wartość materiałów" in src
    assert "Marża %" in src
    assert "Zamówienie" in src

    assert "Wycena wstÄ™pna" not in src
    assert "WartoĹ›Ä‡ materiaĹ‚Ã³w" not in src
    assert "MarĹĽa %" not in src
