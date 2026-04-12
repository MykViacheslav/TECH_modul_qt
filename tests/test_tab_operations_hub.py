from PyQt6.QtWidgets import QApplication

from src.tabs.operations_hub.tab_operations_hub import TabOperationsHub


def test_operations_hub_loads_without_crash(monkeypatch, tmp_path):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    app = QApplication.instance() or QApplication([])
    _ = app
    hub = TabOperationsHub()
    assert hub is not None
    assert hub.tabs.count() == 3
    assert hub.tabs.tabText(0) == "Problemy i alarmy"
    assert hub.tabs.tabText(1) == "Priorytety i trasy"
    assert hub.tabs.tabText(2) == "Mapa zlecen"
    assert "OPERACJE" in hub.kpi_bar.text()


def test_operations_hub_navigate_to_context_goes_to_orders_map(monkeypatch, tmp_path):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    app = QApplication.instance() or QApplication([])
    _ = app
    hub = TabOperationsHub()
    called = {}

    def _fake_navigate(point_id=None, project_name="", client_name=""):
        called["point_id"] = point_id
        called["project_name"] = project_name
        called["client_name"] = client_name
        return True

    hub.panel_orders_map.navigate_to_point = _fake_navigate
    hub.navigate_to_context(
        {
            "point_id": "P-1",
            "project_name": "Projekt A",
            "client_name": "Klient A",
            "target_tab": "mapa_zlecen",
        }
    )
    assert hub.tabs.currentWidget() is hub.panel_orders_map
    assert called["point_id"] == "P-1"


def test_operations_hub_fallback_info_on_missing_point(monkeypatch, tmp_path):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    app = QApplication.instance() or QApplication([])
    _ = app
    hub = TabOperationsHub()
    hub.navigate_to_context({"point_id": "missing", "target_tab": "mapa_zlecen"})
    assert hub.tabs.currentWidget() is hub.panel_orders_map
    assert hub.panel_orders_map.lbl_navigation_info.isHidden() is False
