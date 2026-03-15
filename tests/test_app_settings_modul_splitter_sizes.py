def test_modul_splitter_sizes_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))

    from src.app.app_settings import load_modul_splitter_sizes, save_modul_splitter_sizes

    assert load_modul_splitter_sizes() == [360, 900, 360]

    save_modul_splitter_sizes([420, 860, 400])

    assert load_modul_splitter_sizes() == [420, 860, 400]
