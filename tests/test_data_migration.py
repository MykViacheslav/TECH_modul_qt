def test_config_module_imports():
    import importlib
    mod = importlib.import_module("scripts.data_dir_config")
    assert hasattr(mod, "load_config")
    assert hasattr(mod, "apply_config")
