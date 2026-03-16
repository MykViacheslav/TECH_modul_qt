from pathlib import Path

from PyQt6.QtCore import QRect, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QColor, QImage, QPixmap


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
    w.cb_material_scope.setCurrentText("Front")
    w.cb_material_choice_status.setCurrentText("Wybrane finalnie")
    w.ed_material_choice_material.setText("MDF lakier")
    w.ed_material_choice_color.setText("Cashmere")
    w.ed_material_choice_code.setText("RAL 7044")
    w.ed_material_choice_notes.setText("Probka nr 2")
    QTest.mouseClick(w.btn_add_material_choice, Qt.MouseButton.LeftButton)

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
    assert len(saved_order.material_choices) == 1
    assert saved_order.material_choices[0]["scope"] == "Front"
    assert saved_order.material_choices[0]["status"] == "Wybrane finalnie"
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
    w1.cb_material_scope.setCurrentText("Korpus")
    w1.cb_material_choice_status.setCurrentText("Probka pokazana")
    w1.ed_material_choice_material.setText("Egger U702")
    w1.ed_material_choice_color.setText("Cashmere")
    w1.ed_material_choice_code.setText("U702 ST9")
    w1.ed_material_choice_notes.setText("Probka pokazana klientowi")
    QTest.mouseClick(w1.btn_add_material_choice, Qt.MouseButton.LeftButton)

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
    assert w2.tbl_material_choices.rowCount() == 1
    assert w2.tbl_material_choices.item(0, 0).text() == "Korpus"
    assert w2.tbl_material_choices.item(0, 2).text() == "Cashmere"


