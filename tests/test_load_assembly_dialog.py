from PyQt6.QtWidgets import QApplication


def test_load_assembly_dialog_lists_metadata_and_can_delete(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.assembly_models import FurnitureAssemblyDef
    from src.storage.assembly_store_json import AssemblyStoreJson
    from src.tabs.sciana.dialog_load_assembly import LoadAssemblyDialog

    store = AssemblyStoreJson(path=tmp_path / "assemblies.json")
    store.save_new(
        FurnitureAssemblyDef(
            name="KOMPLET_DIALOG",
            client_name="Klient komplet",
            order_name="ORD-88",
            worker_name="Anna Projekt",
            wall_name="SCIANA_88",
        )
    )

    dlg = LoadAssemblyDialog(None, store)
    assert dlg.tbl.rowCount() == 1
    assert dlg.tbl.item(0, 0).text() == "KOMPLET_DIALOG"
    assert dlg.tbl.item(0, 1).text() == "Klient komplet"
    assert dlg.tbl.item(0, 2).text() == "ORD-88"
    assert dlg.tbl.item(0, 3).text() == "Anna Projekt"
    assert dlg.tbl.item(0, 4).text() == "SCIANA_88"
    assert "Klient: Klient komplet" in dlg.info.text()
    assert "Zamowienie: ORD-88" in dlg.info.text()
    assert "Pracownik: Anna Projekt" in dlg.info.text()

    dlg._confirm_delete = lambda _name: True
    dlg.btn_delete.click()

    assert store.get("KOMPLET_DIALOG") is None
    assert dlg.tbl.rowCount() == 0
