from PyQt6.QtWidgets import QApplication

from src.domain.module_models import ModuleDef


def _any(obj, names):
    for n in names:
        if hasattr(obj, n):
            return getattr(obj, n)
    raise AssertionError(f"Brak wymaganej metody/atrybutu: {names} w {type(obj).__name__}")


def test_blocks_contracts_smoke(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")
    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import (
        DimensionsBlock, VisiblePartsBlock, CarcassJointsBlock, ReferencePointBlock,
        ShelvesBlock, DividersBlock, DrawingSettingsBlock, ProjectTreeBlock,
        BomBlock, ViewsCanvas
    )
    from src.storage.catalog_store_json import CatalogStoreJson
    from src.tabs.modul.tab_modul import MaterialsBlock, EdgeBandingBlock, FrontHardwareBlock

    # --- DimensionsBlock ---
    dim = DimensionsBlock()
    assert hasattr(dim, "sp_w") and hasattr(dim, "sp_d") and hasattr(dim, "sp_h")
    dim.sp_w.setValue(800.0)
    dim.sp_d.setValue(500.0)
    dim.sp_h.setValue(500.0)
    assert dim.sp_w.value() == 800.0

    # --- VisiblePartsBlock ---
    vis = VisiblePartsBlock()
    _any(vis, ["set_checked"])(set(["side_left", "front"]))
    got = _any(vis, ["get_visible_parts"])()
    assert "front" in got

    # --- CarcassJointsBlock ---
    j = CarcassJointsBlock()
    _any(j, ["set_value"])("type2")
    assert _any(j, ["get_value"])() == "type2"

    # --- ReferencePointBlock ---
    r = ReferencePointBlock()
    _any(r, ["set_values"])("upper", "LBT")
    assert _any(r, ["get_kind"])() == "upper"
    assert _any(r, ["get_ref"])() == "LBT"

    # --- ShelvesBlock ---
    sh = ShelvesBlock()
    _any(sh, ["set_value"])(2)
    assert _any(sh, ["get_value"])() == 2

    # --- DividersBlock ---
    dv = DividersBlock()
    _any(dv, ["set_values"])(2, "right")
    assert _any(dv, ["get_count"])() == 2
    assert _any(dv, ["get_mount"])() in ("left", "right")

    # --- MaterialsBlock ---
    cat = CatalogStoreJson()
    mb = MaterialsBlock(cat)
    _any(mb, ["set_materials"])({"carcass": "PB18", "front": "MDF19", "back": "HDF2.5"})
    mats = _any(mb, ["get_materials"])()
    assert mats["carcass"] == "PB18"

    # --- FrontHardwareBlock ---
    fhw = FrontHardwareBlock()
    m = ModuleDef(
        name="X", width_mm=800, depth_mm=500, height_mm=500,
        visible_parts=set(["front"]), materials={"carcass": "PB18", "front": "MDF19", "back": "HDF2.5"},
        parts={}
    )
    _any(fhw, ["set_from_module"])(m)
    _any(fhw, ["apply_to_module"])(m)

    # --- DrawingSettingsBlock (smoke) ---
    ds = DrawingSettingsBlock()
    assert ds is not None

    # --- ProjectTreeBlock + BOM + Canvas (smoke) ---
    tree = ProjectTreeBlock()
    bom = BomBlock(cat)
    canvas = ViewsCanvas()
    assert tree is not None and bom is not None and canvas is not None

    # EdgeBandingBlock (smoke + metody)
    eb = EdgeBandingBlock(cat)
    assert hasattr(eb, "sig_changed")