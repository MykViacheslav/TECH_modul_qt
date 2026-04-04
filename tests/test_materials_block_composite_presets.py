from PyQt6.QtWidgets import QApplication


def test_materials_block_applies_composite_preset_for_front(tmp_path):
    app = QApplication.instance() or QApplication([])

    from src.storage.catalog_store_json import CatalogStoreJson
    from src.tabs.modul.materials_block import MaterialsBlock

    catalog = CatalogStoreJson(tmp_path / "catalog.json")
    block = MaterialsBlock(catalog)

    idx_target = block.cb_composite_target.findData("front")
    assert idx_target >= 0
    block.cb_composite_target.setCurrentIndex(idx_target)

    idx_preset = block.cb_composite_preset.findData("veneer_2s_06")
    assert idx_preset >= 0
    block.cb_composite_preset.setCurrentIndex(idx_preset)
    block._apply_composite_preset()

    front_key = str(block.cb_front.currentData() or "MDF19")
    mat = catalog.get_material(front_key)
    assert mat is not None
    assert mat.composite_enabled is True
    assert abs(float(mat.left_facing_thickness_mm) - 0.6) < 0.001
    assert abs(float(mat.right_facing_thickness_mm) - 0.6) < 0.001
    assert abs(catalog.material_thickness(front_key, mat.thickness_mm) - float(mat.thickness_mm)) < 0.001
    assert "Zastosowano preset" in str(block.lab_composite_status.text() or "")


def test_materials_block_can_clear_composite_preset(tmp_path):
    app = QApplication.instance() or QApplication([])

    from src.storage.catalog_store_json import CatalogStoreJson
    from src.tabs.modul.materials_block import MaterialsBlock

    catalog = CatalogStoreJson(tmp_path / "catalog.json")
    block = MaterialsBlock(catalog)

    idx_target = block.cb_composite_target.findData("carcass")
    assert idx_target >= 0
    block.cb_composite_target.setCurrentIndex(idx_target)

    idx_hpl = block.cb_composite_preset.findData("hpl_1s_08")
    assert idx_hpl >= 0
    block.cb_composite_preset.setCurrentIndex(idx_hpl)
    block._apply_composite_preset()

    carcass_key = str(block.cb_carcass.currentData() or "PB18")
    mat_before_clear = catalog.get_material(carcass_key)
    assert mat_before_clear is not None
    assert mat_before_clear.composite_enabled is True

    idx_none = block.cb_composite_preset.findData("none")
    assert idx_none >= 0
    block.cb_composite_preset.setCurrentIndex(idx_none)
    block._apply_composite_preset()

    mat_after_clear = catalog.get_material(carcass_key)
    assert mat_after_clear is not None
    assert mat_after_clear.composite_enabled is False
    assert abs(float(mat_after_clear.core_thickness_mm) - 0.0) < 0.001
    assert abs(float(mat_after_clear.left_facing_thickness_mm) - 0.0) < 0.001
    assert abs(float(mat_after_clear.right_facing_thickness_mm) - 0.0) < 0.001
    assert "Wyczyszczono kompozyt" in str(block.lab_composite_status.text() or "")
