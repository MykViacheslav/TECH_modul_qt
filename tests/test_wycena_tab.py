from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication


def test_wycena_tab_lists_assemblies_and_saves_commercial_values(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.assembly_models import FurnitureAssemblyDef
    from src.storage.assembly_store_json import AssemblyStoreJson
    from src.tabs.wycena.tab_wycena import TabWycena

    assembly_store = AssemblyStoreJson(path=tmp_path / "assemblies.json")
    assembly_store.save_new(
        FurnitureAssemblyDef(
            name="KOMPLET-WYCENA-01",
            order_name="ORDER-WYCENA-01",
            client_name="Klient Wycena",
        )
    )

    w = TabWycena(assembly_store=assembly_store)

    assert w.tbl_assemblies.rowCount() == 1
    assert w.tbl_assemblies.item(0, 0).text() == "KOMPLET-WYCENA-01"

    w.tbl_assemblies.selectRow(0)
    w.sp_labor.setValue(120.0)
    w.sp_transport.setValue(45.0)
    w.sp_montage.setValue(80.0)
    w.sp_margin.setValue(15.0)

    QTest.mouseClick(w.btn_save, Qt.MouseButton.LeftButton)

    saved = assembly_store.get("KOMPLET-WYCENA-01")
    assert saved is not None
    assert float(saved.labor_cost_pln) == 120.0
    assert float(saved.transport_cost_pln) == 45.0
    assert float(saved.montage_cost_pln) == 80.0
    assert float(saved.margin_percent) == 15.0
    assert "Nadpisano komplet" in w.lab_status.text()


def test_wycena_tab_filters_by_order_name(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.assembly_models import FurnitureAssemblyDef
    from src.storage.assembly_store_json import AssemblyStoreJson
    from src.tabs.wycena.tab_wycena import TabWycena

    assembly_store = AssemblyStoreJson(path=tmp_path / "assemblies.json")
    assembly_store.save_new(FurnitureAssemblyDef(name="KOMPLET-A", order_name="ORDER-A", client_name="Klient A"))
    assembly_store.save_new(FurnitureAssemblyDef(name="KOMPLET-B", order_name="ORDER-B", client_name="Klient B"))

    w = TabWycena(assembly_store=assembly_store)

    idx = w.cb_order.findData("ORDER-B")
    assert idx >= 0
    w.cb_order.setCurrentIndex(idx)

    assert w.tbl_assemblies.rowCount() == 1
    assert w.tbl_assemblies.item(0, 0).text() == "KOMPLET-B"
