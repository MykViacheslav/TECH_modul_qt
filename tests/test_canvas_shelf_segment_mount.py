from PyQt6.QtWidgets import QApplication


def _item_key(it):
    k = getattr(it, "key", None)
    if k:
        return k
    try:
        return it.data(0)
    except Exception:
        return None


def test_shelf_is_drawn_only_in_selected_segment(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import ViewsCanvas
    from src.domain.module_models import ModuleDef

    m = ModuleDef(
        name="X",
        width_mm=800.0,
        depth_mm=500.0,
        height_mm=500.0,
        carcass_joint_type="type1",
        shelf_count=2,
        divider_count=1,          # jeden pion -> dwa segmenty
        shelf_mount="right",      # polki maja byc w prawym segmencie
        cabinet_kind="lower",
        ref_point="LBB",
        visible_parts=set(["side_left", "side_right", "top", "bottom", "divider", "shelf"]),
        materials={"carcass": "PB18", "front": "MDF19", "back": "HDF2.5"},
        parts={}
    )

    c = ViewsCanvas()
    c.render_module(m, fit=False, selected_part_key="shelf_1")

    # znajdz prostokat polki:
    # akceptuj rozne historyczne warianty kluczy i oba zrodla identyfikacji
    shelf = None
    accepted = {
        "shelf_1",
        "shelf-1",
        "shelf__1",
        "shelf@1",
    }

    for it in c.scene.items():
        k = _item_key(it)
        if k in accepted:
            shelf = it
            break

    assert shelf is not None

    r = shelf.rect()
    # przy jednym dividerze i mount="right" polka ma byc w prawym segmencie,
    # czyli jej lewa krawedz nie moze zaczynac sie przy lewym boku korpusu
    assert r.left() > 100.0