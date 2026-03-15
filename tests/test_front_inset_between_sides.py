from PyQt6.QtWidgets import QApplication


def test_front_inset_dimensions_are_between_sides(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    # bazowe wymiary
    w.dim.sp_w.setValue(800.0)
    w.dim.sp_d.setValue(500.0)
    w.dim.sp_h.setValue(700.0)

    # korpus + front
    w.vis.set_checked(set(["side_left", "side_right", "top", "bottom", "front"]))
    idx = w.fhw.cb_front_layout.findData("inset")
    if idx >= 0:
        w.fhw.cb_front_layout.setCurrentIndex(idx)

    w._on_any_change()

    front = w._draft.parts.get("front")
    assert front is not None

    t = float(front.dims_mm["t"])
    # tu t frontu nie jest potrzebne, sprawdzamy szer./wys. frontu wg korpusu
    carcass_t = float(w._catalog.material_thickness(w._draft.materials.get("carcass", "PB18"), 18.0))

    assert abs(float(front.dims_mm["w"]) - (800.0 - 2 * carcass_t)) < 0.01
    assert abs(float(front.dims_mm["h"]) - (700.0 - 2 * carcass_t)) < 0.01