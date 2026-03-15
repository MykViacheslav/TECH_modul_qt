from PyQt6.QtWidgets import QApplication

from src.domain.module_models import ModuleDef


def test_blocks_pull_after_apply(tmp_path, monkeypatch):
    # izolacja plikow data/ w testach
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul
    w = TabModul()

    m = ModuleDef(
        name="LOAD_X",
        width_mm=777.0,
        depth_mm=333.0,
        height_mm=444.0,
        carcass_joint_type="type2",
        shelf_count=2,
        divider_count=1,
        shelf_mount="right",
        module_type="hanging",
        cabinet_kind="upper",
        ref_point="LBT",
        visible_parts=set(["side_left","side_right","top","bottom","shelf","front","back","divider"]),
        materials={"carcass":"PB18","front":"MDF19","back":"HDF2.5"},
        parts={}
    )

    # 1) apply -> UI
    w._apply_loaded_module(m)

    # 2) pull UI -> draft
    w._pull_ui_to_draft()

    # 3) sprawdz, czy draft ma to co wczytalismy
    assert w._draft.width_mm == 777.0
    assert w._draft.depth_mm == 333.0
    assert w._draft.height_mm == 444.0

    assert w._draft.carcass_joint_type == "type2"
    assert w._draft.shelf_count == 2
    assert w._draft.divider_count == 1
    assert w._draft.shelf_mount == "right"

    assert w._draft.module_type == "hanging"
    assert w._draft.cabinet_kind == "upper"
    assert w._draft.ref_point == "LBT"

    assert "divider" in w._draft.visible_parts
    assert "front" in w._draft.visible_parts
    assert w._draft.materials.get("carcass") == "PB18"
    assert w._draft.materials.get("front") == "MDF19"
    assert w._draft.materials.get("back") == "HDF2.5"
