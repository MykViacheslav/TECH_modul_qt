from PyQt6.QtWidgets import QApplication, QHeaderView


def test_bazy_tab_has_subtabs_and_can_add_client_and_order(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.core.module_parts_service import build_module_parts
    from src.domain.assembly_models import FurnitureAssemblyDef
    from src.domain.module_models import ModuleDef
    from src.domain.wall_models import WallLayoutDef
    from src.storage.assembly_store_json import AssemblyStoreJson
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.storage.client_store_json import ClientStoreJson
    from src.storage.module_store_json import ModuleStoreJson
    from src.storage.order_store_json import OrderStoreJson
    from src.storage.wall_store_json import WallStoreJson
    from src.storage.worker_store_json import WorkerStoreJson
    from src.tabs.bazy import tab_bazy as tab_bazy_module
    from src.tabs.bazy.tab_bazy import TabBazy

    def _find_module_item(widget, name: str):
        for group_idx in range(widget.tree_modules.topLevelItemCount()):
            group_item = widget.tree_modules.topLevelItem(group_idx)
            for child_idx in range(group_item.childCount()):
                candidate = group_item.child(child_idx)
                if candidate is not None and candidate.text(0) == name:
                    return candidate
        return None

    def _select_wall_row(widget, name: str) -> None:
        for row in range(widget.tbl_walls.rowCount()):
            item = widget.tbl_walls.item(row, 0)
            if item is not None and item.text() == name:
                widget.tbl_walls.selectRow(row)
                return

    def _select_assembly_row(widget, name: str) -> None:
        for row in range(widget.tbl_assemblies.rowCount()):
            item = widget.tbl_assemblies.item(row, 0)
            if item is not None and item.text() == name:
                widget.tbl_assemblies.selectRow(row)
                return

    catalog = CatalogStoreJson()
    module_store = ModuleStoreJson(path=tmp_path / "modules.json")
    wall_store = WallStoreJson(path=tmp_path / "walls.json")
    assembly_store = AssemblyStoreJson(path=tmp_path / "assemblies.json")
    client_store = ClientStoreJson(path=tmp_path / "clients.json")
    order_store = OrderStoreJson(path=tmp_path / "orders.json")
    worker_store = WorkerStoreJson(path=tmp_path / "workers.json")

    module = ModuleDef(name="BAZA_MODUL", width_mm=800.0, depth_mm=500.0, height_mm=720.0)
    module.parts = build_module_parts(module, catalog)
    module_store.save_new(module)
    wall_store.save_new(WallLayoutDef(name="BAZA_SCIANA", client_name="Klient A", order_name="ORD-A"))
    assembly_store.save_new(
        FurnitureAssemblyDef(
            name="BAZA_KOMPLET",
            client_name="Klient A",
            order_name="ORD-A",
            worker_name="Jan Monter",
            wall_name="BAZA_SCIANA",
        )
    )

    w = TabBazy(
        module_store=module_store,
        wall_store=wall_store,
        assembly_store=assembly_store,
        client_store=client_store,
        order_store=order_store,
        worker_store=worker_store,
        catalog=catalog,
    )

    titles = [w.tabs.tabText(i) for i in range(w.tabs.count())]
    assert titles == ["Moduly", "Sciany", "Komplety", "Klienci", "Zamowienia", "Materialy", "Pracownicy"]
    assert w.open_clients_tab(clear_form=True) is True
    assert w.tabs.tabText(w.tabs.currentIndex()) == "Klienci"
    assert w.ed_client_name.text() == ""
    assert w.open_orders_tab(clear_form=True) is True
    assert w.tabs.tabText(w.tabs.currentIndex()) == "Zamowienia"
    assert w.ed_order_code.text() == ""
    assert w.tree_modules.topLevelItemCount() >= 1
    assert w.tbl_walls.rowCount() == 1
    assert w.tbl_assemblies.rowCount() == 1
    assert w.tbl_walls.horizontalHeader().sectionResizeMode(0) == QHeaderView.ResizeMode.Interactive
    assert w.tbl_assemblies.horizontalHeader().sectionResizeMode(0) == QHeaderView.ResizeMode.Interactive
    assert w.tbl_clients.horizontalHeader().sectionResizeMode(0) == QHeaderView.ResizeMode.Interactive
    assert w.tbl_orders.horizontalHeader().sectionResizeMode(0) == QHeaderView.ResizeMode.Interactive
    assert w.tbl_workers.horizontalHeader().sectionResizeMode(0) == QHeaderView.ResizeMode.Interactive
    assert w.tbl_workers.horizontalHeader().stretchLastSection() is False
    assert w.btn_client_add.maximumWidth() <= 140
    assert w.btn_client_overwrite.maximumWidth() <= 140
    assert w.btn_delete_module.maximumWidth() <= 140
    assert w.btn_open_catalog.maximumWidth() <= 220

    prompt_values = iter(
        [
            ("BAZA_MODUL_KOPIA", True),
            ("BAZA_MODUL_RENAME", True),
            ("BAZA_SCIANA_KOPIA", True),
            ("BAZA_SCIANA_RENAME", True),
            ("BAZA_KOMPLET_KOPIA", True),
            ("BAZA_KOMPLET_RENAME", True),
        ]
    )
    monkeypatch.setattr(
        tab_bazy_module.QInputDialog,
        "getText",
        lambda *args, **kwargs: next(prompt_values),
    )

    opened_modules: list[str] = []
    opened_walls: list[str] = []
    opened_assemblies: list[str] = []
    new_targets: list[str] = []

    w.sig_open_module_requested.connect(opened_modules.append)
    w.sig_open_wall_requested.connect(opened_walls.append)
    w.sig_open_assembly_requested.connect(opened_assemblies.append)
    w.sig_new_module_requested.connect(lambda: new_targets.append("module"))
    w.sig_new_wall_requested.connect(lambda: new_targets.append("wall"))
    w.sig_new_assembly_requested.connect(lambda: new_targets.append("assembly"))

    module_item = w.tree_modules.topLevelItem(0).child(0)
    assert module_item is not None
    w.tree_modules.setCurrentItem(module_item)
    w.btn_open_module.click()
    assert opened_modules == ["BAZA_MODUL"]

    w.btn_duplicate_module.click()
    assert module_store.get("BAZA_MODUL_KOPIA") is not None

    module_item = _find_module_item(w, "BAZA_MODUL")
    assert module_item is not None
    w.tree_modules.setCurrentItem(module_item)
    w.btn_rename_module.click()
    assert module_store.get("BAZA_MODUL") is None
    assert module_store.get("BAZA_MODUL_RENAME") is not None

    renamed_module_item = _find_module_item(w, "BAZA_MODUL_RENAME")
    assert renamed_module_item is not None
    w.tree_modules.setCurrentItem(renamed_module_item)

    move_idx = w.cb_module_target_group.findData("wardrobe")
    assert move_idx >= 0
    w.cb_module_target_group.setCurrentIndex(move_idx)
    w.btn_move_module.click()
    moved_module = module_store.get("BAZA_MODUL_RENAME")
    assert moved_module is not None
    assert moved_module.base_group == "wardrobe"

    w.btn_new_module.click()
    assert new_targets[-1] == "module"

    w.tbl_walls.selectRow(0)
    w.btn_open_wall.click()
    assert opened_walls == ["BAZA_SCIANA"]

    w.tbl_walls.selectRow(0)
    w.btn_duplicate_wall.click()
    assert wall_store.get("BAZA_SCIANA_KOPIA") is not None

    w.tbl_walls.selectRow(0)
    w.btn_rename_wall.click()
    assert wall_store.get("BAZA_SCIANA") is None
    assert wall_store.get("BAZA_SCIANA_RENAME") is not None

    _select_wall_row(w, "BAZA_SCIANA_RENAME")

    w.btn_new_wall.click()
    assert new_targets[-1] == "wall"

    w.ed_client_name.setText("Klient B")
    w.ed_client_phone.setText("555-111")
    w.btn_client_add.click()

    assert client_store.get("Klient B") is not None
    assert w.tbl_clients.rowCount() == 1
    assert w.cb_order_client.findText("Klient B") >= 0

    w.ed_worker_name.setText("Jan Monter")
    w.ed_worker_role.setText("Pomiar")
    w.btn_worker_add.click()

    assert worker_store.get("Jan Monter") is not None
    assert w.tbl_workers.rowCount() == 1
    assert w.cb_order_worker.findText("Jan Monter") >= 0

    w.ed_order_code.setText("ORD-B")
    w.cb_order_client.setCurrentText("Klient B")
    w.cb_order_worker.setCurrentText("Jan Monter")
    w.cb_order_status.setCurrentText("Nowe")
    w.ed_order_address.setText("Gdansk")
    w.btn_order_add.click()

    loaded_order = order_store.get("ORD-B")
    assert loaded_order is not None
    assert loaded_order.worker_name == "Jan Monter"
    assert w.tbl_orders.rowCount() == 1

    w.tbl_assemblies.selectRow(0)
    w.btn_open_assembly.click()

    assert opened_assemblies == ["BAZA_KOMPLET"]

    w.tbl_assemblies.selectRow(0)
    w.btn_duplicate_assembly.click()
    assert assembly_store.get("BAZA_KOMPLET_KOPIA") is not None

    w.tbl_assemblies.selectRow(0)
    w.btn_rename_assembly.click()
    assert assembly_store.get("BAZA_KOMPLET") is None
    assert assembly_store.get("BAZA_KOMPLET_RENAME") is not None

    _select_assembly_row(w, "BAZA_KOMPLET_RENAME")

    w.btn_new_assembly.click()
    assert new_targets[-1] == "assembly"

    w.btn_delete_assembly.click()
    assert assembly_store.get("BAZA_KOMPLET_RENAME") is None

    renamed_module_item = _find_module_item(w, "BAZA_MODUL_RENAME")
    assert renamed_module_item is not None
    w.tree_modules.setCurrentItem(renamed_module_item)
    w.btn_delete_module.click()
    assert module_store.get("BAZA_MODUL_RENAME") is None

    _select_wall_row(w, "BAZA_SCIANA_RENAME")
    w.btn_delete_wall.click()
    assert wall_store.get("BAZA_SCIANA_RENAME") is None
