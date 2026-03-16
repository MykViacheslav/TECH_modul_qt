from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QDialog


def test_sciana_layout_tab_supports_layout_types_obstacles_and_photos(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.sciana.tab_sciana_layout import TabScianaLayout

    w = TabScianaLayout()

    assert w.cb_layout_type.findData("l") >= 0
    assert w.cb_layout_type.findData("c") >= 0

    w.cb_layout_type.setCurrentIndex(w.cb_layout_type.findData("c"))
    w.chk_island.setChecked(True)
    w.sp_wall_a.setValue(4200.0)
    w.sp_wall_b.setValue(2600.0)
    w.sp_wall_c.setValue(2400.0)
    w.sp_base_plinth.setValue(100.0)
    w.sp_upper_clearance.setValue(80.0)
    w.sp_base_offset_left.setValue(120.0)
    w.sp_base_offset_right.setValue(90.0)
    w.sp_upper_offset_left.setValue(140.0)
    w.sp_upper_offset_right.setValue(70.0)

    w.cb_obstacle_kind.setCurrentIndex(w.cb_obstacle_kind.findData("window"))
    w.cb_obstacle_opening.setCurrentIndex(w.cb_obstacle_opening.findData("left"))
    w.cb_obstacle_side.setCurrentIndex(w.cb_obstacle_side.findData("A"))
    w.ed_obstacle_name.setText("Okno glowne")
    w.sp_obstacle_x.setValue(850.0)
    w.sp_obstacle_bottom.setValue(900.0)
    w.sp_obstacle_w.setValue(1200.0)
    w.sp_obstacle_h.setValue(1400.0)
    w.sp_obstacle_d.setValue(120.0)
    w.btn_add_obstacle.click()

    w.ed_photo_path.setText("C:/projekty/sciana_kuchnia_01.jpg")
    w.ed_photo_caption.setText("Lewa strona kuchni")
    w.btn_add_photo.click()

    assert len(w._wall.obstacles) == 1
    assert len(w._wall.photos) == 1
    assert w.tbl_obstacles.rowCount() == 1
    assert w.tbl_photos.rowCount() == 1
    assert len(w.preview.scene.items()) > 0

    summary = w.lab_summary.text()
    assert "Typ ukladu: C" in summary
    assert "Widok z przodu:" in summary
    assert "Wyspa: tak" in summary
    assert "Dolny cokol: 100 mm" in summary
    assert "Gorny odstep: 80 mm" in summary
    assert "Dolne od lewej: 120 mm" in summary
    assert "Dolne od prawej: 90 mm" in summary
    assert "Gorne od lewej: 140 mm" in summary
    assert "Gorne od prawej: 70 mm" in summary
    assert "Przeszkody: 1" in summary
    assert "Zdjecia: 1" in summary
    assert "Detale przeszkod:" not in summary
    assert "Okno glowne: parapet 900 mm, otwor 1400 mm, Lewe" in w.lab_obstacle_details.text()


def test_sciana_layout_tab_drag_updates_obstacle_position(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.sciana.tab_sciana_layout import TabScianaLayout

    w = TabScianaLayout()
    w.resize(1400, 900)
    w.show()
    QTest.qWaitForWindowExposed(w)

    w.cb_layout_type.setCurrentIndex(w.cb_layout_type.findData("line"))
    w.cb_obstacle_kind.setCurrentIndex(w.cb_obstacle_kind.findData("window"))
    w.cb_obstacle_side.setCurrentIndex(w.cb_obstacle_side.findData("A"))
    w.ed_obstacle_name.setText("Okno 1")
    w.sp_obstacle_x.setValue(600.0)
    w.sp_obstacle_bottom.setValue(900.0)
    w.sp_obstacle_w.setValue(900.0)
    w.sp_obstacle_h.setValue(1200.0)
    w.sp_obstacle_d.setValue(120.0)
    w.btn_add_obstacle.click()

    front_rect = w.preview.scene_rect_for_obstacle(0, "front")
    assert front_rect is not None

    start = w.preview.mapFromScene(front_rect.center())
    end = w.preview.mapFromScene(front_rect.center().x() + 280.0, front_rect.center().y() - 140.0)

    QTest.mousePress(w.preview.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
    QTest.mouseMove(w.preview.viewport(), end)
    QTest.mouseRelease(w.preview.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, end)

    obstacle = w._wall.obstacles[0]
    assert float(obstacle.x_mm) > 600.0
    assert float(getattr(obstacle, "bottom_offset_mm", 0.0)) > 900.0


def test_sciana_layout_tab_editor_updates_selected_obstacle_live(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.sciana.tab_sciana_layout import TabScianaLayout

    w = TabScianaLayout()
    w.cb_layout_type.setCurrentIndex(w.cb_layout_type.findData("line"))
    w.cb_obstacle_kind.setCurrentIndex(w.cb_obstacle_kind.findData("window"))
    w.cb_obstacle_side.setCurrentIndex(w.cb_obstacle_side.findData("A"))
    w.ed_obstacle_name.setText("Okno 1")
    w.sp_obstacle_x.setValue(300.0)
    w.sp_obstacle_bottom.setValue(850.0)
    w.sp_obstacle_w.setValue(900.0)
    w.sp_obstacle_h.setValue(1200.0)
    w.sp_obstacle_d.setValue(120.0)
    w.btn_add_obstacle.click()

    w.tbl_obstacles.selectRow(0)

    w.sp_obstacle_x.setValue(700.0)
    w.sp_obstacle_bottom.setValue(1100.0)

    obstacle = w._wall.obstacles[0]
    assert float(obstacle.x_mm) == 700.0
    assert float(getattr(obstacle, "bottom_offset_mm", 0.0)) == 1100.0

    front_rect = w.preview.scene_rect_for_obstacle(0, "front")
    assert front_rect is not None
    assert abs(float(front_rect.left()) - 700.0) < 0.1


def test_sciana_layout_tab_hides_irrelevant_layout_fields(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.sciana.tab_sciana_layout import TabScianaLayout

    w = TabScianaLayout()

    assert w.sp_wall_b.isHidden()
    assert w.sp_wall_c.isHidden()
    assert w.sp_island_w.isHidden()
    assert w.sp_island_d.isHidden()
    assert w.sp_island_x.isHidden()
    assert w.sp_island_y.isHidden()

    w.cb_layout_type.setCurrentIndex(w.cb_layout_type.findData("c"))
    w.chk_island.setChecked(True)

    assert not w.sp_wall_b.isHidden()
    assert not w.sp_wall_c.isHidden()
    assert not w.sp_island_w.isHidden()
    assert not w.sp_island_d.isHidden()
    assert not w.sp_island_x.isHidden()
    assert not w.sp_island_y.isHidden()


def test_sciana_layout_tab_allows_large_depth_and_height_values(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.sciana.tab_sciana_layout import TabScianaLayout

    w = TabScianaLayout()

    assert float(w.sp_base_depth.maximum()) >= 3000.0
    assert float(w.sp_room_height.maximum()) >= 6000.0
    assert float(w.sp_island_d.maximum()) >= 3000.0
    assert float(w.sp_obstacle_d.maximum()) >= 3000.0

    w.sp_base_depth.setValue(3000.0)
    w.sp_room_height.setValue(6000.0)
    w.sp_island_d.setValue(3000.0)
    w.sp_obstacle_d.setValue(3000.0)

    assert float(w.sp_base_depth.value()) == 3000.0
    assert float(w.sp_room_height.value()) == 6000.0
    assert float(w.sp_island_d.value()) == 3000.0
    assert float(w.sp_obstacle_d.value()) == 3000.0


def test_sciana_layout_tab_uses_thin_top_wall_and_simple_view_labels(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.sciana.tab_sciana_layout import TabScianaLayout

    w = TabScianaLayout()
    w.cb_layout_type.setCurrentIndex(w.cb_layout_type.findData("line"))
    w.sp_base_depth.setValue(600.0)

    rect_a = w.preview._top_wall_rects.get("A")
    assert rect_a is not None
    assert float(rect_a.height()) <= 16.0

    texts = []
    for item in w.preview.scene.items():
        if hasattr(item, "text"):
            try:
                texts.append(str(item.text()))
            except Exception:
                pass

    assert "Widok z przodu - Sciana A" not in texts
    assert "Widok z gory" not in texts
    assert "A" in texts


def test_sciana_layout_tab_uses_separate_front_and_top_previews(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.sciana.tab_sciana_layout import TabScianaLayout

    w = TabScianaLayout()

    assert hasattr(w, "center_views_splitter")
    assert w.center_views_splitter.count() == 2
    assert str(getattr(w.preview, "_view_mode", "")) == "front"
    assert str(getattr(w.preview_top, "_view_mode", "")) == "top"
    assert int(w.preview.minimumHeight()) >= 360
    assert int(w.preview_top.minimumHeight()) >= 180


def test_sciana_layout_tab_front_and_top_previews_share_scale_for_simple_wall(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.sciana.tab_sciana_layout import TabScianaLayout

    w = TabScianaLayout()
    w.resize(1500, 950)
    w.show()
    QTest.qWaitForWindowExposed(w)
    QTest.qWait(50)

    front_scale = float(w.preview.transform().m11())
    top_scale = float(w.preview_top.transform().m11())

    assert front_scale > 0.0
    assert top_scale > 0.0
    assert abs(front_scale - top_scale) < 1e-6


def test_sciana_layout_tab_window_and_door_fields_are_contextual(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.sciana.tab_sciana_layout import TabScianaLayout

    w = TabScianaLayout()

    w.cb_obstacle_kind.setCurrentIndex(w.cb_obstacle_kind.findData("window"))
    label_bottom = w._obstacle_form.labelForField(w.sp_obstacle_bottom)
    label_height = w._obstacle_form.labelForField(w.sp_obstacle_h)
    label_open = w._obstacle_form.labelForField(w.cb_obstacle_opening)

    assert label_bottom is not None
    assert label_height is not None
    assert label_open is not None
    assert label_bottom.text() == "Parapet"
    assert label_height.text() == "Wysokosc otworu"
    assert not w.cb_obstacle_opening.isHidden()

    w.cb_obstacle_kind.setCurrentIndex(w.cb_obstacle_kind.findData("door"))
    assert label_bottom.text() == "Od podlogi"
    assert label_height.text() == "Wysokosc otworu"
    assert label_open.text() == "Kierunek otwierania"
    assert not w.cb_obstacle_opening.isHidden()

    w.cb_obstacle_kind.setCurrentIndex(w.cb_obstacle_kind.findData("projection"))
    assert label_bottom.text() == "Od podlogi"
    assert label_height.text() == "Wysokosc"
    assert w.cb_obstacle_opening.isHidden()


def test_sciana_layout_tab_technical_obstacle_fields_are_contextual(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.sciana.tab_sciana_layout import TabScianaLayout

    w = TabScianaLayout()

    label_bottom = w._obstacle_form.labelForField(w.sp_obstacle_bottom)
    label_width = w._obstacle_form.labelForField(w.sp_obstacle_w)
    label_height = w._obstacle_form.labelForField(w.sp_obstacle_h)
    label_depth = w._obstacle_form.labelForField(w.sp_obstacle_d)

    assert label_bottom is not None
    assert label_width is not None
    assert label_height is not None
    assert label_depth is not None

    w.cb_obstacle_kind.setCurrentIndex(w.cb_obstacle_kind.findData("socket"))
    assert label_bottom.text() == "Wysokosc montazu"
    assert label_width.text() == "Szerokosc pola"
    assert label_height.text() == "Wysokosc pola"
    assert label_depth.text() == "Glebokosc puszki"
    assert w.cb_obstacle_opening.isHidden()

    w.cb_obstacle_kind.setCurrentIndex(w.cb_obstacle_kind.findData("plumbing"))
    assert label_bottom.text() == "Wysokosc przylaczy"
    assert label_width.text() == "Szerokosc strefy"
    assert label_height.text() == "Wysokosc strefy"
    assert label_depth.text() == "Glebokosc strefy"

    w.cb_obstacle_kind.setCurrentIndex(w.cb_obstacle_kind.findData("radiator"))
    assert label_bottom.text() == "Od podlogi"
    assert label_width.text() == "Szerokosc grzejnika"
    assert label_height.text() == "Wysokosc grzejnika"
    assert label_depth.text() == "Odstawanie"

    w.cb_obstacle_kind.setCurrentIndex(w.cb_obstacle_kind.findData("sill"))
    assert label_bottom.text() == "Wysokosc parapetu"
    assert label_width.text() == "Dlugosc parapetu"
    assert label_height.text() == "Wysokosc pasa"
    assert label_depth.text() == "Wysuniecie"


def test_sciana_layout_tab_has_collapsible_blocks_with_compact_start(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.sciana.tab_sciana_layout import TabScianaLayout

    w = TabScianaLayout()

    assert w._get_collapsible_block_body(w.blk_main) is not None
    assert w._get_collapsible_block_body(w.blk_store) is not None
    assert w._get_collapsible_block_body(w.blk_obstacles) is not None
    assert w._get_collapsible_block_body(w.blk_photos) is not None
    assert w._get_collapsible_block_body(w.blk_notes) is not None
    assert w._get_collapsible_block_body(w.blk_obstacle_details) is not None

    assert w.blk_main.is_expanded()
    assert w.blk_store.is_expanded()
    assert w.blk_obstacles.is_expanded()
    assert not w.blk_photos.is_expanded()
    assert not w.blk_notes.is_expanded()
    assert w.blk_summary.is_expanded()
    assert not w.blk_obstacle_details.is_expanded()
    assert not w.blk_suggestions.is_expanded()

    assert not w._get_collapsible_block_body(w.blk_main).isHidden()  # type: ignore[union-attr]
    assert not w._get_collapsible_block_body(w.blk_store).isHidden()  # type: ignore[union-attr]
    assert not w._get_collapsible_block_body(w.blk_obstacles).isHidden()  # type: ignore[union-attr]
    assert w._get_collapsible_block_body(w.blk_photos).isHidden()  # type: ignore[union-attr]
    assert w._get_collapsible_block_body(w.blk_notes).isHidden()  # type: ignore[union-attr]
    assert not w._get_collapsible_block_body(w.blk_summary).isHidden()  # type: ignore[union-attr]
    assert w._get_collapsible_block_body(w.blk_obstacle_details).isHidden()  # type: ignore[union-attr]
    assert w._get_collapsible_block_body(w.blk_suggestions).isHidden()  # type: ignore[union-attr]


def test_sciana_layout_tab_loads_architect_reference_images_into_wall_photos(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.order_models import OrderDef
    from src.storage.order_store_json import OrderStoreJson
    from src.tabs.sciana.tab_sciana_layout import TabScianaLayout

    image_path = tmp_path / "wizualizacja_sciany.png"
    image_path.write_bytes(b"fake")

    order_store = OrderStoreJson(path=tmp_path / "orders.json")
    order_store.save_new(
        OrderDef(
            code="ORDER-ARCH-01",
            attachments=[
                {
                    "path": str(image_path),
                    "kind": "Obraz",
                    "description": "Widok szafy",
                    "target_kind": "Sciana",
                    "target_name": "Szafa wejsciowa",
                    "source_page": "Strona 3",
                }
            ],
        )
    )

    w = TabScianaLayout(order_store=order_store)
    w.start_new_wall_from_order_context(
        {
            "order_name": "ORDER-ARCH-01",
            "quote_item_name": "Szafa wejsciowa",
            "quote_item_kind": "Szafa",
        }
    )

    assert len(w._wall.photos) == 1
    assert w.tbl_photos.rowCount() == 1
    assert w.tbl_photos.item(0, 0).text() == str(image_path)
    assert "Widok szafy" in w.tbl_photos.item(0, 1).text()
    assert "Strona 3" in w.tbl_photos.item(0, 1).text()
    assert w.blk_photos.is_expanded()


def test_sciana_layout_tab_preview_uses_simple_obstacle_labels(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.sciana.tab_sciana_layout import TabScianaLayout

    w = TabScianaLayout()
    w.cb_obstacle_kind.setCurrentIndex(w.cb_obstacle_kind.findData("window"))
    w.ed_obstacle_name.setText("Okno glowne")
    w.sp_obstacle_x.setValue(900.0)
    w.sp_obstacle_bottom.setValue(722.0)
    w.sp_obstacle_w.setValue(1200.0)
    w.sp_obstacle_h.setValue(1400.0)
    w.btn_add_obstacle.click()

    texts = []
    for item in w.preview.scene.items():
        if hasattr(item, "text"):
            try:
                texts.append(str(item.text()))
            except Exception:
                pass

    assert "Okno" in texts
    assert "Parapet 722" not in texts


def test_sciana_layout_tab_preview_hides_non_selected_small_technical_labels(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.sciana.tab_sciana_layout import TabScianaLayout

    w = TabScianaLayout()
    w.cb_obstacle_kind.setCurrentIndex(w.cb_obstacle_kind.findData("socket"))
    w.cb_obstacle_side.setCurrentIndex(w.cb_obstacle_side.findData("A"))
    w.ed_obstacle_name.setText("Gniazdo AGD")
    w.sp_obstacle_x.setValue(1200.0)
    w.sp_obstacle_bottom.setValue(250.0)
    w.sp_obstacle_w.setValue(80.0)
    w.sp_obstacle_h.setValue(80.0)
    w.sp_obstacle_d.setValue(60.0)
    w.btn_add_obstacle.click()

    w.tbl_obstacles.clearSelection()
    w._selected_obstacle_index = -1
    w.preview.set_selected_obstacle_index(-1)
    w.preview_top.set_selected_obstacle_index(-1)
    w._render_previews()

    front_texts = []
    for item in w.preview.scene.items():
        if hasattr(item, "text"):
            try:
                front_texts.append(str(item.text()))
            except Exception:
                pass

    top_texts = []
    for item in w.preview_top.scene.items():
        if hasattr(item, "text"):
            try:
                top_texts.append(str(item.text()))
            except Exception:
                pass

    assert "Gniazdko" not in front_texts
    assert "Gniazdko" not in top_texts


def test_sciana_layout_tab_front_dimension_boxes_edit_selected_obstacle(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.sciana.tab_sciana_layout import TabScianaLayout

    w = TabScianaLayout()
    w.resize(1400, 900)
    w.show()
    QTest.qWaitForWindowExposed(w)

    w.cb_layout_type.setCurrentIndex(w.cb_layout_type.findData("line"))
    w.cb_obstacle_kind.setCurrentIndex(w.cb_obstacle_kind.findData("window"))
    w.cb_obstacle_side.setCurrentIndex(w.cb_obstacle_side.findData("A"))
    w.ed_obstacle_name.setText("Okno z edytorem")
    w.sp_obstacle_x.setValue(500.0)
    w.sp_obstacle_bottom.setValue(700.0)
    w.sp_obstacle_w.setValue(900.0)
    w.sp_obstacle_h.setValue(1200.0)
    w.sp_obstacle_d.setValue(120.0)
    w.btn_add_obstacle.click()

    w.tbl_obstacles.selectRow(0)

    assert w.preview.front_dimension_editor("x") is None
    assert w.preview.front_dimension_editor("bottom") is None

    front_rect = w.preview.scene_rect_for_obstacle(0, "front")
    assert front_rect is not None

    start = w.preview.mapFromScene(front_rect.center())
    end = w.preview.mapFromScene(front_rect.center().x() + 120.0, front_rect.center().y() - 80.0)

    QTest.mousePress(w.preview.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
    QTest.mouseMove(w.preview.viewport(), end)

    editor_x = w.preview.front_dimension_editor("x")
    editor_bottom = w.preview.front_dimension_editor("bottom")

    assert editor_x is not None
    assert editor_bottom is not None
    assert 120 <= editor_x.width() <= 130
    assert 120 <= editor_bottom.width() <= 130

    QTest.mouseRelease(w.preview.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, end)

    assert w.preview.front_dimension_editor("x") is None
    assert w.preview.front_dimension_editor("bottom") is None


def test_sciana_layout_tab_supports_technical_obstacles_in_table_and_summary(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.sciana.tab_sciana_layout import TabScianaLayout

    w = TabScianaLayout()

    w.cb_obstacle_kind.setCurrentIndex(w.cb_obstacle_kind.findData("socket"))
    w.cb_obstacle_side.setCurrentIndex(w.cb_obstacle_side.findData("A"))
    w.ed_obstacle_name.setText("Gniazdo AGD")
    w.sp_obstacle_x.setValue(1200.0)
    w.sp_obstacle_bottom.setValue(250.0)
    w.sp_obstacle_w.setValue(80.0)
    w.sp_obstacle_h.setValue(80.0)
    w.sp_obstacle_d.setValue(60.0)
    w.btn_add_obstacle.click()

    w.tbl_obstacles.clearSelection()
    w._selected_obstacle_index = -1
    w.preview.set_selected_obstacle_index(-1)

    w.cb_obstacle_kind.setCurrentIndex(w.cb_obstacle_kind.findData("radiator"))
    w.ed_obstacle_name.setText("Grzejnik pod oknem")
    w.sp_obstacle_x.setValue(900.0)
    w.sp_obstacle_bottom.setValue(120.0)
    w.sp_obstacle_w.setValue(1000.0)
    w.sp_obstacle_h.setValue(600.0)
    w.sp_obstacle_d.setValue(120.0)
    w.btn_add_obstacle.click()

    assert len(w._wall.obstacles) == 2
    assert w.tbl_obstacles.rowCount() == 2
    row_texts = [w.tbl_obstacles.item(row, 3).text() for row in range(w.tbl_obstacles.rowCount())]
    assert any("montaz=250" in text for text in row_texts)
    assert any("odstawanie=120" in text for text in row_texts)

    summary = w.lab_summary.text()
    assert "Elementy techniczne: 2" in summary
    details = w.lab_obstacle_details.text()
    assert "- Gniazdo AGD: montaz 250 mm, pole 80 x 80 mm" in details
    assert "- Grzejnik pod oknem: dol 120 mm, 1000 x 600 mm, odstawanie 120 mm" in details


def test_sciana_layout_tab_can_save_and_load_wall_with_client_and_order(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.client_models import ClientDef
    from src.domain.order_models import OrderDef
    from src.domain.wall_models import WallLayoutDef
    from src.domain.worker_models import WorkerDef
    from src.storage.client_store_json import ClientStoreJson
    from src.storage.order_store_json import OrderStoreJson
    from src.storage.wall_store_json import WallStoreJson
    from src.storage.worker_store_json import WorkerStoreJson
    from src.tabs.sciana import tab_sciana_layout as wall_tab_module
    from src.tabs.sciana.tab_sciana_layout import TabScianaLayout

    store = WallStoreJson(path=tmp_path / "walls.json")
    client_store = ClientStoreJson(path=tmp_path / "clients.json")
    order_store = OrderStoreJson(path=tmp_path / "orders.json")
    worker_store = WorkerStoreJson(path=tmp_path / "workers.json")
    client_store.save_new(ClientDef(name="Klient UI"))
    client_store.save_new(ClientDef(name="Klient LOAD"))
    worker_store.save_new(WorkerDef(name="Jan Monter"))
    worker_store.save_new(WorkerDef(name="Anna Projekt"))
    order_store.save_new(
        OrderDef(code="ORDER-UI-01", client_name="Klient UI", worker_name="Jan Monter", status="Nowe", site_address="Warszawa 1")
    )
    order_store.save_new(
        OrderDef(
            code="ORDER-LOAD",
            client_name="Klient LOAD",
            worker_name="Anna Projekt",
            status="Pomiar",
            site_address="Krakow, Lipowa 5",
        )
    )
    w = TabScianaLayout(store=store, client_store=client_store, order_store=order_store, worker_store=worker_store)

    w.ed_name.setText("SCIANA_UI")
    w.cb_client.setCurrentIndex(w.cb_client.findData("Klient UI"))
    w.cb_order.setCurrentIndex(w.cb_order.findData("ORDER-UI-01"))
    w.cb_worker.setCurrentIndex(w.cb_worker.findData("Jan Monter"))
    w.cb_layout_type.setCurrentIndex(w.cb_layout_type.findData("l"))
    w.sp_wall_a.setValue(4300.0)
    w.btn_save.click()

    saved = store.get("SCIANA_UI")
    assert saved is not None
    assert saved.client_name == "Klient UI"
    assert saved.order_name == "ORDER-UI-01"
    assert saved.worker_name == "Jan Monter"
    assert saved.layout_type == "l"

    class _FakeLoadWallDialog:
        DialogCode = QDialog.DialogCode

        def __init__(self, _parent, _store):
            self._wall = WallLayoutDef(
                name="SCIANA_WCZYTANA",
                client_name="Klient LOAD",
                order_name="ORDER-LOAD",
                worker_name="Anna Projekt",
                layout_type="c",
                wall_a_width_mm=3900.0,
            )

        def exec(self):
            return self.DialogCode.Accepted

        def selected_wall(self):
            return self._wall

    monkeypatch.setattr(wall_tab_module, "LoadWallDialog", _FakeLoadWallDialog)

    w.btn_load.click()

    assert w.ed_name.text() == "SCIANA_WCZYTANA"
    assert w.cb_client.currentData() == "Klient LOAD"
    assert w.cb_order.currentData() == "ORDER-LOAD"
    assert w.cb_worker.currentData() == "Anna Projekt"
    assert w.cb_layout_type.currentData() == "c"
    assert "Klient: Klient LOAD" in w.lab_summary.text()
    assert "Zamowienie: ORDER-LOAD" in w.lab_summary.text()
    assert "Pracownik: Anna Projekt" in w.lab_summary.text()
    assert "Status zamowienia: Pomiar" in w.lab_summary.text()
    assert "Adres realizacji: Krakow, Lipowa 5" in w.lab_summary.text()


def test_sciana_layout_tab_filters_orders_by_selected_client(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.client_models import ClientDef
    from src.domain.order_models import OrderDef
    from src.storage.client_store_json import ClientStoreJson
    from src.storage.order_store_json import OrderStoreJson
    from src.tabs.sciana.tab_sciana_layout import TabScianaLayout

    client_store = ClientStoreJson(path=tmp_path / "clients.json")
    order_store = OrderStoreJson(path=tmp_path / "orders.json")
    client_store.save_new(ClientDef(name="Klient A"))
    client_store.save_new(ClientDef(name="Klient B"))
    order_store.save_new(OrderDef(code="ORDER-A-01", client_name="Klient A"))
    order_store.save_new(OrderDef(code="ORDER-A-02", client_name="Klient A"))
    order_store.save_new(OrderDef(code="ORDER-B-01", client_name="Klient B"))

    w = TabScianaLayout(client_store=client_store, order_store=order_store)

    w.cb_client.setCurrentIndex(w.cb_client.findData("Klient A"))
    order_codes_a = [str(w.cb_order.itemData(i) or "") for i in range(w.cb_order.count())]
    assert "ORDER-A-01" in order_codes_a
    assert "ORDER-A-02" in order_codes_a
    assert "ORDER-B-01" not in order_codes_a

    w.cb_client.setCurrentIndex(w.cb_client.findData("Klient B"))
    order_codes_b = [str(w.cb_order.itemData(i) or "") for i in range(w.cb_order.count())]
    assert "ORDER-B-01" in order_codes_b
    assert "ORDER-A-01" not in order_codes_b


def test_sciana_layout_tab_preview_auto_fits_when_resized(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.sciana.tab_sciana_layout import TabScianaLayout

    w = TabScianaLayout()
    w.resize(1500, 950)
    w.show()
    QTest.qWaitForWindowExposed(w)

    w.cb_obstacle_kind.setCurrentIndex(w.cb_obstacle_kind.findData("window"))
    w.cb_obstacle_side.setCurrentIndex(w.cb_obstacle_side.findData("A"))
    w.ed_obstacle_name.setText("Okno skala")
    w.sp_obstacle_x.setValue(700.0)
    w.sp_obstacle_bottom.setValue(850.0)
    w.sp_obstacle_w.setValue(1100.0)
    w.sp_obstacle_h.setValue(1200.0)
    w.sp_obstacle_d.setValue(120.0)
    w.btn_add_obstacle.click()

    scale_before = float(w.preview.transform().m11())
    w.resize(980, 900)
    QTest.qWait(50)
    scale_after = float(w.preview.transform().m11())

    assert scale_before > 0.0
    assert scale_after > 0.0
    assert abs(scale_after - scale_before) > 1e-6


def test_sciana_layout_tab_stores_zabudowa_parameters(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.sciana.tab_sciana_layout import TabScianaLayout

    w = TabScianaLayout()
    w.sp_base_plinth.setValue(120.0)
    w.sp_upper_clearance.setValue(90.0)
    w.sp_base_offset_left.setValue(250.0)
    w.sp_base_offset_right.setValue(180.0)
    w.sp_upper_offset_left.setValue(210.0)
    w.sp_upper_offset_right.setValue(160.0)

    assert float(getattr(w._wall, "base_plinth_mm", 0.0)) == 120.0
    assert float(getattr(w._wall, "upper_clearance_mm", 0.0)) == 90.0
    assert float(getattr(w._wall, "base_offset_left_mm", 0.0)) == 250.0
    assert float(getattr(w._wall, "base_offset_right_mm", 0.0)) == 180.0
    assert float(getattr(w._wall, "upper_offset_left_mm", 0.0)) == 210.0
    assert float(getattr(w._wall, "upper_offset_right_mm", 0.0)) == 160.0
