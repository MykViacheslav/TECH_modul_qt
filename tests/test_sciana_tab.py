import json

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QDialog


def _select_saved_module(tree, name: str) -> bool:
    for top_index in range(tree.topLevelItemCount()):
        group_item = tree.topLevelItem(top_index)
        for child_index in range(group_item.childCount()):
            child = group_item.child(child_index)
            if str(child.data(0, Qt.ItemDataRole.UserRole) or "") == name:
                tree.setCurrentItem(child)
                return True
    return False


def _visible_saved_module_names(tree) -> list[str]:
    names: list[str] = []
    for top_index in range(tree.topLevelItemCount()):
        group_item = tree.topLevelItem(top_index)
        for child_index in range(group_item.childCount()):
            child = group_item.child(child_index)
            names.append(str(child.data(0, Qt.ItemDataRole.UserRole) or ""))
    return names


def _scene_has_key(view, key: str) -> bool:
    for item in view.scene.items():
        try:
            if item.data(0) == key:
                return True
        except Exception:
            pass
    return False


def _scene_item_by_key(view, key: str):
    for item in view.scene.items():
        try:
            if item.data(0) == key:
                return item
        except Exception:
            pass
    return None


def test_sciana_tab_adds_saved_modules_and_aggregates_costs(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.core.module_parts_service import build_module_parts
    from src.domain.module_models import ModuleDef
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.storage.module_store_json import ModuleStoreJson
    from src.tabs.sciana.tab_sciana import TabSciana

    catalog = CatalogStoreJson()
    store = ModuleStoreJson()

    module = ModuleDef(
        name="BASE_1",
        width_mm=800.0,
        depth_mm=500.0,
        height_mm=720.0,
        shelf_count=1,
        visible_parts={"side_left", "side_right", "top", "bottom", "shelf", "front"},
        materials={"carcass": "PB18", "front": "MDF19", "back": "HDF2.5"},
    )
    module.parts = build_module_parts(module, catalog)
    store.save_new(module)

    w = TabSciana()
    assert _select_saved_module(w.tree_saved_modules, "BASE_1")

    w.btn_add_saved.click()

    assert len(w._assembly.items) == 1
    assert len(w._resolved_items) == 1
    assert w.tbl_items.rowCount() == 1
    assert "Liczba modulow: 1" in w.lab_summary.text()
    assert "RAZEM:" in w.lab_summary.text()


def test_sciana_tab_saved_module_library_supports_quick_filters_and_search(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.core.module_parts_service import build_module_parts
    from src.domain.module_models import ModuleDef
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.storage.module_store_json import ModuleStoreJson
    from src.tabs.sciana.tab_sciana import TabSciana

    catalog = CatalogStoreJson()
    store = ModuleStoreJson()

    lower = ModuleDef(name="LOWER_FAST", width_mm=600.0, depth_mm=510.0, height_mm=720.0, cabinet_kind="lower", module_type="legs")
    lower.parts = build_module_parts(lower, catalog)
    store.save_new(lower)

    upper = ModuleDef(name="UPPER_FAST", width_mm=600.0, depth_mm=320.0, height_mm=720.0, cabinet_kind="upper", module_type="hanging")
    upper.parts = build_module_parts(upper, catalog)
    store.save_new(upper)

    drawers = ModuleDef(
        name="SZUFLADY_80_FAST",
        width_mm=800.0,
        depth_mm=560.0,
        height_mm=720.0,
        cabinet_kind="lower",
        module_type="legs_plinth",
        facade_mode="drawers",
    )
    drawers.parts = build_module_parts(drawers, catalog)
    store.save_new(drawers)

    tall = ModuleDef(name="SLUPEK_FAST", width_mm=600.0, depth_mm=560.0, height_mm=2200.0, cabinet_kind="lower", module_type="legs_plinth")
    tall.parts = build_module_parts(tall, catalog)
    store.save_new(tall)

    corner = ModuleDef(name="NAROZNA_FAST", width_mm=900.0, depth_mm=900.0, height_mm=720.0, cabinet_kind="lower", module_type="corner")
    corner.parts = build_module_parts(corner, catalog)
    store.save_new(corner)

    w = TabSciana(module_store=store)
    w.show()
    app.processEvents()

    assert hasattr(w, "cb_saved_quick_group")
    assert hasattr(w, "cb_saved_front_variant")
    assert hasattr(w, "cb_saved_width_variant")
    assert hasattr(w, "ed_saved_search")

    idx_upper = w.cb_saved_quick_group.findData("upper")
    assert idx_upper >= 0
    w.cb_saved_quick_group.setCurrentIndex(idx_upper)
    app.processEvents()
    assert _visible_saved_module_names(w.tree_saved_modules) == ["UPPER_FAST"]

    idx_all = w.cb_saved_quick_group.findData("all")
    assert idx_all >= 0
    w.cb_saved_quick_group.setCurrentIndex(idx_all)
    w.ed_saved_search.setText("naroz")
    app.processEvents()
    assert _visible_saved_module_names(w.tree_saved_modules) == ["NAROZNA_FAST"]

    w.ed_saved_search.clear()
    idx_tall = w.cb_saved_quick_group.findData("tall")
    assert idx_tall >= 0
    w.cb_saved_quick_group.setCurrentIndex(idx_tall)
    app.processEvents()
    assert _visible_saved_module_names(w.tree_saved_modules) == ["SLUPEK_FAST"]

    idx_all = w.cb_saved_quick_group.findData("all")
    assert idx_all >= 0
    w.cb_saved_quick_group.setCurrentIndex(idx_all)
    idx_drawers = w.cb_saved_front_variant.findData("drawers")
    assert idx_drawers >= 0
    w.cb_saved_front_variant.setCurrentIndex(idx_drawers)
    app.processEvents()
    assert _visible_saved_module_names(w.tree_saved_modules) == ["SZUFLADY_80_FAST"]

    idx_front_all = w.cb_saved_front_variant.findData("all")
    assert idx_front_all >= 0
    w.cb_saved_front_variant.setCurrentIndex(idx_front_all)
    idx_width_60 = w.cb_saved_width_variant.findData("60")
    assert idx_width_60 >= 0
    w.cb_saved_width_variant.setCurrentIndex(idx_width_60)
    app.processEvents()
    assert set(_visible_saved_module_names(w.tree_saved_modules)) == {"LOWER_FAST", "UPPER_FAST", "SLUPEK_FAST"}


def test_sciana_tab_wall_selector_uses_short_readable_labels(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.wall_models import WallLayoutDef
    from src.storage.wall_store_json import WallStoreJson
    from src.tabs.sciana.tab_sciana import TabSciana

    wall_store = WallStoreJson(path=tmp_path / "walls_labels.json")
    wall_store.save_new(
        WallLayoutDef(
            name="KUCHNIA_A",
            client_name="Klient Alfa",
            order_name="ORD-ALFA-01",
            wall_a_width_mm=3600.0,
        )
    )

    w = TabSciana(wall_store=wall_store)
    app.processEvents()

    wall_idx = w.cb_wall.findData("KUCHNIA_A")
    assert wall_idx >= 0
    assert w.cb_wall.itemText(wall_idx) == "KUCHNIA_A - Klient Alfa (ORD-ALFA-01)"
    assert "Sciana: KUCHNIA_A" in str(w.cb_wall.itemData(wall_idx, Qt.ItemDataRole.ToolTipRole) or "")
    assert "Klient: Klient Alfa" in str(w.cb_wall.itemData(wall_idx, Qt.ItemDataRole.ToolTipRole) or "")


def test_sciana_tab_preview_draws_module_parts_not_only_outer_block(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.core.module_parts_service import build_module_parts
    from src.domain.module_models import ModuleDef
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.storage.module_store_json import ModuleStoreJson
    from src.tabs.sciana.tab_sciana import TabSciana

    catalog = CatalogStoreJson()
    store = ModuleStoreJson()

    module = ModuleDef(
        name="FULL_PREVIEW_MOD",
        width_mm=800.0,
        depth_mm=500.0,
        height_mm=720.0,
        shelf_count=1,
        divider_count=1,
        visible_parts={"side_left", "side_right", "top", "bottom", "shelf", "divider", "front"},
        materials={"carcass": "PB18", "front": "MDF19", "back": "HDF2.5"},
    )
    module.parts = build_module_parts(module, catalog)
    store.save_new(module)

    w = TabSciana(module_store=store)
    assert _select_saved_module(w.tree_saved_modules, "FULL_PREVIEW_MOD")

    w.btn_add_saved.click()

    assert _scene_has_key(w.preview, "assembly_module__0") is True
    assert _scene_has_key(w.preview, "assembly_module__0__side_left") is True
    assert _scene_has_key(w.preview, "assembly_module__0__top") is True
    assert _scene_has_key(w.preview, "assembly_module__0__shelf_1") is True
    assert _scene_has_key(w.preview, "assembly_module__0__divider_1") is True
    assert _scene_has_key(w.preview, "assembly_module__0__front") is True
    module_item = _scene_item_by_key(w.preview, "assembly_module__0")
    shelf_item = _scene_item_by_key(w.preview, "assembly_module__0__shelf_1")
    divider_item = _scene_item_by_key(w.preview, "assembly_module__0__divider_1")
    front_item = _scene_item_by_key(w.preview, "assembly_module__0__front")
    assert module_item is not None
    assert shelf_item is not None
    assert divider_item is not None
    assert front_item is not None
    assert front_item.brush().style() != Qt.BrushStyle.NoBrush
    assert float(shelf_item.zValue()) > float(module_item.zValue())
    assert float(divider_item.zValue()) > float(module_item.zValue())


def test_sciana_tab_preview_draws_front_subdivision_for_double_doors_and_drawers(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.core.module_parts_service import build_module_parts
    from src.domain.module_models import ModuleDef
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.storage.module_store_json import ModuleStoreJson
    from src.tabs.sciana.tab_sciana import TabSciana

    store = ModuleStoreJson()
    catalog = CatalogStoreJson()

    door_module = ModuleDef(
        name="DOUBLE_DOOR_PREVIEW",
        width_mm=800.0,
        depth_mm=500.0,
        height_mm=720.0,
        visible_parts=set(["side_left", "side_right", "top", "bottom", "back", "front"]),
        facade_mode="doors",
    )
    door_module.parts = build_module_parts(door_module, catalog)
    store.save_new(door_module)

    drawer_module = ModuleDef(
        name="DRAWER_PREVIEW",
        width_mm=800.0,
        depth_mm=500.0,
        height_mm=720.0,
        visible_parts=set(["side_left", "side_right", "top", "bottom", "back", "front"]),
        facade_mode="drawers",
        drawer_count=3,
    )
    drawer_module.parts = build_module_parts(drawer_module, catalog)
    store.save_new(drawer_module)

    w = TabSciana(module_store=store)
    w.show()
    app.processEvents()

    assert _select_saved_module(w.tree_saved_modules, "DOUBLE_DOOR_PREVIEW")
    w.btn_add_saved.click()
    assert _scene_has_key(w.preview, "assembly_module__0__front_split_line") is True
    assert _scene_has_key(w.preview, "assembly_module__0__front_handle_1") is True
    assert _scene_has_key(w.preview, "assembly_module__0__front_handle_2") is True

    assert _select_saved_module(w.tree_saved_modules, "DRAWER_PREVIEW")
    w.btn_add_saved.click()
    assert _scene_has_key(w.preview, "assembly_module__1__front_drawer_split_1") is True
    assert _scene_has_key(w.preview, "assembly_module__1__front_drawer_split_2") is True


def test_sciana_tab_front_preview_without_linked_wall_stays_compact_and_shows_only_selected_title(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.core.module_parts_service import build_module_parts
    from src.domain.module_models import ModuleDef
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.storage.module_store_json import ModuleStoreJson
    from src.tabs.sciana.tab_sciana import TabSciana

    catalog = CatalogStoreJson()
    store = ModuleStoreJson()

    module_a = ModuleDef(name="READABLE_A", width_mm=700.0, depth_mm=500.0, height_mm=720.0)
    module_a.parts = build_module_parts(module_a, catalog)
    store.save_new(module_a)

    module_b = ModuleDef(name="READABLE_B", width_mm=600.0, depth_mm=500.0, height_mm=720.0)
    module_b.parts = build_module_parts(module_b, catalog)
    store.save_new(module_b)

    w = TabSciana(module_store=store)
    assert _select_saved_module(w.tree_saved_modules, "READABLE_A")
    w.btn_add_saved.click()
    assert _select_saved_module(w.tree_saved_modules, "READABLE_B")
    w.btn_add_saved.click()
    app.processEvents()

    assert _scene_has_key(w.preview, "assembly_wall_frame") is False
    assert _scene_has_key(w.preview, "assembly_module_title__1") is True
    assert _scene_has_key(w.preview, "assembly_module_title__0") is False


def test_sciana_tab_uses_separate_front_and_top_previews(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.sciana.tab_sciana import TabSciana

    w = TabSciana()

    assert hasattr(w, "center_views_splitter")
    assert w.center_views_splitter.count() == 2
    assert str(getattr(w.preview, "_view_mode", "")) == "front"
    assert str(getattr(w.preview_top, "_view_mode", "")) == "top"
    assert str(w.cb_active_view.currentData() or "") == "front"
    assert not w.front_box.isHidden()
    assert w.top_box.isHidden()
    assert int(w.preview.minimumHeight()) >= 360
    assert int(w.preview_top.minimumHeight()) >= 170
    assert hasattr(w, "lab_preview_context")
    assert hasattr(w, "lab_active_module_info")
    assert "Widok z przodu" in w.lab_preview_context.text()
    assert "Dodaj zapisany modul" in w.lab_active_module_info.text()


def test_sciana_tab_right_zone_uses_scroll_area_for_lower_blocks(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.sciana.tab_sciana import TabSciana

    w = TabSciana()
    w.resize(1400, 900)
    w.show()
    app.processEvents()

    assert hasattr(w, "right_scroll_area")
    assert w.right_scroll_area.widget() is not None
    assert w.right_scroll_area.widgetResizable() is True
    assert w.block_offset.parent() is w.right_scroll_area.widget()
    assert w.block_summary.parent() is w.right_scroll_area.widget()


def test_sciana_tab_preview_info_bar_tracks_selected_module(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.core.module_parts_service import build_module_parts
    from src.domain.module_models import ModuleDef
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.storage.module_store_json import ModuleStoreJson
    from src.tabs.sciana.tab_sciana import TabSciana

    catalog = CatalogStoreJson()
    store = ModuleStoreJson()

    module = ModuleDef(name="INFO_TEST", width_mm=700.0, depth_mm=500.0, height_mm=720.0)
    module.parts = build_module_parts(module, catalog)
    store.save_new(module)

    w = TabSciana(module_store=store)
    assert _select_saved_module(w.tree_saved_modules, "INFO_TEST")
    w.btn_add_saved.click()
    app.processEvents()

    assert "INFO_TEST" in w.lab_active_module_info.text()
    assert "700 x 720 x 500 mm" in w.lab_active_module_info.text()


def test_sciana_tab_top_preview_keeps_real_module_depth_scale(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.core.module_parts_service import build_module_parts
    from src.domain.module_models import ModuleDef
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.storage.module_store_json import ModuleStoreJson
    from src.tabs.sciana.tab_sciana import TabSciana

    catalog = CatalogStoreJson()
    store = ModuleStoreJson()

    module = ModuleDef(name="TOP_DEPTH_500", width_mm=800.0, depth_mm=500.0, height_mm=720.0)
    module.parts = build_module_parts(module, catalog)
    store.save_new(module)

    w = TabSciana(module_store=store)
    assert _select_saved_module(w.tree_saved_modules, "TOP_DEPTH_500")
    w.btn_add_saved.click()
    app.processEvents()

    top_rect = w.preview_top.top_item_scene_rect(0)
    assert top_rect is not None
    assert abs(float(top_rect.height()) - 500.0) < 0.1


def test_sciana_tab_saved_modules_tree_exports_drag_payload(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.core.module_parts_service import build_module_parts
    from src.domain.module_models import ModuleDef
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.storage.module_store_json import ModuleStoreJson
    from src.tabs.sciana.tab_sciana import SAVED_MODULE_MIME, TabSciana

    catalog = CatalogStoreJson()
    store = ModuleStoreJson()

    module = ModuleDef(name="DRAG_MOD", width_mm=700.0, depth_mm=500.0, height_mm=720.0)
    module.parts = build_module_parts(module, catalog)
    store.save_new(module)

    w = TabSciana(module_store=store)
    assert _select_saved_module(w.tree_saved_modules, "DRAG_MOD")

    item = w.tree_saved_modules.currentItem()
    assert item is not None

    mime = w.tree_saved_modules.mimeData([item])

    assert mime is not None
    assert mime.hasFormat(SAVED_MODULE_MIME)
    payload = json.loads(bytes(mime.data(SAVED_MODULE_MIME)).decode("utf-8"))
    assert payload["name"] == "DRAG_MOD"
    assert float(payload["width_mm"]) == 700.0
    assert float(payload["height_mm"]) == 720.0


def test_sciana_tab_can_drop_saved_module_into_preview_at_target_position(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.core.module_parts_service import build_module_parts
    from src.domain.module_models import ModuleDef
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.storage.module_store_json import ModuleStoreJson
    from src.tabs.sciana.tab_sciana import TabSciana

    catalog = CatalogStoreJson()
    store = ModuleStoreJson()

    module_a = ModuleDef(name="DROP_A", width_mm=800.0, depth_mm=500.0, height_mm=720.0)
    module_a.parts = build_module_parts(module_a, catalog)
    store.save_new(module_a)

    module_b = ModuleDef(name="DROP_B", width_mm=600.0, depth_mm=500.0, height_mm=720.0)
    module_b.parts = build_module_parts(module_b, catalog)
    store.save_new(module_b)

    w = TabSciana(module_store=store)
    assert _select_saved_module(w.tree_saved_modules, "DROP_A")
    w.btn_add_saved.click()

    assert [item.source_name for item in w._assembly.items] == ["DROP_A"]

    w.preview.sig_saved_module_dropped.emit("DROP_B", 0.0)

    assert [item.source_name for item in w._assembly.items] == ["DROP_B", "DROP_A"]
    assert len(w._resolved_items) == 2
    assert w.tbl_items.rowCount() == 2
    assert w._selected_index() == 0
    assert "Dodano modul \"DROP_B\" do kompletu." in w.lab_store_status.text()


def test_sciana_tab_preview_top_drag_changes_module_wall_and_length_offsets(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.core.module_parts_service import build_module_parts
    from src.domain.module_models import ModuleDef
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.storage.module_store_json import ModuleStoreJson
    from src.tabs.sciana.tab_sciana import TabSciana

    catalog = CatalogStoreJson()
    store = ModuleStoreJson()

    module_a = ModuleDef(name="PREVIEW_A", width_mm=700.0, depth_mm=500.0, height_mm=720.0)
    module_a.parts = build_module_parts(module_a, catalog)
    store.save_new(module_a)

    module_b = ModuleDef(name="PREVIEW_B", width_mm=600.0, depth_mm=500.0, height_mm=720.0)
    module_b.parts = build_module_parts(module_b, catalog)
    store.save_new(module_b)

    w = TabSciana(module_store=store)
    w.resize(1400, 900)
    w.show()
    app.processEvents()

    assert _select_saved_module(w.tree_saved_modules, "PREVIEW_A")
    w.btn_add_saved.click()
    assert _select_saved_module(w.tree_saved_modules, "PREVIEW_B")
    w.btn_add_saved.click()
    w.sp_depth.setValue(1000.0)
    app.processEvents()

    first_rect = w.preview_top.top_item_scene_rect(0)
    second_rect = w.preview_top.top_item_scene_rect(1)
    assert first_rect is not None
    assert second_rect is not None

    second_center = w.preview_top.mapFromScene(second_rect.center())
    release_scene = QPointF(float(second_rect.center().x()) - 140.0, float(second_rect.center().y()) + 80.0)
    release_point = w.preview_top.mapFromScene(release_scene)

    QTest.mouseClick(
        w.preview_top.viewport(),
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        second_center,
    )
    app.processEvents()

    assert w._selected_index() == 1

    QTest.mousePress(
        w.preview_top.viewport(),
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        second_center,
    )
    QTest.mouseMove(w.preview_top.viewport(), release_point)
    QTest.mouseRelease(
        w.preview_top.viewport(),
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        release_point,
    )
    app.processEvents()

    assert w._selected_index() == 1
    assert float(getattr(w._assembly.items[1], "offset_mm", 0.0)) < 700.0
    assert float(getattr(w._assembly.items[1], "wall_depth_offset_mm", 0.0)) > 0.0
    moved_rect = w.preview_top.top_item_scene_rect(1)
    assert moved_rect is not None
    assert float(moved_rect.top()) > float(second_rect.top())


def test_sciana_tab_preview_front_drag_changes_module_offset(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.core.module_parts_service import build_module_parts
    from src.domain.module_models import ModuleDef
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.storage.module_store_json import ModuleStoreJson
    from src.tabs.sciana.tab_sciana import TabSciana

    catalog = CatalogStoreJson()
    store = ModuleStoreJson()

    module_a = ModuleDef(name="OFFSET_A", width_mm=700.0, depth_mm=500.0, height_mm=720.0)
    module_a.parts = build_module_parts(module_a, catalog)
    store.save_new(module_a)

    module_b = ModuleDef(name="OFFSET_B", width_mm=600.0, depth_mm=500.0, height_mm=720.0)
    module_b.parts = build_module_parts(module_b, catalog)
    store.save_new(module_b)

    w = TabSciana(module_store=store)
    w.resize(1400, 900)
    w.show()
    app.processEvents()

    assert _select_saved_module(w.tree_saved_modules, "OFFSET_A")
    w.btn_add_saved.click()
    assert _select_saved_module(w.tree_saved_modules, "OFFSET_B")
    w.btn_add_saved.click()
    app.processEvents()

    second_rect = w.preview.item_scene_rect(1)
    assert second_rect is not None

    press_point = w.preview.mapFromScene(second_rect.center())
    release_scene = QPointF(second_rect.center().x() + 90.0, second_rect.center().y())
    release_point = w.preview.mapFromScene(release_scene)

    QTest.mousePress(
        w.preview.viewport(),
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        press_point,
    )
    QTest.mouseMove(w.preview.viewport(), release_point)
    QTest.mouseRelease(
        w.preview.viewport(),
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        release_point,
    )
    app.processEvents()

    assert float(getattr(w._assembly.items[1], "offset_mm", 0.0)) > 0.0
    assert float(w._resolved_items[1].x_mm) > float(w._resolved_items[0].x_mm + w._resolved_items[0].width_mm + w._assembly.gap_mm)
    assert str(w.cb_selected_x_ref.currentData() or "") == "wall_left"
    assert "Lewa krawedz sciany" in w.lab_offset_ref.text()


def test_sciana_tab_preview_front_drag_keeps_committed_offset_until_release(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.core.module_parts_service import build_module_parts
    from src.domain.module_models import ModuleDef
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.storage.module_store_json import ModuleStoreJson
    from src.tabs.sciana.tab_sciana import TabSciana

    catalog = CatalogStoreJson()
    store = ModuleStoreJson()

    module_a = ModuleDef(name="OFFSET_HOLD_A", width_mm=700.0, depth_mm=500.0, height_mm=720.0)
    module_a.parts = build_module_parts(module_a, catalog)
    store.save_new(module_a)

    module_b = ModuleDef(name="OFFSET_HOLD_B", width_mm=600.0, depth_mm=500.0, height_mm=720.0)
    module_b.parts = build_module_parts(module_b, catalog)
    store.save_new(module_b)

    w = TabSciana(module_store=store)
    w.resize(1400, 900)
    w.show()
    app.processEvents()

    assert _select_saved_module(w.tree_saved_modules, "OFFSET_HOLD_A")
    w.btn_add_saved.click()
    assert _select_saved_module(w.tree_saved_modules, "OFFSET_HOLD_B")
    w.btn_add_saved.click()
    app.processEvents()

    second_rect = w.preview.item_scene_rect(1)
    assert second_rect is not None
    initial_offset = float(getattr(w._assembly.items[1], "offset_mm", 0.0))

    press_point = w.preview.mapFromScene(second_rect.center())
    move_scene = QPointF(second_rect.center().x() + 120.0, second_rect.center().y())
    move_point = w.preview.mapFromScene(move_scene)

    QTest.mousePress(
        w.preview.viewport(),
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        press_point,
    )
    QTest.mouseMove(w.preview.viewport(), move_point)
    app.processEvents()

    ghost_rect = w.preview.ghost_scene_rect()
    assert ghost_rect is not None
    assert abs(float(getattr(w._assembly.items[1], "offset_mm", 0.0)) - initial_offset) < 0.1

    QTest.mouseRelease(
        w.preview.viewport(),
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        move_point,
    )
    app.processEvents()

    assert float(getattr(w._assembly.items[1], "offset_mm", 0.0)) > initial_offset


def test_sciana_tab_preview_front_drag_snap_prefers_previous_neighbor_attachment(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.core.module_parts_service import build_module_parts
    from src.domain.module_models import ModuleDef
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.storage.module_store_json import ModuleStoreJson
    from src.tabs.sciana.tab_sciana import TabSciana

    catalog = CatalogStoreJson()
    store = ModuleStoreJson()

    module_a = ModuleDef(name="SNAP_ATTACH_A", width_mm=700.0, depth_mm=500.0, height_mm=720.0)
    module_a.parts = build_module_parts(module_a, catalog)
    store.save_new(module_a)

    module_b = ModuleDef(name="SNAP_ATTACH_B", width_mm=600.0, depth_mm=500.0, height_mm=720.0)
    module_b.parts = build_module_parts(module_b, catalog)
    store.save_new(module_b)

    w = TabSciana(module_store=store)
    w.resize(1400, 900)
    w.show()
    app.processEvents()

    assert _select_saved_module(w.tree_saved_modules, "SNAP_ATTACH_A")
    w.btn_add_saved.click()
    assert _select_saved_module(w.tree_saved_modules, "SNAP_ATTACH_B")
    w.btn_add_saved.click()
    app.processEvents()

    w.sp_selected_offset.setValue(90.0)
    app.processEvents()

    second_rect = w.preview.item_scene_rect(1)
    assert second_rect is not None

    attach_left = float(w._resolved_items[0].x_mm + w._resolved_items[0].width_mm)
    w.preview._drag_left_offset = float(second_rect.center().x() - second_rect.left())
    scene_x = attach_left + float(w.preview._drag_left_offset) + 6.0

    snapped_offset, snapped_left = w.preview._snapped_offset_for_scene_x(1, scene_x)

    assert abs(snapped_offset - attach_left) < 0.1
    assert abs(snapped_left - attach_left) < 0.1


def test_sciana_tab_preview_front_drag_commits_using_real_drag_offsets(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.core.module_parts_service import build_module_parts
    from src.domain.module_models import ModuleDef
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.storage.module_store_json import ModuleStoreJson
    from src.tabs.sciana.tab_sciana import TabSciana

    catalog = CatalogStoreJson()
    store = ModuleStoreJson()

    module_a = ModuleDef(name="RELEASE_ATTACH_A", width_mm=700.0, depth_mm=500.0, height_mm=720.0)
    module_a.parts = build_module_parts(module_a, catalog)
    store.save_new(module_a)

    module_b = ModuleDef(name="RELEASE_ATTACH_B", width_mm=600.0, depth_mm=500.0, height_mm=720.0)
    module_b.parts = build_module_parts(module_b, catalog)
    store.save_new(module_b)

    w = TabSciana(module_store=store)
    w.resize(1400, 900)
    w.show()
    app.processEvents()

    assert _select_saved_module(w.tree_saved_modules, "RELEASE_ATTACH_A")
    w.btn_add_saved.click()
    assert _select_saved_module(w.tree_saved_modules, "RELEASE_ATTACH_B")
    w.btn_add_saved.click()
    app.processEvents()

    second_rect = w.preview.item_scene_rect(1)
    assert second_rect is not None

    attach_left = float(w._resolved_items[0].x_mm + w._resolved_items[0].width_mm)
    press_point = w.preview.mapFromScene(second_rect.center())
    drag_left_offset = float(second_rect.center().x() - second_rect.left())
    release_scene = QPointF(attach_left + drag_left_offset + 4.0, second_rect.center().y())
    release_point = w.preview.mapFromScene(release_scene)

    QTest.mousePress(
        w.preview.viewport(),
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        press_point,
    )
    QTest.mouseMove(w.preview.viewport(), release_point)
    QTest.mouseRelease(
        w.preview.viewport(),
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        release_point,
    )
    app.processEvents()

    assert abs(float(w._resolved_items[1].x_mm) - attach_left) < 0.1
    assert abs(float(getattr(w._assembly.items[1], "offset_mm", 0.0)) - attach_left) < 0.1


def test_sciana_tab_preview_front_drag_has_stable_snap_targets_for_following_module(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.core.module_parts_service import build_module_parts
    from src.domain.module_models import ModuleDef
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.storage.module_store_json import ModuleStoreJson
    from src.tabs.sciana.tab_sciana import TabSciana

    catalog = CatalogStoreJson()
    store = ModuleStoreJson()

    module_a = ModuleDef(name="SNAP_TARGET_A", width_mm=700.0, depth_mm=500.0, height_mm=720.0)
    module_a.parts = build_module_parts(module_a, catalog)
    store.save_new(module_a)

    module_b = ModuleDef(name="SNAP_TARGET_B", width_mm=600.0, depth_mm=500.0, height_mm=720.0)
    module_b.parts = build_module_parts(module_b, catalog)
    store.save_new(module_b)

    w = TabSciana(module_store=store)
    assert _select_saved_module(w.tree_saved_modules, "SNAP_TARGET_A")
    w.btn_add_saved.click()
    assert _select_saved_module(w.tree_saved_modules, "SNAP_TARGET_B")
    w.btn_add_saved.click()
    app.processEvents()

    second_rect = w.preview.item_scene_rect(1)
    assert second_rect is not None

    attach_left = float(w._resolved_items[0].x_mm + w._resolved_items[0].width_mm)
    w.preview._drag_left_offset = float(second_rect.center().x() - second_rect.left())

    gap_scene_x = float(w.preview._drag_left_offset) + 6.0
    snapped_gap_offset, snapped_gap_left = w.preview._snapped_offset_for_scene_x(1, gap_scene_x)
    assert abs(snapped_gap_offset) < 0.1
    assert abs(snapped_gap_left) < 0.1

    attach_scene_x = attach_left + float(w.preview._drag_left_offset) + 6.0
    snapped_attach_offset, snapped_attach_left = w.preview._snapped_offset_for_scene_x(1, attach_scene_x)
    assert abs(snapped_attach_offset - attach_left) < 0.1
    assert abs(snapped_attach_left - attach_left) < 0.1


def test_sciana_tab_same_row_snap_prefers_side_attachment_not_left_edge_alignment(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.core.module_parts_service import build_module_parts
    from src.domain.module_models import ModuleDef
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.storage.module_store_json import ModuleStoreJson
    from src.tabs.sciana.tab_sciana import TabSciana

    catalog = CatalogStoreJson()
    store = ModuleStoreJson()

    module_a = ModuleDef(name="ROW_ALIGN_A", width_mm=700.0, depth_mm=500.0, height_mm=720.0)
    module_a.parts = build_module_parts(module_a, catalog)
    store.save_new(module_a)

    module_b = ModuleDef(name="ROW_ALIGN_B", width_mm=600.0, depth_mm=500.0, height_mm=720.0)
    module_b.parts = build_module_parts(module_b, catalog)
    store.save_new(module_b)

    w = TabSciana(module_store=store)
    assert _select_saved_module(w.tree_saved_modules, "ROW_ALIGN_A")
    w.btn_add_saved.click()
    assert _select_saved_module(w.tree_saved_modules, "ROW_ALIGN_B")
    w.btn_add_saved.click()
    app.processEvents()

    w._assembly.items[0].offset_mm = 200.0
    w._rebuild_assembly(select_index=1)
    app.processEvents()

    candidates = list(w.preview._snap_offset_candidate_values(1))
    other_left = float(w._resolved_items[0].x_mm)
    other_right = float(w._resolved_items[0].x_mm + w._resolved_items[0].width_mm)

    assert any(abs(candidate - other_right) < 0.1 for candidate in candidates)
    assert not any(abs(candidate - other_left) < 0.1 for candidate in candidates)


def test_sciana_tab_preview_front_drag_can_snap_module_under_another_module(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.core.module_parts_service import build_module_parts
    from src.domain.module_models import ModuleDef
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.storage.module_store_json import ModuleStoreJson
    from src.tabs.sciana.tab_sciana import TabSciana

    catalog = CatalogStoreJson()
    store = ModuleStoreJson()

    module_upper = ModuleDef(
        name="SNAP_VERTICAL_UPPER",
        width_mm=700.0,
        depth_mm=320.0,
        height_mm=720.0,
        module_type="hanging",
        cabinet_kind="upper",
    )
    module_upper.parts = build_module_parts(module_upper, catalog)
    store.save_new(module_upper)

    module_lower = ModuleDef(
        name="SNAP_VERTICAL_LOWER",
        width_mm=700.0,
        depth_mm=560.0,
        height_mm=720.0,
        module_type="legs_plinth",
        cabinet_kind="lower",
    )
    module_lower.parts = build_module_parts(module_lower, catalog)
    store.save_new(module_lower)

    w = TabSciana(module_store=store)
    assert _select_saved_module(w.tree_saved_modules, "SNAP_VERTICAL_UPPER")
    w.btn_add_saved.click()
    assert _select_saved_module(w.tree_saved_modules, "SNAP_VERTICAL_LOWER")
    w.btn_add_saved.click()
    app.processEvents()

    w._assembly.items[1].offset_mm = float(w._resolved_items[0].x_mm)
    w._rebuild_assembly(select_index=1)
    app.processEvents()

    upper_rect = w.preview.item_scene_rect(0)
    lower_rect = w.preview.item_scene_rect(1)
    assert upper_rect is not None
    assert lower_rect is not None

    w.preview._drag_top_offset = float(lower_rect.center().y() - lower_rect.top())
    target_top = float(upper_rect.bottom())
    scene_y = target_top + float(w.preview._drag_top_offset) + 6.0

    snapped_y, snapped_top = w.preview._snapped_y_for_scene_y(
        1,
        scene_y,
        current_left_x=float(upper_rect.left()),
        drag_top_offset=w.preview._drag_top_offset,
    )

    assert abs(snapped_y - target_top) < 0.1
    assert abs(snapped_top - target_top) < 0.1


def test_sciana_tab_stacked_modules_use_vertical_snap_without_overlap_alignment_targets(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.core.module_parts_service import build_module_parts
    from src.domain.module_models import ModuleDef
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.storage.module_store_json import ModuleStoreJson
    from src.tabs.sciana.tab_sciana import TabSciana

    catalog = CatalogStoreJson()
    store = ModuleStoreJson()

    module_upper = ModuleDef(
        name="STACK_TARGET_UPPER",
        width_mm=700.0,
        depth_mm=320.0,
        height_mm=720.0,
        module_type="hanging",
        cabinet_kind="upper",
    )
    module_upper.parts = build_module_parts(module_upper, catalog)
    store.save_new(module_upper)

    module_lower = ModuleDef(
        name="STACK_TARGET_LOWER",
        width_mm=700.0,
        depth_mm=560.0,
        height_mm=600.0,
        module_type="legs_plinth",
        cabinet_kind="lower",
    )
    module_lower.parts = build_module_parts(module_lower, catalog)
    store.save_new(module_lower)

    w = TabSciana(module_store=store)
    assert _select_saved_module(w.tree_saved_modules, "STACK_TARGET_UPPER")
    w.btn_add_saved.click()
    assert _select_saved_module(w.tree_saved_modules, "STACK_TARGET_LOWER")
    w.btn_add_saved.click()
    app.processEvents()

    w._assembly.items[1].offset_mm = float(w._resolved_items[0].x_mm)
    w._rebuild_assembly(select_index=1)
    app.processEvents()

    upper = w._resolved_items[0]
    lower = w._resolved_items[1]
    candidates = list(w.preview._snap_y_candidate_values(1, current_left_x=float(upper.x_mm)))

    below_target = float(upper.y_mm + upper.height_mm)
    above_target = float(upper.y_mm - lower.height_mm)
    overlap_top_target = float(upper.y_mm)
    overlap_bottom_target = float(upper.y_mm + upper.height_mm - lower.height_mm)

    assert any(abs(candidate - below_target) < 0.1 for candidate in candidates)
    assert any(abs(candidate - above_target) < 0.1 for candidate in candidates)
    assert not any(abs(candidate - overlap_top_target) < 0.1 for candidate in candidates)
    assert not any(abs(candidate - overlap_bottom_target) < 0.1 for candidate in candidates)


def test_sciana_tab_material_override_changes_resolved_module_materials(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.core.module_parts_service import build_module_parts
    from src.domain.module_models import ModuleDef
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.storage.module_store_json import ModuleStoreJson
    from src.tabs.sciana.tab_sciana import TabSciana

    catalog = CatalogStoreJson()
    store = ModuleStoreJson()

    module = ModuleDef(
        name="MAT_OVERRIDE_A",
        width_mm=800.0,
        depth_mm=500.0,
        height_mm=720.0,
        shelf_count=1,
        visible_parts={"side_left", "side_right", "top", "bottom", "shelf", "front"},
        materials={"carcass": "PB18", "front": "MDF19", "back": "HDF2.5"},
    )
    module.parts = build_module_parts(module, catalog)
    store.save_new(module)

    w = TabSciana(module_store=store)
    assert _select_saved_module(w.tree_saved_modules, "MAT_OVERRIDE_A")
    w.btn_add_saved.click()
    app.processEvents()

    before_total = float(w._resolved_items[0].cost_breakdown.material_total_pln)

    idx = w.cb_material_front.findData("PB18")
    assert idx >= 0
    w.cb_material_front.setCurrentIndex(idx)
    app.processEvents()

    assert str(w._assembly.material_overrides.get("front", "")) == "PB18"
    assert str(w._resolved_items[0].module.materials.get("front", "")) == "PB18"
    assert float(w._resolved_items[0].cost_breakdown.material_total_pln) != before_total


def test_sciana_tab_selected_offset_spinbox_updates_module_offset(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.core.module_parts_service import build_module_parts
    from src.domain.module_models import ModuleDef
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.storage.module_store_json import ModuleStoreJson
    from src.tabs.sciana.tab_sciana import TabSciana

    catalog = CatalogStoreJson()
    store = ModuleStoreJson()

    module_a = ModuleDef(name="SPIN_A", width_mm=700.0, depth_mm=500.0, height_mm=720.0)
    module_a.parts = build_module_parts(module_a, catalog)
    store.save_new(module_a)

    module_b = ModuleDef(name="SPIN_B", width_mm=600.0, depth_mm=500.0, height_mm=720.0)
    module_b.parts = build_module_parts(module_b, catalog)
    store.save_new(module_b)

    w = TabSciana(module_store=store)
    assert _select_saved_module(w.tree_saved_modules, "SPIN_A")
    w.btn_add_saved.click()
    assert _select_saved_module(w.tree_saved_modules, "SPIN_B")
    w.btn_add_saved.click()
    app.processEvents()

    w.tbl_items.selectRow(1)
    app.processEvents()
    w.sp_selected_offset.setValue(80.0)
    app.processEvents()

    assert abs(float(getattr(w._assembly.items[1], "offset_mm", 0.0)) - 80.0) < 0.1
    assert abs(float(w._resolved_items[1].x_mm) - 80.0) < 0.1
    assert str(w.cb_selected_x_ref.currentData() or "") == "wall_left"


def test_sciana_tab_next_module_uses_wall_left_base_and_starts_after_previous(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.core.module_parts_service import build_module_parts
    from src.domain.module_models import ModuleDef
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.storage.module_store_json import ModuleStoreJson
    from src.tabs.sciana.tab_sciana import TabSciana

    catalog = CatalogStoreJson()
    store = ModuleStoreJson()

    module_a = ModuleDef(name="ATTACH_A", width_mm=700.0, depth_mm=500.0, height_mm=720.0)
    module_a.parts = build_module_parts(module_a, catalog)
    store.save_new(module_a)

    module_b = ModuleDef(name="ATTACH_B", width_mm=600.0, depth_mm=500.0, height_mm=720.0)
    module_b.parts = build_module_parts(module_b, catalog)
    store.save_new(module_b)

    w = TabSciana(module_store=store)
    assert _select_saved_module(w.tree_saved_modules, "ATTACH_A")
    w.btn_add_saved.click()
    assert _select_saved_module(w.tree_saved_modules, "ATTACH_B")
    w.btn_add_saved.click()
    app.processEvents()

    assert str(getattr(w._assembly.items[1], "offset_ref_mode", "")) == "wall_left"
    assert abs(float(getattr(w._assembly.items[1], "offset_mm", 0.0)) - 700.0) < 0.1
    assert abs(float(w._resolved_items[1].x_mm) - float(w._resolved_items[0].x_mm + w._resolved_items[0].width_mm)) < 0.1


def test_sciana_tab_can_switch_horizontal_base_from_left_wall_to_previous_module(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.core.module_parts_service import build_module_parts
    from src.domain.module_models import ModuleDef
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.storage.module_store_json import ModuleStoreJson
    from src.tabs.sciana.tab_sciana import TabSciana

    catalog = CatalogStoreJson()
    store = ModuleStoreJson()

    module_a = ModuleDef(name="REF_A", width_mm=700.0, depth_mm=500.0, height_mm=720.0)
    module_a.parts = build_module_parts(module_a, catalog)
    store.save_new(module_a)

    module_b = ModuleDef(name="REF_B", width_mm=600.0, depth_mm=500.0, height_mm=720.0)
    module_b.parts = build_module_parts(module_b, catalog)
    store.save_new(module_b)

    w = TabSciana(module_store=store)
    assert _select_saved_module(w.tree_saved_modules, "REF_A")
    w.btn_add_saved.click()
    assert _select_saved_module(w.tree_saved_modules, "REF_B")
    w.btn_add_saved.click()
    app.processEvents()

    w.tbl_items.selectRow(1)
    app.processEvents()

    before_x = float(w._resolved_items[1].x_mm)
    idx = w.cb_selected_x_ref.findData("previous_module")
    assert idx >= 0
    w.cb_selected_x_ref.setCurrentIndex(idx)
    app.processEvents()

    assert str(getattr(w._assembly.items[1], "offset_ref_mode", "")) == "previous_module"
    assert abs(float(getattr(w._assembly.items[1], "offset_mm", 0.0))) < 0.1
    assert abs(float(w._resolved_items[1].x_mm) - before_x) < 0.1
    assert "Poprzedni modul:" in w.lab_offset_ref.text()


def test_sciana_tab_negative_offset_shows_collision_alert(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.core.module_parts_service import build_module_parts
    from src.domain.module_models import ModuleDef
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.storage.module_store_json import ModuleStoreJson
    from src.tabs.sciana.tab_sciana import TabSciana

    catalog = CatalogStoreJson()
    store = ModuleStoreJson()

    module_a = ModuleDef(name="COLLIDE_A", width_mm=700.0, depth_mm=500.0, height_mm=720.0)
    module_a.parts = build_module_parts(module_a, catalog)
    store.save_new(module_a)

    module_b = ModuleDef(name="COLLIDE_B", width_mm=600.0, depth_mm=500.0, height_mm=720.0)
    module_b.parts = build_module_parts(module_b, catalog)
    store.save_new(module_b)

    w = TabSciana(module_store=store)
    assert _select_saved_module(w.tree_saved_modules, "COLLIDE_A")
    w.btn_add_saved.click()
    assert _select_saved_module(w.tree_saved_modules, "COLLIDE_B")
    w.btn_add_saved.click()
    app.processEvents()

    w._assembly.items[1].offset_mm = -100.0
    w._rebuild_assembly(select_index=1)
    app.processEvents()

    assert bool(getattr(w._resolved_items[0], "has_collision", False)) is True
    assert bool(getattr(w._resolved_items[1], "has_collision", False)) is True
    assert "Kolizja:" in w.lab_layout_alert.text()
    assert _scene_has_key(w.preview, "assembly_warning__collision__0") is True or _scene_has_key(w.preview, "assembly_warning__collision__1") is True


def test_sciana_tab_preview_front_drag_changes_module_vertical_position(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.core.module_parts_service import build_module_parts
    from src.domain.module_models import ModuleDef
    from src.domain.wall_models import WallLayoutDef
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.storage.module_store_json import ModuleStoreJson
    from src.storage.wall_store_json import WallStoreJson
    from src.tabs.sciana.tab_sciana import TabSciana

    catalog = CatalogStoreJson()
    store = ModuleStoreJson()
    wall_store = WallStoreJson(path=tmp_path / "walls.json")

    wall_store.save_new(
        WallLayoutDef(
            name="VERTICAL_WALL",
            wall_a_width_mm=4000.0,
            room_height_mm=2600.0,
            base_depth_mm=600.0,
            base_plinth_mm=100.0,
        )
    )

    module = ModuleDef(name="VERTICAL_DRAG", width_mm=700.0, depth_mm=500.0, height_mm=720.0, module_type="legs_plinth", cabinet_kind="lower")
    module.parts = build_module_parts(module, catalog)
    store.save_new(module)

    w = TabSciana(module_store=store, wall_store=wall_store)
    w.resize(1400, 900)
    w.show()
    w.start_new_assembly_from_wall_context({"wall_name": "VERTICAL_WALL", "width_mm": 4000.0, "height_mm": 2600.0, "depth_mm": 600.0})
    app.processEvents()

    assert _select_saved_module(w.tree_saved_modules, "VERTICAL_DRAG")
    w.btn_add_saved.click()
    app.processEvents()

    rect = w.preview.item_scene_rect(0)
    assert rect is not None

    press_point = w.preview.mapFromScene(rect.center())
    release_scene = QPointF(rect.center().x(), rect.center().y() - 120.0)
    release_point = w.preview.mapFromScene(release_scene)

    QTest.mousePress(
        w.preview.viewport(),
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        press_point,
    )
    QTest.mouseMove(w.preview.viewport(), release_point)
    QTest.mouseRelease(
        w.preview.viewport(),
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        release_point,
    )
    app.processEvents()

    assert abs(float(getattr(w._assembly.items[0], "position_y_mm", 0.0)) - 1780.0) > 0.1
    assert abs(float(w._resolved_items[0].y_mm) - float(getattr(w._assembly.items[0], "position_y_mm", 0.0))) < 0.1


def test_sciana_tab_selected_y_spinbox_updates_module_vertical_position(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.core.module_parts_service import build_module_parts
    from src.domain.module_models import ModuleDef
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.storage.module_store_json import ModuleStoreJson
    from src.tabs.sciana.tab_sciana import TabSciana

    catalog = CatalogStoreJson()
    store = ModuleStoreJson()

    module = ModuleDef(name="SPIN_Y", width_mm=700.0, depth_mm=500.0, height_mm=720.0)
    module.parts = build_module_parts(module, catalog)
    store.save_new(module)

    w = TabSciana(module_store=store)
    assert _select_saved_module(w.tree_saved_modules, "SPIN_Y")
    w.btn_add_saved.click()
    app.processEvents()

    w.tbl_items.selectRow(0)
    app.processEvents()
    w.sp_selected_y.setValue(140.0)
    app.processEvents()

    assert abs(float(getattr(w._assembly.items[0], "position_y_mm", 0.0)) - 140.0) < 0.1
    assert abs(float(w._resolved_items[0].y_mm) - 140.0) < 0.1


def test_sciana_tab_selected_bottom_offset_spinbox_updates_module_vertical_position(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.core.module_parts_service import build_module_parts
    from src.domain.module_models import ModuleDef
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.storage.module_store_json import ModuleStoreJson
    from src.tabs.sciana.tab_sciana import TabSciana

    catalog = CatalogStoreJson()
    store = ModuleStoreJson()

    module = ModuleDef(name="SPIN_Y_BOTTOM", width_mm=700.0, depth_mm=500.0, height_mm=720.0)
    module.parts = build_module_parts(module, catalog)
    store.save_new(module)

    w = TabSciana(module_store=store)
    assert _select_saved_module(w.tree_saved_modules, "SPIN_Y_BOTTOM")
    w.btn_add_saved.click()
    app.processEvents()

    w.tbl_items.selectRow(0)
    app.processEvents()

    idx = w.cb_selected_y_ref.findData("bottom")
    assert idx >= 0
    w.cb_selected_y_ref.setCurrentIndex(idx)
    app.processEvents()

    w.sp_selected_y.setValue(100.0)
    app.processEvents()

    expected_top = float(w.preview._max_y_for_index(0)) - 100.0
    assert str(getattr(w.preview, "_vertical_reference_mode", "")) == "bottom"
    assert abs(float(getattr(w._assembly.items[0], "position_y_mm", 0.0)) - expected_top) < 0.1
    assert abs(float(w._resolved_items[0].y_mm) - expected_top) < 0.1
    assert w.offset_form.labelForField(w.sp_selected_y).text() == "Od dolu"


def test_sciana_tab_top_view_uses_wall_offset_editor(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.core.module_parts_service import build_module_parts
    from src.domain.module_models import ModuleDef
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.storage.module_store_json import ModuleStoreJson
    from src.tabs.sciana.tab_sciana import TabSciana

    catalog = CatalogStoreJson()
    store = ModuleStoreJson()

    module = ModuleDef(name="TOP_EDITOR", width_mm=700.0, depth_mm=500.0, height_mm=720.0)
    module.parts = build_module_parts(module, catalog)
    store.save_new(module)

    w = TabSciana(module_store=store)
    w.resize(1400, 900)
    w.show()
    app.processEvents()

    assert _select_saved_module(w.tree_saved_modules, "TOP_EDITOR")
    w.btn_add_saved.click()
    w.sp_depth.setValue(1000.0)
    app.processEvents()

    w.tbl_items.selectRow(0)
    w._set_active_view_mode("top")
    app.processEvents()

    assert w.offset_form.labelForField(w.sp_selected_y).text() == "Od sciany"
    assert w.offset_form.labelForField(w.sp_selected_offset).text() == "Po dlugosci"
    assert w.cb_selected_y_ref.isHidden() is True


def test_sciana_tab_top_view_wall_offset_spinbox_updates_module_depth_position(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.core.module_parts_service import build_module_parts
    from src.domain.module_models import ModuleDef
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.storage.module_store_json import ModuleStoreJson
    from src.tabs.sciana.tab_sciana import TabSciana

    catalog = CatalogStoreJson()
    store = ModuleStoreJson()

    module = ModuleDef(name="TOP_OFFSET", width_mm=700.0, depth_mm=500.0, height_mm=720.0)
    module.parts = build_module_parts(module, catalog)
    store.save_new(module)

    w = TabSciana(module_store=store)
    w.resize(1400, 900)
    w.show()
    app.processEvents()

    assert _select_saved_module(w.tree_saved_modules, "TOP_OFFSET")
    w.btn_add_saved.click()
    w.sp_depth.setValue(1000.0)
    app.processEvents()

    w.tbl_items.selectRow(0)
    w._set_active_view_mode("top")
    app.processEvents()

    w.sp_selected_y.setValue(120.0)
    app.processEvents()

    top_rect = w.preview_top.top_item_scene_rect(0)
    assert top_rect is not None
    assert abs(float(getattr(w._assembly.items[0], "wall_depth_offset_mm", 0.0)) - 120.0) < 0.1
    assert abs(float(top_rect.top()) - (w.preview_top._top_view_base_y() + 120.0)) < 0.1


def test_sciana_tab_selected_module_does_not_show_inline_offset_editor_when_idle(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.core.module_parts_service import build_module_parts
    from src.domain.module_models import ModuleDef
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.storage.module_store_json import ModuleStoreJson
    from src.tabs.sciana.tab_sciana import TabSciana

    catalog = CatalogStoreJson()
    store = ModuleStoreJson()

    module = ModuleDef(name="INLINE_OFFSET", width_mm=700.0, depth_mm=500.0, height_mm=720.0)
    module.parts = build_module_parts(module, catalog)
    store.save_new(module)

    w = TabSciana(module_store=store)
    w.resize(1400, 900)
    w.show()
    app.processEvents()

    assert _select_saved_module(w.tree_saved_modules, "INLINE_OFFSET")
    w.btn_add_saved.click()
    app.processEvents()

    assert _scene_has_key(w.preview, "assembly_offset_editor__0") is False
    assert _scene_has_key(w.preview, "assembly_offset_ref__0") is False


def test_sciana_tab_shows_inline_offset_editor_only_during_front_drag(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.core.module_parts_service import build_module_parts
    from src.domain.module_models import ModuleDef
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.storage.module_store_json import ModuleStoreJson
    from src.tabs.sciana.tab_sciana import TabSciana

    catalog = CatalogStoreJson()
    store = ModuleStoreJson()

    module = ModuleDef(name="INLINE_DRAG", width_mm=700.0, depth_mm=500.0, height_mm=720.0)
    module.parts = build_module_parts(module, catalog)
    store.save_new(module)

    w = TabSciana(module_store=store)
    w.resize(1400, 900)
    w.show()
    app.processEvents()

    assert _select_saved_module(w.tree_saved_modules, "INLINE_DRAG")
    w.btn_add_saved.click()
    app.processEvents()

    w.preview._drag_index = 0
    w.preview._drag_mode = "position"
    w.preview._drag_started = True
    w.preview._front_drag_offset_mm = 0.0
    w.preview._front_drag_y_mm = 0.0
    w._refresh_preview_only()
    app.processEvents()

    assert _scene_has_key(w.preview, "assembly_offset_editor__0") is True
    assert _scene_has_key(w.preview, "assembly_offset_ref__0") is True


def test_sciana_tab_preview_shows_ghost_for_drag_and_reorder(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.core.module_parts_service import build_module_parts
    from src.domain.module_models import ModuleDef
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.storage.module_store_json import ModuleStoreJson
    from src.tabs.sciana.tab_sciana import TabSciana

    catalog = CatalogStoreJson()
    store = ModuleStoreJson()

    module_a = ModuleDef(name="GHOST_A", width_mm=800.0, depth_mm=500.0, height_mm=720.0)
    module_a.parts = build_module_parts(module_a, catalog)
    store.save_new(module_a)

    module_b = ModuleDef(name="GHOST_B", width_mm=600.0, depth_mm=500.0, height_mm=720.0)
    module_b.parts = build_module_parts(module_b, catalog)
    store.save_new(module_b)

    w = TabSciana(module_store=store)
    assert _select_saved_module(w.tree_saved_modules, "GHOST_A")
    w.btn_add_saved.click()

    item = w.tree_saved_modules.currentItem()
    assert item is not None
    payload = json.loads(bytes(w.tree_saved_modules.mimeData([item]).data("application/x-tech-modul-saved-module")).decode("utf-8"))
    w.preview._set_saved_module_drag_preview(payload, 0.0)

    ghost_rect = w.preview.ghost_scene_rect()
    assert ghost_rect is not None
    assert abs(ghost_rect.width() - 800.0) < 0.1
    assert abs(ghost_rect.height() - 720.0) < 0.1
    assert w.preview.drop_indicator_x() is not None

    assert _select_saved_module(w.tree_saved_modules, "GHOST_B")
    w.btn_add_saved.click()
    w.preview_top._set_reorder_drag_preview(1, 0.0)

    ghost_rect_2 = w.preview_top.ghost_scene_rect()
    assert ghost_rect_2 is not None
    assert abs(ghost_rect_2.width() - 600.0) < 0.1
    assert ghost_rect_2.left() <= 0.1


def test_sciana_tab_applies_wall_inheritance_and_profile(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.core.module_parts_service import build_module_parts
    from src.domain.module_models import ModuleDef
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.storage.module_store_json import ModuleStoreJson
    from src.tabs.sciana.tab_sciana import TabSciana

    catalog = CatalogStoreJson()
    store = ModuleStoreJson()

    module = ModuleDef(
        name="WARD_1",
        width_mm=600.0,
        depth_mm=450.0,
        height_mm=1800.0,
        module_family="wardrobe",
        inherit_height_from_wall=True,
        inherit_depth_from_wall=True,
        inherit_materials_from_group=True,
        inherit_edgeband_from_group=True,
        visible_parts={"side_left", "side_right", "top", "bottom", "front"},
        materials={"carcass": "PB18", "front": "MDF19", "back": "HDF2.5"},
    )
    module.parts = build_module_parts(module, catalog)
    store.save_new(module)

    w = TabSciana()
    profile_idx = w.cb_profile.findData("OAK_PREMIUM")
    assert profile_idx >= 0
    w.cb_profile.setCurrentIndex(profile_idx)
    w.sp_height.setValue(2400.0)
    w.sp_depth.setValue(620.0)

    assert _select_saved_module(w.tree_saved_modules, "WARD_1")
    w.btn_add_saved.click()

    resolved = w._resolved_items[0].module
    assert float(resolved.height_mm) == 2400.0
    assert float(resolved.depth_mm) == 620.0
    assert resolved.materials["front"] == "MDF19_LAK"
    assert resolved.edgebands["front"] == "ABS 2.0"
    assert resolved.hinge_vendor == "blum"


def test_sciana_tab_can_bind_assembly_to_saved_wall_and_metadata(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.order_models import OrderDef
    from src.domain.wall_models import WallLayoutDef
    from src.domain.worker_models import WorkerDef
    from src.storage.module_store_json import ModuleStoreJson
    from src.storage.order_store_json import OrderStoreJson
    from src.storage.wall_store_json import WallStoreJson
    from src.storage.worker_store_json import WorkerStoreJson
    from src.tabs.sciana.tab_sciana import TabSciana

    module_store = ModuleStoreJson(path=tmp_path / "modules.json")
    wall_store = WallStoreJson(path=tmp_path / "walls.json")
    order_store = OrderStoreJson(path=tmp_path / "orders.json")
    worker_store = WorkerStoreJson(path=tmp_path / "workers.json")
    worker_store.save_new(WorkerDef(name="Kierownik Montazu"))
    order_store.save_new(
        OrderDef(
            code="ORDER-S-01",
            client_name="Klient Sciana",
            worker_name="Kierownik Montazu",
            status="Do akceptacji",
            site_address="Gdansk, Morska 22",
        )
    )
    wall_store.save_new(
        WallLayoutDef(
            name="SCIANA_KUCHNIA_1",
            client_name="Klient Sciana",
            order_name="ORDER-S-01",
            worker_name="Kierownik Montazu",
            front_view_wall_side="B",
            wall_a_width_mm=4000.0,
            wall_b_width_mm=2600.0,
            room_height_mm=2750.0,
            base_depth_mm=620.0,
        )
    )

    w = TabSciana(module_store=module_store, wall_store=wall_store, order_store=order_store, worker_store=worker_store)
    idx = w.cb_wall.findData("SCIANA_KUCHNIA_1")
    assert idx >= 0

    w.cb_wall.setCurrentIndex(idx)

    assert w.ed_client.text() == "Klient Sciana"
    assert w.ed_order.text() == "ORDER-S-01"
    assert float(w.sp_width.value()) == 2600.0
    assert float(w.sp_height.value()) == 2750.0
    assert float(w.sp_depth.value()) == 620.0
    assert getattr(w._assembly, "wall_name", "") == "SCIANA_KUCHNIA_1"
    assert getattr(w._assembly, "client_name", "") == "Klient Sciana"
    assert getattr(w._assembly, "order_name", "") == "ORDER-S-01"
    assert getattr(w._assembly, "worker_name", "") == "Kierownik Montazu"
    assert "Powiazana sciana: SCIANA_KUCHNIA_1" in w.lab_summary.text()
    assert "Klient: Klient Sciana" in w.lab_summary.text()
    assert "Zamowienie: ORDER-S-01" in w.lab_summary.text()
    assert "Pracownik: Kierownik Montazu" in w.lab_summary.text()
    assert "Status zamowienia: Do akceptacji" in w.lab_summary.text()
    assert "Adres realizacji: Gdansk, Morska 22" in w.lab_summary.text()


def test_sciana_tab_preview_draws_linked_wall_context_from_saved_wall(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.wall_models import WallLayoutDef, WallObstacleDef
    from src.storage.wall_store_json import WallStoreJson
    from src.tabs.sciana.tab_sciana import TabSciana

    wall_store = WallStoreJson(path=tmp_path / "walls.json")
    wall_store.save_new(
        WallLayoutDef(
            name="SCIANA_Z_OKNEM",
            client_name="Klient Test",
            order_name="ORDER-WALL-01",
            worker_name="Monter 1",
            front_view_wall_side="A",
            wall_a_width_mm=3200.0,
            room_height_mm=2700.0,
            base_depth_mm=620.0,
            base_plinth_mm=120.0,
            upper_clearance_mm=80.0,
            base_offset_left_mm=150.0,
            obstacles=[
                WallObstacleDef(
                    kind="window",
                    wall_side="A",
                    name="Okno 1",
                    x_mm=700.0,
                    bottom_offset_mm=900.0,
                    width_mm=1200.0,
                    height_mm=1100.0,
                    depth_mm=150.0,
                )
            ],
        )
    )

    w = TabSciana(wall_store=wall_store)
    w.start_new_assembly_from_wall_context(
        {
            "wall_name": "SCIANA_Z_OKNEM",
            "client_name": "Klient Test",
            "order_name": "ORDER-WALL-01",
            "worker_name": "Monter 1",
            "width_mm": 3200.0,
            "height_mm": 2700.0,
            "depth_mm": 620.0,
        }
    )

    assert str(w.cb_wall.currentData() or "") == "SCIANA_Z_OKNEM"
    assert _scene_has_key(w.preview, "assembly_wall_frame") is True
    assert _scene_has_key(w.preview, "assembly_wall_side") is True
    assert _scene_has_key(w.preview, "assembly_zone__base") is True
    assert _scene_has_key(w.preview, "assembly_zone__upper") is True
    assert _scene_has_key(w.preview_top, "assembly_top_wall") is True
    assert _scene_has_key(w.preview, "assembly_wall_guide__base_plinth") is True
    assert _scene_has_key(w.preview, "assembly_wall_guide__upper_clearance") is True
    assert _scene_has_key(w.preview, "assembly_wall_guide__base_left") is True
    assert _scene_has_key(w.preview, "assembly_wall_obstacle__0") is True
    assert float(w.preview.scene.sceneRect().left()) <= -29.0
    assert float(w.preview.scene.sceneRect().top()) <= -40.0


def test_sciana_tab_shows_architect_references_for_selected_order_context(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.order_models import OrderDef
    from src.storage.order_store_json import OrderStoreJson
    from src.tabs.sciana.tab_sciana import TabSciana

    image_path = tmp_path / "komplet_ref.png"
    pixmap = QPixmap(120, 80)
    pixmap.fill(Qt.GlobalColor.white)
    assert pixmap.save(str(image_path))

    order_store = OrderStoreJson(path=tmp_path / "orders.json")
    order_store.save_new(
        OrderDef(
            code="ORDER-REF-01",
            attachments=[
                {
                    "path": str(image_path),
                    "kind": "Obraz",
                    "description": "Wizualizacja szafy",
                    "target_kind": "Komplet",
                    "target_name": "Szafa wejscie",
                    "source_page": "Strona 2",
                }
            ],
        )
    )

    w = TabSciana(order_store=order_store)
    w.start_new_assembly_from_wall_context(
        {
            "order_name": "ORDER-REF-01",
            "quote_item_name": "Szafa wejscie",
            "quote_item_kind": "Szafa",
        }
    )

    assert w.tbl_project_refs.rowCount() == 1
    assert w.tbl_project_refs.item(0, 0).text() == "komplet_ref.png"
    assert "Komplet / Szafa wejscie" in w.tbl_project_refs.item(0, 1).text()
    assert "Wizualizacja szafy" in w.tbl_project_refs.item(0, 2).text()
    assert w.lab_project_reference_info.text()
    assert w.lab_project_reference_preview.pixmap() is not None
    assert not w.lab_project_reference_preview.pixmap().isNull()


def test_sciana_tab_places_lower_and_hanging_modules_in_wall_zones(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.core.module_parts_service import build_module_parts
    from src.domain.module_models import ModuleDef
    from src.domain.wall_models import WallLayoutDef
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.storage.module_store_json import ModuleStoreJson
    from src.storage.wall_store_json import WallStoreJson
    from src.tabs.sciana.tab_sciana import TabSciana

    catalog = CatalogStoreJson()
    module_store = ModuleStoreJson(path=tmp_path / "modules.json")
    wall_store = WallStoreJson(path=tmp_path / "walls.json")

    wall_store.save_new(
        WallLayoutDef(
            name="ZONE_WALL",
            wall_a_width_mm=4000.0,
            room_height_mm=2600.0,
            base_depth_mm=600.0,
            base_plinth_mm=100.0,
            upper_clearance_mm=200.0,
        )
    )

    lower = ModuleDef(
        name="LOWER_ZONE",
        width_mm=800.0,
        depth_mm=560.0,
        height_mm=720.0,
        module_type="legs_plinth",
        cabinet_kind="lower",
    )
    lower.parts = build_module_parts(lower, catalog)
    module_store.save_new(lower)

    upper = ModuleDef(
        name="UPPER_ZONE",
        width_mm=800.0,
        depth_mm=320.0,
        height_mm=720.0,
        module_type="hanging",
        cabinet_kind="upper",
    )
    upper.parts = build_module_parts(upper, catalog)
    module_store.save_new(upper)

    w = TabSciana(module_store=module_store, wall_store=wall_store)
    w.start_new_assembly_from_wall_context(
        {
            "wall_name": "ZONE_WALL",
            "width_mm": 4000.0,
            "height_mm": 2600.0,
            "depth_mm": 600.0,
        }
    )
    app.processEvents()

    w._add_saved_module_by_name("LOWER_ZONE")
    w._add_saved_module_by_name("UPPER_ZONE")
    app.processEvents()

    assert len(w._resolved_items) == 2
    assert abs(float(w._resolved_items[0].y_mm) - 1780.0) < 0.1
    assert abs(float(w._resolved_items[1].y_mm) - 200.0) < 0.1


def test_sciana_tab_allows_module_under_module_without_horizontal_collision(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.core.module_parts_service import build_module_parts
    from src.domain.module_models import ModuleDef
    from src.domain.wall_models import WallLayoutDef
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.storage.module_store_json import ModuleStoreJson
    from src.storage.wall_store_json import WallStoreJson
    from src.tabs.sciana.tab_sciana import TabSciana

    catalog = CatalogStoreJson()
    module_store = ModuleStoreJson(path=tmp_path / "modules_under.json")
    wall_store = WallStoreJson(path=tmp_path / "walls_under.json")

    wall_store.save_new(
        WallLayoutDef(
            name="STACK_WALL",
            wall_a_width_mm=4000.0,
            room_height_mm=2600.0,
            base_depth_mm=600.0,
            base_plinth_mm=100.0,
            upper_clearance_mm=200.0,
        )
    )

    upper = ModuleDef(
        name="STACK_UPPER",
        width_mm=800.0,
        depth_mm=320.0,
        height_mm=720.0,
        module_type="hanging",
        cabinet_kind="upper",
    )
    upper.parts = build_module_parts(upper, catalog)
    module_store.save_new(upper)

    lower = ModuleDef(
        name="STACK_LOWER",
        width_mm=800.0,
        depth_mm=560.0,
        height_mm=720.0,
        module_type="legs_plinth",
        cabinet_kind="lower",
    )
    lower.parts = build_module_parts(lower, catalog)
    module_store.save_new(lower)

    w = TabSciana(module_store=module_store, wall_store=wall_store)
    w.start_new_assembly_from_wall_context(
        {
            "wall_name": "STACK_WALL",
            "width_mm": 4000.0,
            "height_mm": 2600.0,
            "depth_mm": 600.0,
        }
    )
    app.processEvents()

    w._add_saved_module_by_name("STACK_UPPER")
    w._add_saved_module_by_name("STACK_LOWER")
    app.processEvents()

    assert len(w._resolved_items) == 2
    assert str(getattr(w._assembly.items[1], "offset_ref_mode", "")) == "wall_left"

    align_left_offset = float(w._resolved_items[0].x_mm) - float(w.preview._base_x_for_module_index(1))
    snap_candidates = list(w.preview._snap_offset_candidate_values(1))
    assert any(abs(candidate - align_left_offset) < 0.1 for candidate in snap_candidates)

    w._assembly.items[1].offset_mm = align_left_offset
    w._rebuild_assembly(select_index=1)
    app.processEvents()

    assert abs(float(w._resolved_items[0].x_mm) - float(w._resolved_items[1].x_mm)) < 0.1
    assert abs(float(w._resolved_items[0].y_mm) - float(w._resolved_items[1].y_mm)) > 100.0
    assert bool(getattr(w._resolved_items[0], "has_collision", False)) is False
    assert bool(getattr(w._resolved_items[1], "has_collision", False)) is False


def test_sciana_tab_can_save_and_load_assembly_with_metadata(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.core.module_parts_service import build_module_parts
    from src.domain.assembly_models import FurnitureAssemblyDef
    from src.domain.module_models import ModuleDef
    from src.domain.order_models import OrderDef
    from src.domain.wall_models import WallLayoutDef
    from src.domain.worker_models import WorkerDef
    from src.storage.assembly_store_json import AssemblyStoreJson
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.storage.module_store_json import ModuleStoreJson
    from src.storage.order_store_json import OrderStoreJson
    from src.storage.wall_store_json import WallStoreJson
    from src.storage.worker_store_json import WorkerStoreJson
    from src.tabs.sciana import tab_sciana as assembly_tab_module
    from src.tabs.sciana.tab_sciana import TabSciana

    catalog = CatalogStoreJson()
    module_store = ModuleStoreJson(path=tmp_path / "modules.json")
    wall_store = WallStoreJson(path=tmp_path / "walls.json")
    order_store = OrderStoreJson(path=tmp_path / "orders.json")
    worker_store = WorkerStoreJson(path=tmp_path / "workers.json")
    assembly_store = AssemblyStoreJson(path=tmp_path / "assemblies.json")

    worker_store.save_new(WorkerDef(name="Jan Monter"))
    order_store.save_new(
        OrderDef(
            code="ORD-K-01",
            client_name="Klient K",
            worker_name="Jan Monter",
            status="Nowe",
            site_address="Poznan 10",
        )
    )
    wall_store.save_new(
        WallLayoutDef(
            name="SCIANA_K",
            client_name="Klient K",
            order_name="ORD-K-01",
            worker_name="Jan Monter",
            front_view_wall_side="A",
            wall_a_width_mm=3600.0,
            room_height_mm=2650.0,
            base_depth_mm=610.0,
        )
    )

    module = ModuleDef(name="MOD_K", width_mm=800.0, depth_mm=500.0, height_mm=720.0)
    module.parts = build_module_parts(module, catalog)
    module_store.save_new(module)

    w = TabSciana(
        module_store=module_store,
        wall_store=wall_store,
        order_store=order_store,
        worker_store=worker_store,
        assembly_store=assembly_store,
    )

    w.ed_name.setText("KOMPLET_UI")
    wall_idx = w.cb_wall.findData("SCIANA_K")
    assert wall_idx >= 0
    w.cb_wall.setCurrentIndex(wall_idx)
    assert _select_saved_module(w.tree_saved_modules, "MOD_K")
    w.btn_add_saved.click()
    w.btn_save.click()

    saved = assembly_store.get("KOMPLET_UI")
    assert saved is not None
    assert saved.client_name == "Klient K"
    assert saved.order_name == "ORD-K-01"
    assert saved.worker_name == "Jan Monter"
    assert saved.wall_name == "SCIANA_K"
    assert len(saved.items) == 1

    class _FakeLoadAssemblyDialog:
        DialogCode = QDialog.DialogCode

        def __init__(self, _parent, _store):
            self._assembly = FurnitureAssemblyDef(
                name="KOMPLET_WCZYTANY",
                wall_name="SCIANA_K",
                client_name="Klient K",
                order_name="ORD-K-01",
                worker_name="Jan Monter",
                width_mm=3600.0,
                height_mm=2650.0,
                depth_mm=610.0,
                items=saved.items,
            )

        def exec(self):
            return self.DialogCode.Accepted

        def selected_assembly(self):
            return self._assembly

    monkeypatch.setattr(assembly_tab_module, "LoadAssemblyDialog", _FakeLoadAssemblyDialog)

    w.btn_load.click()

    assert w.ed_name.text() == "KOMPLET_WCZYTANY"
    assert w.ed_client.text() == "Klient K"
    assert w.ed_order.text() == "ORD-K-01"
    assert w.cb_worker.currentData() == "Jan Monter"
    assert w.tbl_items.rowCount() == 1
    assert "Pracownik: Jan Monter" in w.lab_summary.text()


def test_sciana_tab_shows_compact_ustawienia_panel(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.sciana.tab_sciana import TabSciana

    w = TabSciana()

    assert w.box_setup.title() == "Ustawienia"
    assert w.sp_width.isHidden()
    assert w.sp_height.isHidden()
    assert w.sp_depth.isHidden()
    assert w.sp_gap.isHidden()
    assert w.cb_profile.isHidden()
    assert w.chk_force_hardware.isHidden()
