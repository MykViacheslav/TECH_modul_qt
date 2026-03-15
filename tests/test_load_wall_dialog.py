from PyQt6.QtWidgets import QApplication


def test_load_wall_dialog_lists_metadata_and_can_delete(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.wall_models import WallLayoutDef
    from src.storage.wall_store_json import WallStoreJson
    from src.tabs.sciana.dialog_load_wall import LoadWallDialog

    store = WallStoreJson(path=tmp_path / "walls.json")
    store.save_new(
        WallLayoutDef(
            name="SCIANA_DIALOG",
            client_name="Klient testowy",
            order_name="ORD-17",
            layout_type="c",
        )
    )

    dlg = LoadWallDialog(None, store)
    assert dlg.tbl.rowCount() == 1
    assert dlg.tbl.item(0, 0).text() == "SCIANA_DIALOG"
    assert dlg.tbl.item(0, 1).text() == "Klient testowy"
    assert dlg.tbl.item(0, 2).text() == "ORD-17"
    assert "Klient: Klient testowy" in dlg.info.text()
    assert "Zamowienie: ORD-17" in dlg.info.text()

    dlg._confirm_delete = lambda _name: True
    dlg.btn_delete.click()

    assert store.get("SCIANA_DIALOG") is None
    assert dlg.tbl.rowCount() == 0
