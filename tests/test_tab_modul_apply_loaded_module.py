from PyQt6.QtWidgets import QApplication

from src.domain.module_models import ModuleDef

def test_apply_loaded_module_updates_ui(monkeypatch):
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    m = ModuleDef(
        name="TEST_LOAD",
        width_mm=777.0,
        depth_mm=333.0,
        height_mm=444.0,
        carcass_joint_type="type2",
        shelf_count=2,
        divider_count=1,
        shelf_mount="right",
        cabinet_kind="upper",
        ref_point="LBT",
        visible_parts=set(["side_left","side_right","top","bottom","shelf","front","back","divider"]),
        materials={"carcass":"PB18","front":"MDF19","back":"HDF2.5"},
        parts={}
    )

    w._apply_loaded_module(m)

    assert abs(w.dim.sp_w.value() - 777.0) < 0.001
    assert abs(w.dim.sp_d.value() - 333.0) < 0.001
    assert abs(w.dim.sp_h.value() - 444.0) < 0.001

    got_vis = w.vis.get_visible_parts()
    assert "side_left" in got_vis
    assert "front" in got_vis
    assert "divider" in got_vis

    got_mat = w.mat.get_materials()
    assert got_mat["carcass"] == "PB18"
    assert got_mat["front"] == "MDF19"
    assert got_mat["back"] == "HDF2.5"

    assert w.ref.get_kind() == "upper"
    assert w.ref.get_ref() == "LBT"