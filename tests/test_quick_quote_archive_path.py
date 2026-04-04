from pathlib import Path


def test_quick_quote_archive_path_uses_data_dir_env(monkeypatch, tmp_path):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))

    from src.tabs.baza_szybkich_wycen.tab_baza_szybkich_wycen import quick_quote_archive_path

    assert quick_quote_archive_path() == Path(tmp_path) / "quick_quote_archive.json"
