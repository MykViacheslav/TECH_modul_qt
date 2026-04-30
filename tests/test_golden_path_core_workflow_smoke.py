from __future__ import annotations

import pytest
from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _selected_station_title(tab_stanowiska) -> str:
    tabs = getattr(tab_stanowiska, "_tabs", None)
    if tabs is None:
        return ""
    idx = int(tabs.currentIndex())
    if idx < 0:
        return ""
    return str(tabs.tabText(idx) or "")


def test_golden_path_core_workflow_smoke(monkeypatch, tmp_path, qapp):
    """
    Golden-path smoke:
    Nowe zamowienie -> Sciana -> Komplet -> Wycena -> Stanowiska.
    """
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))

    from src.app.main_window import MainWindow
    from src.domain.assembly_models import FurnitureAssemblyDef
    from src.tabs.modul.tab_modul import TabModul
    from src.tabs.sciana.tab_sciana import TabSciana
    from src.tabs.sciana.tab_sciana_layout import TabScianaLayout
    from src.tabs.stanowiska.tab_stanowiska import TabStanowiska
    from src.tabs.wycena_hub.tab_wycena_hub import TabWycenaHub
    from src.tabs.zamowienie.tab_nowe_zamowienie import TabNoweZamowienie

    win = MainWindow()
    assert win is not None

    # 1) Runtime tabs exist and load expected classes.
    assert isinstance(win._tabs_by_title.get("Nowe zamowienie"), TabNoweZamowienie)
    assert isinstance(win._tabs_by_title.get("Sciana"), TabScianaLayout)
    assert isinstance(win._tabs_by_title.get("Komplet"), TabSciana)
    assert isinstance(win._tabs_by_title.get("Wycena"), TabWycenaHub)
    assert isinstance(win._tabs_by_title.get("Stanowiska"), TabStanowiska)
    assert isinstance(win._tabs_by_title.get("Modul"), TabModul)

    # 2) NZ -> Sciana (context handoff).
    order_context = {
        "client_name": "Klient Test",
        "order_id": "ORD-001",
        "order_name": "ZAM-001",
        "worker_name": "Jan",
        "order_status": "Projekt",
        "order_calendar_stage": "montaz",
        "order_calendar_date": "2031-01-05",
        "site_address": "Testowa 1, Warszawa",
    }
    win._open_new_wall(order_context)
    QApplication.processEvents()
    assert win._current_tab_title() in {"Sciana", "Ściana"}

    sciana_tab = win._tabs_by_title["Sciana"]
    wall = getattr(sciana_tab, "_wall", None)
    assert wall is not None
    assert str(getattr(wall, "order_name", "") or "") == "ZAM-001"
    assert str(getattr(wall, "client_name", "") or "") == "Klient Test"

    # 3) Sciana -> Komplet (context handoff).
    wall_ctx = sciana_tab._context_payload_from_wall(wall)
    win._open_new_assembly(wall_ctx)
    QApplication.processEvents()
    assert win._current_tab_title() == "Komplet"

    komplet_tab = win._tabs_by_title["Komplet"]
    assembly = getattr(komplet_tab, "_assembly", None)
    assert assembly is not None
    assert str(getattr(assembly, "order_name", "") or "") == "ZAM-001"
    assert str(getattr(assembly, "client_name", "") or "") == "Klient Test"

    # Ensure assembly exists in store for Wycena selection/filter smoke.
    assembly_name = str(getattr(assembly, "name", "") or "").strip() or "Komplet-1"
    komplet_tab._assembly_store.save_new(
        FurnitureAssemblyDef(
            name=assembly_name,
            wall_name=str(getattr(assembly, "wall_name", "") or "").strip(),
            client_name="Klient Test",
            order_name="ZAM-001",
            worker_name="Jan",
            width_mm=float(getattr(assembly, "width_mm", 3000.0) or 3000.0),
            height_mm=float(getattr(assembly, "height_mm", 2500.0) or 2500.0),
            depth_mm=float(getattr(assembly, "depth_mm", 560.0) or 560.0),
        )
    )

    # 4) Komplet -> Wycena (open_assembly_for_pricing path).
    win._open_assembly_in_wycena(assembly_name)
    QApplication.processEvents()
    assert win._current_tab_title() == "Wycena"

    wycena_hub = win._tabs_by_title["Wycena"]
    assert int(wycena_hub._sub_tabs.currentIndex()) == 0
    tab_wycena = getattr(wycena_hub, "_tab_wycena", None)
    assert tab_wycena is not None
    assert str(tab_wycena.cb_order.currentData() or "") == "ZAM-001"
    assert int(tab_wycena.tbl_assemblies.rowCount()) >= 1

    # 5) NZ -> Stanowiska (station + reference date handoff).
    win._open_stanowiska_for_order("montaz", reference_date="2031-01-05")
    QApplication.processEvents()
    assert win._current_tab_title() == "Stanowiska"

    stanowiska_tab = win._tabs_by_title["Stanowiska"]
    assert _selected_station_title(stanowiska_tab) == "Montaz"
    idx = int(stanowiska_tab._tabs.currentIndex())
    pane = stanowiska_tab._panes[idx]
    assert str(getattr(pane, "_reference_date_iso", "") or "") == "2031-01-05"
    view = getattr(pane, "_view", None)
    assert view is not None
    assert str(getattr(view, "_reference_date_iso", "") or "") == "2031-01-05"
