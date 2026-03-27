def test_modul_splitter_sizes_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))

    from src.app.app_settings import load_modul_splitter_sizes, save_modul_splitter_sizes

    assert load_modul_splitter_sizes() == [360, 900, 360]

    save_modul_splitter_sizes([420, 860, 400])

    assert load_modul_splitter_sizes() == [420, 860, 400]


def test_table_column_widths_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))

    from src.app.app_settings import load_table_column_widths, save_table_column_widths

    assert load_table_column_widths("bazy_clients") == []

    save_table_column_widths("bazy_clients", [120, 180, 220, 170, 240, 320])

    assert load_table_column_widths("bazy_clients") == [120, 180, 220, 170, 240, 320]