def test_nowe_zamowienie_tab_shows_image_preview_for_selected_architect_attachment(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.zamowienie.tab_nowe_zamowienie import TabNoweZamowienie

    image_path = tmp_path / "wizualizacja.png"
    image = QImage(240, 180, QImage.Format.Format_RGB32)
    image.fill(QColor("#d8c8b2"))
    assert image.save(str(image_path))

    w = TabNoweZamowienie()
    w.ed_architect_file.setText(str(image_path))
    w.cb_architect_kind.setCurrentText("Obraz")
    w.ed_architect_description.setText("Wizualizacja lazienki")
    QTest.mouseClick(w.btn_add_architect_attachment, Qt.MouseButton.LeftButton)

    w.tbl_architect_attachments.selectRow(0)
    app.processEvents()

    assert w.lst_architect_pages.count() == 1
    assert "wizualizacja.png | Obraz" in w.lab_architect_preview_info.text()
    assert not w.architect_crop_preview._pixmap.isNull()


def test_nowe_zamowienie_tab_builds_pdf_page_previews_for_selected_attachment(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.zamowienie.tab_nowe_zamowienie import TabNoweZamowienie

    pdf_path = tmp_path / "architekt.pdf"
    pdf_path.write_text("pdf", encoding="utf-8")

    def _fake_pdf_pages(self, path):
        img1 = QImage(100, 140, QImage.Format.Format_RGB32)
        img1.fill(QColor("#f5f1e8"))
        img2 = QImage(100, 140, QImage.Format.Format_RGB32)
        img2.fill(QColor("#d8e4ef"))
        return [
            {
                "index": 0,
                "label": "Strona 1",
                "thumb": QPixmap.fromImage(img1),
                "full": QPixmap.fromImage(img1),
            },
            {
                "index": 1,
                "label": "Strona 2",
                "thumb": QPixmap.fromImage(img2),
                "full": QPixmap.fromImage(img2),
            },
        ]

    monkeypatch.setattr(TabNoweZamowienie, "_build_pdf_page_previews", _fake_pdf_pages)

    w = TabNoweZamowienie()
    w.ed_architect_file.setText(str(pdf_path))
    w.cb_architect_kind.setCurrentText("PDF")
    w.ed_architect_description.setText("Rzuty od architekta")
    QTest.mouseClick(w.btn_add_architect_attachment, Qt.MouseButton.LeftButton)

    w.tbl_architect_attachments.selectRow(0)
    app.processEvents()

    assert w.lst_architect_pages.count() == 2
    assert "architekt.pdf | PDF | 2 stron" in w.lab_architect_preview_info.text()

    w.lst_architect_pages.setCurrentRow(1)
    app.processEvents()

    assert "Strona 2" in w.lab_architect_preview_info.text()
    assert not w.architect_crop_preview._pixmap.isNull()


def test_nowe_zamowienie_tab_can_save_selected_architect_fragment(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.zamowienie.tab_nowe_zamowienie import TabNoweZamowienie

    pdf_path = tmp_path / "architekt.pdf"
    pdf_path.write_text("pdf", encoding="utf-8")

    def _fake_pdf_pages(self, path):
        img = QImage(320, 240, QImage.Format.Format_RGB32)
        img.fill(QColor("#e7dcc9"))
        pix = QPixmap.fromImage(img)
        return [{"index": 0, "label": "Strona 1", "thumb": pix, "full": pix}]

    monkeypatch.setattr(TabNoweZamowienie, "_build_pdf_page_previews", _fake_pdf_pages)

    w = TabNoweZamowienie()
    w.ed_order_code.setText("ORDER-FRAGMENT-1")
    w.ed_architect_file.setText(str(pdf_path))
    w.cb_architect_kind.setCurrentText("PDF")
    w.ed_architect_description.setText("Rzut kuchni")
    QTest.mouseClick(w.btn_add_architect_attachment, Qt.MouseButton.LeftButton)
    w.tbl_architect_attachments.selectRow(0)
    app.processEvents()

    w.architect_crop_preview._recalculate_display_rect()
    display = w.architect_crop_preview._display_rect
    w.architect_crop_preview.set_selection_rect(QRect(display.left() + 20, display.top() + 20, 120, 90))
    w.cb_architect_fragment_target_kind.setCurrentText("Komplet")
    w.ed_architect_fragment_target_name.setText("Kuchnia salon")
    w.ed_architect_fragment_description.setText("Wizualizacja wyspy")
    QTest.mouseClick(w.btn_save_architect_fragment, Qt.MouseButton.LeftButton)

    assert w.tbl_architect_attachments.rowCount() == 2
    fragment_path = w.tbl_architect_attachments.item(1, 0).data(Qt.ItemDataRole.UserRole)
    assert fragment_path
    assert Path(str(fragment_path)).exists()
    assert w.tbl_architect_attachments.item(1, 1).text() == "Obraz"
    assert "Komplet / Kuchnia salon" in w.tbl_architect_attachments.item(1, 2).text()


def test_nowe_zamowienie_tab_shows_offer_reference_preview_and_final_materials(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.zamowienie.tab_nowe_zamowienie import TabNoweZamowienie

    image_path = tmp_path / "offer_ref.png"
    image = QImage(220, 140, QImage.Format.Format_RGB32)
    image.fill(QColor("#f1eadf"))
    assert image.save(str(image_path))

    w = TabNoweZamowienie()
    w._set_quote_items(
        [
            {
                "name": "RTV salon",
                "kind": "RTV",
                "description": "Szafka wiszaca i lamele",
            }
        ]
    )
    w._set_material_choices(
        [
            {
                "scope": "Front",
                "material": "MDF lakier",
                "color": "Cashmere",
                "code": "RAL 7044",
                "status": "Wybrane finalnie",
                "notes": "Wersja finalna",
            }
        ]
    )
    w._set_architect_attachments(
        [
            {
                "path": str(image_path),
                "kind": "Obraz",
                "description": "Wizualizacja RTV",
                "target_kind": "Oferta",
                "target_name": "Oferta klienta",
            }
        ]
    )
    w._refresh_summary()

    assert "RTV salon" in w.lab_offer_summary.text()
    assert "Finalne materialy: 1" in w.lab_offer_summary.text()
    assert w.tbl_offer_refs.rowCount() == 1
    assert w.tbl_offer_refs.item(0, 0).text() == "offer_ref.png"
    assert w.tbl_offer_refs.item(0, 1).text() == "Oferta klienta"
    assert "Wizualizacja RTV" in w.tbl_offer_refs.item(0, 2).text()
    assert w.lab_offer_ref_preview.pixmap() is not None
    assert not w.lab_offer_ref_preview.pixmap().isNull()


def test_nowe_zamowienie_tab_exports_offer_html(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    import src.tabs.zamowienie.tab_nowe_zamowienie as order_tab_module
    from src.tabs.zamowienie.tab_nowe_zamowienie import TabNoweZamowienie

    image_path = tmp_path / "offer_export.png"
    image = QImage(240, 160, QImage.Format.Format_RGB32)
    image.fill(QColor("#efe4d3"))
    assert image.save(str(image_path))

    export_path = tmp_path / "oferta_test.html"
    monkeypatch.setattr(
        order_tab_module.QFileDialog,
        "getSaveFileName",
        staticmethod(lambda *args, **kwargs: (str(export_path), "Pliki HTML (*.html)")),
    )

    w = TabNoweZamowienie()
    w.cb_client_name.setCurrentText("Klient Export")
    w.ed_order_code.setText("ORDER-EXPORT-1")
    w.cb_order_status.setCurrentText("Wycena")
    w.ed_order_address.setText("Warszawa, Testowa 5")
    w.cb_worker_name.setCurrentText("Jan Handlowiec")
    w._set_quote_items(
        [
            {
                "name": "RTV salon",
                "kind": "RTV",
                "description": "Zabudowa z lamelami",
            }
        ]
    )
    w._set_material_choices(
        [
            {
                "scope": "Front",
                "material": "MDF lakier",
                "color": "Cashmere",
                "code": "RAL 7044",
                "status": "Wybrane finalnie",
                "notes": "Wariant klienta A",
            }
        ]
    )
    w._set_architect_attachments(
        [
            {
                "path": str(image_path),
                "kind": "Obraz",
                "description": "Wizualizacja RTV",
                "target_kind": "Oferta",
                "target_name": "Oferta klienta",
            }
        ]
    )
    w._refresh_summary()

    QTest.mouseClick(w.btn_export_offer, Qt.MouseButton.LeftButton)

    assert export_path.exists()
    html = export_path.read_text(encoding="utf-8")
    assert "Oferta klienta" in html
    assert "Klient Export" in html
    assert "ORDER-EXPORT-1" in html
    assert "RTV salon" in html
    assert "RAL 7044" in html
    assert "RAZEM orientacyjnie" in html
    assert "data:image/png;base64," in html
    assert "Wyeksportowano oferte" in w.lab_status.text()


def test_nowe_zamowienie_tab_exports_offer_pdf(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    import src.tabs.zamowienie.tab_nowe_zamowienie as order_tab_module
    from src.tabs.zamowienie.tab_nowe_zamowienie import TabNoweZamowienie

    image_path = tmp_path / "offer_pdf.png"
    image = QImage(220, 120, QImage.Format.Format_RGB32)
    image.fill(QColor("#e8dccb"))
    assert image.save(str(image_path))

    export_path = tmp_path / "oferta_test.pdf"
    monkeypatch.setattr(
        order_tab_module.QFileDialog,
        "getSaveFileName",
        staticmethod(lambda *args, **kwargs: (str(export_path), "Pliki PDF (*.pdf)")),
    )

    w = TabNoweZamowienie()
    w.cb_client_name.setCurrentText("Klient PDF")
    w.ed_order_code.setText("ORDER-PDF-EXPORT")
    w.cb_order_status.setCurrentText("Wycena")
    w.ed_order_address.setText("Gdansk, Prosta 8")
    w._set_quote_items(
        [
            {
                "name": "Szafa master",
                "kind": "Szafa",
                "description": "Wnekowa z lustrem",
            }
        ]
    )
    w._set_material_choices(
        [
            {
                "scope": "Korpus",
                "material": "PB 18",
                "color": "Dab artisan",
                "code": "KAINDL-18",
                "status": "Wybrane finalnie",
                "notes": "Wersja finalna",
            }
        ]
    )
    w._set_architect_attachments(
        [
            {
                "path": str(image_path),
                "kind": "Obraz",
                "description": "Wizualizacja szafy",
                "target_kind": "Oferta",
                "target_name": "Oferta klienta",
            }
        ]
    )
    w._refresh_summary()

    QTest.mouseClick(w.btn_export_offer_pdf, Qt.MouseButton.LeftButton)

    assert export_path.exists()
    content = export_path.read_bytes()
    assert content.startswith(b"%PDF")
    assert len(content) > 1000
    assert "Wyeksportowano PDF oferty" in w.lab_status.text()


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
    assert isinstance(w.grp_material_choices, CollapsibleBlock)
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
        w.grp_material_choices,
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
