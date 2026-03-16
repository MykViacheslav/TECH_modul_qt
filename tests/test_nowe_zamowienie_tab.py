from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication


def test_nowe_zamowienie_tab_saves_client_worker_and_order(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.storage.client_store_json import ClientStoreJson
    from src.storage.order_store_json import OrderStoreJson
    from src.storage.worker_store_json import WorkerStoreJson
    from src.tabs.zamowienie.tab_nowe_zamowienie import TabNoweZamowienie

    client_store = ClientStoreJson(path=tmp_path / "clients.json")
    order_store = OrderStoreJson(path=tmp_path / "orders.json")
    worker_store = WorkerStoreJson(path=tmp_path / "workers.json")

    w = TabNoweZamowienie(
        client_store=client_store,
        order_store=order_store,
        worker_store=worker_store,
    )

    w.cb_client_name.setCurrentText("Klient Test")
    w.ed_client_phone.setText("500-100-200")
    w.ed_client_email.setText("test@example.com")
    w.ed_client_city.setText("Krakow")

    w.ed_order_code.setText("ORD-NEW-1")
    w.cb_order_status.setCurrentText("Nowe")
    w.ed_order_address.setText("Krakow, Testowa 1")

    w.cb_worker_name.setCurrentText("Jan Pomiar")
    w.ed_worker_role.setText("Pomiar")
    w.ed_worker_phone.setText("600-200-300")

    QTest.mouseClick(w.btn_save_new, Qt.MouseButton.LeftButton)

    saved_client = client_store.get("Klient Test")
    saved_worker = worker_store.get("Jan Pomiar")
    saved_order = order_store.get("ORD-NEW-1")

    assert saved_client is not None
    assert saved_client.city == "Krakow"
    assert saved_worker is not None
    assert saved_worker.role == "Pomiar"
    assert saved_order is not None
    assert saved_order.client_name == "Klient Test"
    assert saved_order.worker_name == "Jan Pomiar"
    assert "Zapisano zamowienie" in w.lab_status.text()


def test_nowe_zamowienie_tab_loads_existing_client_details_from_base(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.client_models import ClientDef
    from src.storage.client_store_json import ClientStoreJson
    from src.tabs.zamowienie.tab_nowe_zamowienie import TabNoweZamowienie

    client_store = ClientStoreJson(path=tmp_path / "clients.json")
    client_store.save_new(
        ClientDef(
            name="Klient Baza",
            phone="777-111-222",
            email="baza@example.com",
            city="Warszawa",
            notes="Z bazy",
        )
    )

    w = TabNoweZamowienie(client_store=client_store)
    w.cb_client_name.setCurrentText("Klient Baza")

    assert w.ed_client_phone.text() == "777-111-222"
    assert w.ed_client_email.text() == "baza@example.com"
    assert w.ed_client_city.text() == "Warszawa"


def test_nowe_zamowienie_tab_can_save_client_directly_to_base(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.storage.client_store_json import ClientStoreJson
    from src.tabs.zamowienie.tab_nowe_zamowienie import TabNoweZamowienie

    client_store = ClientStoreJson(path=tmp_path / "clients.json")
    w = TabNoweZamowienie(client_store=client_store)

    w.cb_client_name.setCurrentText("Klient Bezposredni")
    w.ed_client_phone.setText("123-456-789")
    w.ed_client_city.setText("Lodz")

    QTest.mouseClick(w.btn_save_client, Qt.MouseButton.LeftButton)

    client = client_store.get("Klient Bezposredni")
    assert client is not None
    assert client.phone == "123-456-789"
    assert "Zapisano klienta" in w.lab_status.text()


def test_nowe_zamowienie_tab_can_pick_client_from_base_dialog(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.client_models import ClientDef
    from src.storage.client_store_json import ClientStoreJson
    from src.tabs.zamowienie import tab_nowe_zamowienie as order_tab_module
    from src.tabs.zamowienie.tab_nowe_zamowienie import TabNoweZamowienie

    client_store = ClientStoreJson(path=tmp_path / "clients.json")
    client_store.save_new(ClientDef(name="Klient Dialog", city="Poznan"))

    monkeypatch.setattr(
        order_tab_module.QInputDialog,
        "getItem",
        lambda *args, **kwargs: ("Klient Dialog", True),
    )

    w = TabNoweZamowienie(client_store=client_store)
    QTest.mouseClick(w.btn_pick_client, Qt.MouseButton.LeftButton)

    assert w.cb_client_name.currentText() == "Klient Dialog"
    assert w.ed_client_city.text() == "Poznan"


def test_nowe_zamowienie_tab_restores_saved_draft_on_next_open(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.storage.order_draft_store_json import OrderDraftStoreJson
    from src.tabs.zamowienie.tab_nowe_zamowienie import TabNoweZamowienie

    draft_store = OrderDraftStoreJson(path=tmp_path / "order_draft.json")

    w1 = TabNoweZamowienie(draft_store=draft_store)
    w1.cb_client_name.setCurrentText("Klient Draft")
    w1.ed_client_phone.setText("123-123-123")
    w1.ed_order_code.setText("ORD-DRAFT-1")
    w1.ed_order_address.setText("Gdansk, Draft 5")
    w1.cb_worker_name.setCurrentText("Pracownik Draft")
    w1.ed_worker_role.setText("Kosztorys")
    attachment = tmp_path / "architekt.pdf"
    attachment.write_text("pdf", encoding="utf-8")
    w1.ed_architect_file.setText(str(attachment))
    w1.ed_architect_description.setText("Rzut lazienki")
    QTest.mouseClick(w1.btn_add_architect_attachment, Qt.MouseButton.LeftButton)
    w1.ed_quote_item_name.setText("Kuchnia salon")
    w1.cb_quote_item_kind.setCurrentText("Kuchnia")
    w1.ed_quote_item_description.setText("Wyspa + slupki")
    QTest.mouseClick(w1.btn_add_quote_item, Qt.MouseButton.LeftButton)

    w2 = TabNoweZamowienie(draft_store=draft_store)

    assert w2.cb_client_name.currentText() == "Klient Draft"
    assert w2.ed_client_phone.text() == "123-123-123"
    assert w2.ed_order_code.text() == "ORD-DRAFT-1"
    assert w2.ed_order_address.text() == "Gdansk, Draft 5"
    assert w2.cb_worker_name.currentText() == "Pracownik Draft"
    assert w2.ed_worker_role.text() == "Kosztorys"
    assert w2.tbl_architect_attachments.rowCount() == 1
    assert w2.tbl_architect_attachments.item(0, 0).text() == "architekt.pdf"
    assert w2.tbl_quote_items.rowCount() == 1
    assert w2.tbl_quote_items.item(0, 0).text() == "Kuchnia salon"


def test_nowe_zamowienie_tab_clear_removes_saved_draft(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.storage.order_draft_store_json import OrderDraftStoreJson
    from src.tabs.zamowienie.tab_nowe_zamowienie import TabNoweZamowienie

    draft_store = OrderDraftStoreJson(path=tmp_path / "order_draft.json")

    w1 = TabNoweZamowienie(draft_store=draft_store)
    w1.cb_client_name.setCurrentText("Klient Draft")
    w1.ed_order_code.setText("ORD-DRAFT-2")

    QTest.mouseClick(w1.btn_clear, Qt.MouseButton.LeftButton)

    w2 = TabNoweZamowienie(draft_store=draft_store)

    assert w2.cb_client_name.currentText() == ""
    assert w2.ed_order_code.text() == ""
    assert "Wyczyszczono karte i zapis roboczy." in w1.lab_status.text()


def test_nowe_zamowienie_tab_lists_multiple_walls_for_current_order(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.wall_models import WallLayoutDef
    from src.storage.wall_store_json import WallStoreJson
    from src.tabs.zamowienie.tab_nowe_zamowienie import TabNoweZamowienie

    wall_store = WallStoreJson(path=tmp_path / "walls.json")
    wall_store.save_new(WallLayoutDef(name="SCIANA_A", client_name="Klient 1", order_name="ORDER-1", layout_type="line"))
    wall_store.save_new(WallLayoutDef(name="SCIANA_B", client_name="Klient 1", order_name="ORDER-1", layout_type="l"))
    wall_store.save_new(WallLayoutDef(name="SCIANA_C", client_name="Klient 2", order_name="ORDER-2", layout_type="c"))

    w = TabNoweZamowienie(wall_store=wall_store)
    w.cb_client_name.setCurrentText("Klient 1")
    w.ed_order_code.setText("ORDER-1")

    assert w.tbl_walls.rowCount() == 2
    assert w.tbl_walls.item(0, 0).text() in {"SCIANA_A", "SCIANA_B"}
    assert w.tbl_walls.item(1, 0).text() in {"SCIANA_A", "SCIANA_B"}


def test_nowe_zamowienie_tab_can_open_selected_wall_from_order_list(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.wall_models import WallLayoutDef
    from src.storage.wall_store_json import WallStoreJson
    from src.tabs.zamowienie.tab_nowe_zamowienie import TabNoweZamowienie

    wall_store = WallStoreJson(path=tmp_path / "walls.json")
    wall_store.save_new(WallLayoutDef(name="SCIANA_OTWORZ", client_name="Klient 1", order_name="ORDER-OPEN"))

    w = TabNoweZamowienie(wall_store=wall_store)
    w.cb_client_name.setCurrentText("Klient 1")
    w.ed_order_code.setText("ORDER-OPEN")
    w.tbl_walls.selectRow(0)

    emitted: list[str] = []
    w.sig_open_existing_sciana_requested.connect(emitted.append)

    QTest.mouseClick(w.btn_open_wall, Qt.MouseButton.LeftButton)

    assert emitted == ["SCIANA_OTWORZ"]


def test_nowe_zamowienie_tab_can_open_quote_item_as_sciana_with_context(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.zamowienie.tab_nowe_zamowienie import TabNoweZamowienie

    w = TabNoweZamowienie()
    w.cb_client_name.setCurrentText("Klient Quote")
    w.ed_order_code.setText("ORDER-QUOTE-1")
    w.cb_worker_name.setCurrentText("Jan Quote")
    w.ed_quote_item_name.setText("Kuchnia salon")
    w.cb_quote_item_kind.setCurrentText("Kuchnia")
    w.ed_quote_item_description.setText("Wyspa + slupki")
    QTest.mouseClick(w.btn_add_quote_item, Qt.MouseButton.LeftButton)
    w.tbl_quote_items.selectRow(0)

    emitted: list[dict] = []
    w.sig_open_sciana_requested.connect(emitted.append)

    QTest.mouseClick(w.btn_quote_to_sciana, Qt.MouseButton.LeftButton)

    assert len(emitted) == 1
    assert emitted[0]["client_name"] == "Klient Quote"
    assert emitted[0]["order_name"] == "ORDER-QUOTE-1"
    assert emitted[0]["worker_name"] == "Jan Quote"
    assert emitted[0]["quote_item_name"] == "Kuchnia salon"
    assert emitted[0]["quote_item_kind"] == "Kuchnia"
    assert emitted[0]["quote_item_description"] == "Wyspa + slupki"


def test_nowe_zamowienie_tab_can_open_quote_item_as_komplet_with_context(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.zamowienie.tab_nowe_zamowienie import TabNoweZamowienie

    w = TabNoweZamowienie()
    w.cb_client_name.setCurrentText("Klient Quote")
    w.ed_order_code.setText("ORDER-QUOTE-2")
    w.cb_worker_name.setCurrentText("Anna Quote")
    w.ed_quote_item_name.setText("Szafa wejsciowa")
    w.cb_quote_item_kind.setCurrentText("Szafa")
    w.ed_quote_item_description.setText("Wnekowa z lustrem")
    QTest.mouseClick(w.btn_add_quote_item, Qt.MouseButton.LeftButton)
    w.tbl_quote_items.selectRow(0)

    emitted: list[dict] = []
    w.sig_open_komplet_requested.connect(emitted.append)

    QTest.mouseClick(w.btn_quote_to_komplet, Qt.MouseButton.LeftButton)

    assert len(emitted) == 1
    assert emitted[0]["client_name"] == "Klient Quote"
    assert emitted[0]["order_name"] == "ORDER-QUOTE-2"
    assert emitted[0]["worker_name"] == "Anna Quote"
    assert emitted[0]["quote_item_name"] == "Szafa wejsciowa"
    assert emitted[0]["quote_item_kind"] == "Szafa"
    assert emitted[0]["quote_item_description"] == "Wnekowa z lustrem"


def test_nowe_zamowienie_tab_uses_collapsible_blocks(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.zamowienie.tab_nowe_zamowienie import TabNoweZamowienie
    from src.ui.collapsible_block import CollapsibleBlock

    w = TabNoweZamowienie()

    assert isinstance(w.grp_client, CollapsibleBlock)
    assert isinstance(w.grp_order, CollapsibleBlock)
    assert isinstance(w.grp_worker, CollapsibleBlock)
    assert isinstance(w.grp_actions, CollapsibleBlock)
    assert isinstance(w.grp_architect, CollapsibleBlock)
    assert isinstance(w.grp_quote_items, CollapsibleBlock)
    assert isinstance(w.grp_walls, CollapsibleBlock)
    assert isinstance(w.grp_summary, CollapsibleBlock)
    assert not w.grp_worker.is_expanded()
    assert w.grp_summary.is_expanded()


def test_nowe_zamowienie_tab_places_order_and_actions_in_left_column(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.zamowienie.tab_nowe_zamowienie import TabNoweZamowienie

    w = TabNoweZamowienie()

    widgets = []
    for index in range(w.body_layout.count() - 1):
        item = w.body_layout.itemAt(index)
        if item is not None and item.widget() is not None:
            widgets.append(item.widget())

    assert widgets == [
        w.grp_client,
        w.grp_order,
        w.grp_worker,
        w.grp_actions,
        w.grp_architect,
        w.grp_quote_items,
        w.grp_walls,
        w.grp_summary,
    ]


def test_nowe_zamowienie_tab_uses_scroll_area_for_full_order_view(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.zamowienie.tab_nowe_zamowienie import TabNoweZamowienie

    w = TabNoweZamowienie()

    assert w.scroll_area.widgetResizable()
    assert w.scroll_area.widget() is w.page_widget


def test_nowe_zamowienie_tab_shows_order_costs_and_materials_from_assemblies(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.assembly_models import AssemblyModuleItemDef, FurnitureAssemblyDef
    from src.domain.module_models import ModuleDef
    from src.storage.assembly_store_json import AssemblyStoreJson
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.tabs.zamowienie.tab_nowe_zamowienie import TabNoweZamowienie

    assembly_store = AssemblyStoreJson(path=tmp_path / "assemblies.json")
    catalog = CatalogStoreJson(path=tmp_path / "catalog.json")

    module = ModuleDef(
        name="MOD_KOSZT",
        width_mm=700.0,
        height_mm=800.0,
        depth_mm=525.0,
        shelf_count=1,
        visible_parts={"side_left", "side_right", "top", "bottom", "shelf", "front", "back"},
        materials={"carcass": "PB18", "front": "MDF19", "back": "HDF2.5"},
    )

    assembly_store.save_new(
        FurnitureAssemblyDef(
            name="KOMPLET_KOSZT",
            client_name="Klient Koszt",
            order_name="ORDER-KOSZT",
            items=[
                AssemblyModuleItemDef(
                    source_name="MOD_KOSZT",
                    instance_name="MOD_KOSZT",
                    module=module,
                )
            ],
        )
    )

    w = TabNoweZamowienie(
        assembly_store=assembly_store,
        catalog=catalog,
    )
    w.cb_client_name.setCurrentText("Klient Koszt")
    w.ed_order_code.setText("ORDER-KOSZT")

    assert "Komplety: 1" in w.lab_cost_summary.text()
    assert "RAZEM:" in w.lab_cost_summary.text()
    assert w.tbl_order_assemblies.rowCount() == 1
    assert w.tbl_order_assemblies.item(0, 0).text() == "KOMPLET_KOSZT"
    assert w.tbl_order_materials.rowCount() >= 1

    material_labels = {
        str(w.tbl_order_materials.item(row, 0).text())
        for row in range(w.tbl_order_materials.rowCount())
        if w.tbl_order_materials.item(row, 0) is not None
    }
    assert any("PB18" in label or "MDF19" in label or "HDF2.5" in label for label in material_labels)


def test_nowe_zamowienie_tab_shows_each_assembly_cost_separately(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.assembly_models import AssemblyModuleItemDef, FurnitureAssemblyDef
    from src.domain.module_models import ModuleDef
    from src.storage.assembly_store_json import AssemblyStoreJson
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.tabs.zamowienie.tab_nowe_zamowienie import TabNoweZamowienie

    assembly_store = AssemblyStoreJson(path=tmp_path / "assemblies.json")
    catalog = CatalogStoreJson(path=tmp_path / "catalog.json")

    kitchen_module = ModuleDef(
        name="MOD_KUCHNIA",
        width_mm=700.0,
        height_mm=800.0,
        depth_mm=525.0,
        shelf_count=1,
        visible_parts={"side_left", "side_right", "top", "bottom", "shelf", "front", "back"},
        materials={"carcass": "PB18", "front": "MDF19", "back": "HDF2.5"},
    )
    wardrobe_module = ModuleDef(
        name="MOD_SZAFA",
        width_mm=1000.0,
        height_mm=2200.0,
        depth_mm=620.0,
        shelf_count=3,
        visible_parts={"side_left", "side_right", "top", "bottom", "shelf", "front", "back"},
        materials={"carcass": "PB18", "front": "MDF19", "back": "HDF2.5"},
    )

    assembly_store.save_new(
        FurnitureAssemblyDef(
            name="KUCHNIA",
            client_name="Klient Rozbicie",
            order_name="ORDER-ROZBICIE",
            items=[
                AssemblyModuleItemDef(
                    source_name="MOD_KUCHNIA",
                    instance_name="MOD_KUCHNIA",
                    module=kitchen_module,
                )
            ],
        )
    )
    assembly_store.save_new(
        FurnitureAssemblyDef(
            name="SZAFA",
            client_name="Klient Rozbicie",
            order_name="ORDER-ROZBICIE",
            items=[
                AssemblyModuleItemDef(
                    source_name="MOD_SZAFA",
                    instance_name="MOD_SZAFA",
                    module=wardrobe_module,
                )
            ],
        )
    )

    w = TabNoweZamowienie(
        assembly_store=assembly_store,
        catalog=catalog,
    )
    w.cb_client_name.setCurrentText("Klient Rozbicie")
    w.ed_order_code.setText("ORDER-ROZBICIE")

    assert "Komplety: 2" in w.lab_cost_summary.text()
    assert w.tbl_order_assemblies.rowCount() == 2

    names = {
        str(w.tbl_order_assemblies.item(row, 0).text())
        for row in range(w.tbl_order_assemblies.rowCount())
        if w.tbl_order_assemblies.item(row, 0) is not None
    }
    assert names == {"KUCHNIA", "SZAFA"}

    totals = [
        str(w.tbl_order_assemblies.item(row, 5).text())
        for row in range(w.tbl_order_assemblies.rowCount())
        if w.tbl_order_assemblies.item(row, 5) is not None
    ]
    assert all("zl" in total for total in totals)


def test_nowe_zamowienie_tab_saves_and_loads_architect_attachments_with_order(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.zamowienie import tab_nowe_zamowienie as order_tab_module
    from src.storage.order_store_json import OrderStoreJson
    from src.tabs.zamowienie.tab_nowe_zamowienie import TabNoweZamowienie

    order_store = OrderStoreJson(path=tmp_path / "orders.json")
    attachment = tmp_path / "wizka.pdf"
    attachment.write_text("pdf", encoding="utf-8")

    w = TabNoweZamowienie(order_store=order_store)
    w.cb_client_name.setCurrentText("Klient PDF")
    w.ed_order_code.setText("ORDER-PDF-1")
    w.ed_architect_file.setText(str(attachment))
    w.cb_architect_kind.setCurrentText("PDF")
    w.ed_architect_description.setText("Wizualizacja lazienki")
    QTest.mouseClick(w.btn_add_architect_attachment, Qt.MouseButton.LeftButton)
    QTest.mouseClick(w.btn_save_order, Qt.MouseButton.LeftButton)

    monkeypatch.setattr(
        order_tab_module.QInputDialog,
        "getItem",
        lambda *args, **kwargs: ("ORDER-PDF-1", True),
    )

    w2 = TabNoweZamowienie(order_store=order_store)
    QTest.mouseClick(w2.btn_pick_order, Qt.MouseButton.LeftButton)

    assert w2.tbl_architect_attachments.rowCount() == 1
    assert w2.tbl_architect_attachments.item(0, 0).text() == "wizka.pdf"
    assert w2.tbl_architect_attachments.item(0, 1).text() == "PDF"
    assert w2.tbl_architect_attachments.item(0, 2).text() == "Wizualizacja lazienki"


def test_nowe_zamowienie_tab_saves_and_loads_quote_items_with_order(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.zamowienie import tab_nowe_zamowienie as order_tab_module
    from src.storage.order_store_json import OrderStoreJson
    from src.tabs.zamowienie.tab_nowe_zamowienie import TabNoweZamowienie

    order_store = OrderStoreJson(path=tmp_path / "orders.json")

    w = TabNoweZamowienie(order_store=order_store)
    w.cb_client_name.setCurrentText("Klient Pozycja")
    w.ed_order_code.setText("ORDER-POS-1")
    w.ed_quote_item_name.setText("Szafa wneka")
    w.cb_quote_item_kind.setCurrentText("Szafa")
    w.ed_quote_item_description.setText("Przedpokoj, lustro i siedzisko")
    QTest.mouseClick(w.btn_add_quote_item, Qt.MouseButton.LeftButton)
    QTest.mouseClick(w.btn_save_order, Qt.MouseButton.LeftButton)

    monkeypatch.setattr(
        order_tab_module.QInputDialog,
        "getItem",
        lambda *args, **kwargs: ("ORDER-POS-1", True),
    )

    w2 = TabNoweZamowienie(order_store=order_store)
    QTest.mouseClick(w2.btn_pick_order, Qt.MouseButton.LeftButton)

    assert w2.tbl_quote_items.rowCount() == 1
    assert w2.tbl_quote_items.item(0, 0).text() == "Szafa wneka"
    assert w2.tbl_quote_items.item(0, 1).text() == "Szafa"
    assert w2.tbl_quote_items.item(0, 2).text() == "Przedpokoj, lustro i siedzisko"
