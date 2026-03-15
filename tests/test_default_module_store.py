import dataclasses

from src.domain.module_models import ModuleDef
from src.storage.default_module_store_json import save_default_module, load_default_module


def test_save_load_default_module(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))

    m = ModuleDef(
        name="TEST",
        width_mm=800.0,
        depth_mm=500.0,
        height_mm=500.0,
        carcass_joint_type="type2",
        shelf_count=2,
        divider_count=1,
        shelf_mount="right",
        cabinet_kind="lower",
        ref_point="LBB",
        visible_parts=set(["side_left", "side_right", "top", "bottom", "shelf", "back", "front", "divider"]),
        materials={"carcass": "PB16", "front": "MDF19", "back": "HDF2.5"},
        parts={},
    )

    save_default_module(m)
    m2 = load_default_module()

    assert m2 is not None
    assert m2.to_dict() == m.to_dict()
    # sanity: pola sa naprawde w modelu
    assert "divider_count" in [f.name for f in dataclasses.fields(ModuleDef)]