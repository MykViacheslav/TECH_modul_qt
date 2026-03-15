from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication


def _find_child_by_name(tree, name: str):
    for top_index in range(tree.topLevelItemCount()):
        group_item = tree.topLevelItem(top_index)
        for child_index in range(group_item.childCount()):
            child = group_item.child(child_index)
            if str(child.data(0, Qt.ItemDataRole.UserRole) or "") == name:
                return child
    return None


def test_load_module_dialog_preview_builds_real_module_shapes(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.core.module_parts_service import build_module_parts
    from src.domain.module_models import ModuleDef
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.storage.module_store_json import ModuleStoreJson
    from src.tabs.modul.dialog_load_module import LoadModuleDialog

    catalog = CatalogStoreJson()
    store = ModuleStoreJson(path=tmp_path / "modules.json")

    module = ModuleDef(
        name="PREVIEW_TEST",
        width_mm=900.0,
        depth_mm=560.0,
        height_mm=720.0,
        shelf_count=2,
        divider_count=1,
        visible_parts={"side_left", "side_right", "top", "bottom", "shelf", "divider", "front", "back"},
        materials={"carcass": "PB18", "front": "MDF19", "back": "HDF2.5"},
    )
    module.parts = build_module_parts(module, catalog)
    store.save_new(module)

    dlg = LoadModuleDialog(None, store)
    dlg.resize(980, 560)
    item = _find_child_by_name(dlg.tree, "PREVIEW_TEST")
    assert item is not None
    dlg.tree.setCurrentItem(item)

    spec = dlg.preview.build_render_spec(520.0, 320.0)
    front_keys = [shape["key"] for shape in spec["front_shapes"]]
    top_keys = [shape["key"] for shape in spec["top_shapes"]]

    assert spec["front_caption"] == "Widok z przodu"
    assert spec["top_caption"] == "Widok z gory"
    assert "front" in front_keys
    assert any(key.startswith("shelf_") for key in front_keys)
    assert any(key.startswith("divider_") for key in front_keys)
    assert "outline" in top_keys


def test_load_module_dialog_shows_clean_ascii_info_text(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.module_models import ModuleDef
    from src.storage.module_store_json import ModuleStoreJson
    from src.tabs.modul.dialog_load_module import LoadModuleDialog

    store = ModuleStoreJson(path=tmp_path / "modules.json")
    store.save_new(ModuleDef(name="INFO_TEST", width_mm=800.0, depth_mm=500.0, height_mm=700.0))

    dlg = LoadModuleDialog(None, store)
    item = _find_child_by_name(dlg.tree, "INFO_TEST")
    assert item is not None
    dlg.tree.setCurrentItem(item)
    info_text = dlg.info.text()

    assert "Nazwa: INFO_TEST" in info_text
    assert "Grupa bazy: Kuchnia" in info_text
    assert "Polki:" in info_text
    assert "Laczenie:" in info_text


def test_load_module_dialog_can_move_module_to_another_group(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.module_models import ModuleDef
    from src.storage.module_store_json import ModuleStoreJson
    from src.tabs.modul.dialog_load_module import LoadModuleDialog

    store = ModuleStoreJson(path=tmp_path / "modules.json")
    store.save_new(ModuleDef(name="MOVE_ME", base_group="kitchen"))

    dlg = LoadModuleDialog(None, store)
    item = _find_child_by_name(dlg.tree, "MOVE_ME")
    assert item is not None
    dlg.tree.setCurrentItem(item)

    idx = dlg.cb_target_group.findData("wardrobe")
    assert idx >= 0
    dlg.cb_target_group.setCurrentIndex(idx)
    dlg.btn_move_group.click()

    moved = store.get("MOVE_ME")
    assert moved is not None
    assert moved.base_group == "wardrobe"
    assert _find_child_by_name(dlg.tree, "MOVE_ME") is not None
    assert "Przeniesiono modul" in dlg.lab_err.text()


def test_load_module_dialog_can_delete_module_from_base(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.module_models import ModuleDef
    from src.storage.module_store_json import ModuleStoreJson
    from src.tabs.modul.dialog_load_module import LoadModuleDialog

    store = ModuleStoreJson(path=tmp_path / "modules.json")
    store.save_new(ModuleDef(name="DELETE_ME", base_group="other"))

    dlg = LoadModuleDialog(None, store)
    item = _find_child_by_name(dlg.tree, "DELETE_ME")
    assert item is not None
    dlg.tree.setCurrentItem(item)
    dlg._confirm_delete = lambda _name: True

    dlg.btn_delete.click()

    assert store.get("DELETE_ME") is None
    assert _find_child_by_name(dlg.tree, "DELETE_ME") is None
    assert "Usunieto modul" in dlg.lab_err.text()


def test_load_module_dialog_can_create_custom_group_and_move_module(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.module_models import ModuleDef
    from src.storage.module_store_json import ModuleStoreJson
    from src.tabs.modul.dialog_load_module import LoadModuleDialog

    store = ModuleStoreJson(path=tmp_path / "modules.json")
    store.save_new(ModuleDef(name="CUSTOM_GROUP_ME", base_group="kitchen"))

    dlg = LoadModuleDialog(None, store)
    item = _find_child_by_name(dlg.tree, "CUSTOM_GROUP_ME")
    assert item is not None
    dlg.tree.setCurrentItem(item)

    from src.tabs.modul import dialog_load_module as load_dialog_module

    monkeypatch.setattr(load_dialog_module.QInputDialog, "getText", lambda *args, **kwargs: ("Biuro premium", True))
    dlg.btn_add_group.click()

    moved = store.get("CUSTOM_GROUP_ME")
    assert moved is not None
    assert moved.base_group == "Biuro premium"
    assert _find_child_by_name(dlg.tree, "CUSTOM_GROUP_ME") is not None
    assert dlg.cb_target_group.findData("Biuro premium") >= 0
    assert "Przeniesiono modul" in dlg.lab_err.text()
