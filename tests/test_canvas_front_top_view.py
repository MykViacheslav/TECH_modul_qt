from tests._qt_teardown_local import qt_canvas_teardown  # noqa: F401
from PyQt6.QtWidgets import QApplication

from src.domain.module_models import ModuleDef
from src.app.app_settings import load_drawing_settings, save_drawing_settings, DrawingSettings


def test_front_exists_in_top_view(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    s = load_drawing_settings()
    sd = DrawingSettings(**{**s.__dict__, "show_front_part": True, "front_mode": "external"})
    save_drawing_settings(sd)

    from src.tabs.modul.tab_modul import ViewsCanvas

    m = ModuleDef(
        name="X",
        width_mm=800.0,
        depth_mm=500.0,
        height_mm=500.0,
        carcass_joint_type="type1",
        shelf_count=1,
        divider_count=0,
        shelf_mount="right",
        cabinet_kind="lower",
        ref_point="LBB",
        visible_parts=set(["side_left", "side_right", "top", "bottom", "front", "back", "shelf"]),
        materials={"carcass": "PB18", "front": "MDF19", "back": "HDF2.5"},
        parts={}
    )

    c = ViewsCanvas()
    c.render_module(m, fit=False, selected_part_key="front")

    keys = []
    front_top_rect_h = None

    for it in c.scene.items():
        try:
            k = it.data(0)
        except Exception:
            k = None

        if isinstance(k, str) and k:
            keys.append(k)
            if k == "front__top":
                try:
                    front_top_rect_h = float(it.rect().height())
                except Exception:
                    front_top_rect_h = None

    assert "front__top" in keys
    assert front_top_rect_h is not None
    assert front_top_rect_h > 0.5  # musi byc dodatnia wysokosc
