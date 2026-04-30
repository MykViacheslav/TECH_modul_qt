from tests._qt_teardown_local import qt_canvas_teardown  # noqa: F401
from PyQt6.QtWidgets import QApplication

from src.domain.module_models import ModuleDef


def test_front_top_is_clickable_partrect(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import ViewsCanvas

    m = ModuleDef(
        name="X",
        width_mm=800.0,
        depth_mm=500.0,
        height_mm=500.0,
        visible_parts=set(["side_left", "side_right", "top", "bottom", "front", "back"]),
        materials={"carcass": "PB18", "front": "MDF19", "back": "HDF2.5"},
        parts={},
    )

    c = ViewsCanvas()
    c.render_module(m, fit=False, selected_part_key="front")

    found = False
    for it in c.scene.items():
        k = None
        try:
            k = it.data(0)
        except Exception:
            pass

        if k == "front__top":
            # klikalnosc = nasza klasa (nazwa klasy wystarczy, bo PartRect moze byc zagniezdzony)
            assert type(it).__name__ == "PartRect"
            found = True

    assert found
