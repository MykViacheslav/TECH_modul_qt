def test_module_store_lists_names_grouped_by_base_group(tmp_path):
    from src.domain.module_models import ModuleDef
    from src.storage.module_store_json import ModuleStoreJson

    store = ModuleStoreJson(path=tmp_path / "modules.json")
    store.save_new(ModuleDef(name="KUCHNIA_1", base_group="kitchen"))
    store.save_new(ModuleDef(name="SZAFA_1", base_group="wardrobe"))
    store.save_new(ModuleDef(name="LAZIENKA_1", base_group="bathroom"))
    store.save_new(ModuleDef(name="INNE_1", base_group="other"))

    grouped = store.list_grouped_names()

    assert grouped["kitchen"] == ["KUCHNIA_1"]
    assert grouped["wardrobe"] == ["SZAFA_1"]
    assert grouped["bathroom"] == ["LAZIENKA_1"]
    assert grouped["other"] == ["INNE_1"]


def test_module_store_keeps_custom_base_groups(tmp_path):
    from src.domain.module_models import ModuleDef
    from src.storage.module_store_json import ModuleStoreJson

    store = ModuleStoreJson(path=tmp_path / "modules.json")
    store.save_new(ModuleDef(name="CUSTOM_1", base_group="Biuro premium"))

    grouped = store.list_grouped_names()
    base_groups = store.list_base_groups()

    assert grouped["Biuro premium"] == ["CUSTOM_1"]
    assert "Biuro premium" in base_groups
