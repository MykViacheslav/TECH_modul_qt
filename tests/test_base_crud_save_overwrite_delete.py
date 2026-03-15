from PyQt6.QtWidgets import QApplication


def _set_front_zone_offsets_mode(w, top_mm: float, bottom_mm: float) -> None:
    idx = w.fhw.cb_front_height_mode.findData("offsets")
    if idx >= 0:
        w.fhw.cb_front_height_mode.setCurrentIndex(idx)

    w.fhw.sp_front_offset_top.setValue(float(top_mm))
    w.fhw.sp_front_offset_bottom.setValue(float(bottom_mm))
    w._on_any_change()


def _set_front_zone_to_top_rail_mode(w, bottom_mm: float) -> None:
    idx = w.fhw.cb_front_height_mode.findData("to_top_rail")
    if idx >= 0:
        w.fhw.cb_front_height_mode.setCurrentIndex(idx)

    w.fhw.sp_front_offset_bottom.setValue(float(bottom_mm))
    w._on_any_change()


def _coerce_loaded_module(w, raw):
    ModuleCls = type(w._draft)

    if raw is None:
        raise AssertionError("Store zwrocil None przy wczytywaniu modulu.")

    # czasem wynik jest opakowany
    if hasattr(raw, "module"):
        raw = raw.module

    # jesli juz jest ModuleDef
    if isinstance(raw, ModuleCls):
        return raw

    # jesli store zwraca dict/opakowany dict
    if isinstance(raw, dict):
        if "module" in raw and isinstance(raw["module"], dict):
            raw = raw["module"]

        for fn_name in ("from_dict", "from_json_dict", "model_validate"):
            if hasattr(ModuleCls, fn_name):
                fn = getattr(ModuleCls, fn_name)
                try:
                    return fn(raw)
                except Exception:
                    pass

    raise AssertionError(f"Nie umiem zrzutowac wyniku store do ModuleDef: {type(raw)!r}")


def _load_module_from_store_by_name(w, name: str):
    store = w._store

    for fn_name in ("load", "load_module", "get", "read"):
        if not hasattr(store, fn_name):
            continue

        fn = getattr(store, fn_name)
        try:
            raw = fn(name)
        except TypeError:
            continue

        return _coerce_loaded_module(w, raw)

    raise AssertionError("Store nie ma metody load/load_module/get/read.")


def test_base_crud_save_overwrite_delete(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    # ------------------------------------------------------
    # SAVE
    # ------------------------------------------------------
    w.dim.ed_name.setText("TEST_CRUD_FRONT_ZONE")
    w.dim.sp_w.setValue(800.0)
    w.dim.sp_d.setValue(560.0)
    w.dim.sp_h.setValue(720.0)

    _set_front_zone_offsets_mode(w, 120.0, 35.0)

    w._on_dim_save_clicked()

    names = list(w._store_list_names())
    assert "TEST_CRUD_FRONT_ZONE" in names
    assert w._store_has("TEST_CRUD_FRONT_ZONE") is True

    # ------------------------------------------------------
    # OVERWRITE
    # ------------------------------------------------------
    _set_front_zone_offsets_mode(w, 140.0, 45.0)
    w._on_dim_overwrite_clicked()

    # ------------------------------------------------------
    # LOAD (bez dialogu, prosto ze store)
    # ------------------------------------------------------
    loaded = _load_module_from_store_by_name(w, "TEST_CRUD_FRONT_ZONE")
    w._apply_loaded_module(loaded)

    assert w.fhw.cb_front_height_mode.currentData() == "offsets"
    assert abs(w.fhw.sp_front_offset_top.value() - 140.0) < 0.1
    assert abs(w.fhw.sp_front_offset_bottom.value() - 45.0) < 0.1

    # ------------------------------------------------------
    # DELETE
    # ------------------------------------------------------
    w.dim.ed_name.setText("TEST_CRUD_FRONT_ZONE")
    w._on_dim_delete_clicked()

    names_after = list(w._store_list_names())
    assert "TEST_CRUD_FRONT_ZONE" not in names_after
    assert w._store_has("TEST_CRUD_FRONT_ZONE") is False


def test_base_load_restores_front_zone_offsets_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    w.dim.ed_name.setText("TEST_FRONT_ZONE_OFFSETS")
    w.dim.sp_w.setValue(900.0)
    w.dim.sp_d.setValue(580.0)
    w.dim.sp_h.setValue(760.0)

    _set_front_zone_offsets_mode(w, 180.0, 22.0)
    w._on_dim_save_clicked()

    assert w._store_has("TEST_FRONT_ZONE_OFFSETS") is True

    # zmien UI, zeby sprawdzic prawdziwe przywrocenie
    idx = w.fhw.cb_front_height_mode.findData("full")
    if idx >= 0:
        w.fhw.cb_front_height_mode.setCurrentIndex(idx)
    w.fhw.sp_front_offset_top.setValue(0.0)
    w.fhw.sp_front_offset_bottom.setValue(0.0)
    w._on_any_change()

    loaded = _load_module_from_store_by_name(w, "TEST_FRONT_ZONE_OFFSETS")
    w._apply_loaded_module(loaded)

    assert w.fhw.cb_front_height_mode.currentData() == "offsets"
    assert abs(w.fhw.sp_front_offset_top.value() - 180.0) < 0.1
    assert abs(w.fhw.sp_front_offset_bottom.value() - 22.0) < 0.1


def test_base_load_restores_front_zone_to_top_rail_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.tabs.modul.tab_modul import TabModul

    w = TabModul()

    w.dim.ed_name.setText("TEST_FRONT_ZONE_TOP_RAIL")
    w.dim.sp_w.setValue(1000.0)
    w.dim.sp_d.setValue(600.0)
    w.dim.sp_h.setValue(780.0)

    _set_front_zone_to_top_rail_mode(w, 55.0)
    w._on_dim_save_clicked()

    assert w._store_has("TEST_FRONT_ZONE_TOP_RAIL") is True

    # zmien UI, zeby sprawdzic prawdziwe przywrocenie
    idx = w.fhw.cb_front_height_mode.findData("offsets")
    if idx >= 0:
        w.fhw.cb_front_height_mode.setCurrentIndex(idx)
    w.fhw.sp_front_offset_top.setValue(111.0)
    w.fhw.sp_front_offset_bottom.setValue(222.0)
    w._on_any_change()

    loaded = _load_module_from_store_by_name(w, "TEST_FRONT_ZONE_TOP_RAIL")
    w._apply_loaded_module(loaded)

    assert w.fhw.cb_front_height_mode.currentData() == "to_top_rail"
    assert abs(w.fhw.sp_front_offset_bottom.value() - 55.0) < 0.1