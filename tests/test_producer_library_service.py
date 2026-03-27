from __future__ import annotations

from pathlib import Path

from src.services.producer_library_service import ProducerLibraryService
from src.storage.producer_library_store_json import ProducerLibraryStoreJson


def test_producer_library_store_roundtrip(tmp_path: Path):
    store = ProducerLibraryStoreJson(path=tmp_path / "producer_library.json")
    store.save(
        rows=[{"kod": "A-1", "typ": "plyta", "nazwa": "Test", "producent": "X", "parametry": "P", "grubosc": "18", "cena_zl": "100"}],
        import_headers=["Kod", "Nazwa"],
        import_mapping={"kod": "Kod", "nazwa": "Nazwa"},
    )

    loaded = store.load()
    assert len(loaded["rows"]) == 1
    assert loaded["rows"][0]["kod"] == "A-1"
    assert loaded["import_headers"] == ["Kod", "Nazwa"]
    assert loaded["import_mapping"]["kod"] == "Kod"


def test_producer_library_service_import_mapping_and_merge(tmp_path: Path):
    service = ProducerLibraryService()
    csv_path = tmp_path / "lib.csv"
    csv_path.write_text(
        "SKU;Nazwa handlowa;Producent;Rodzaj;Spec;Grubosc mm;Cena netto\n"
        "TS-001;Front test;Swisskrono;front;U190;18;299\n",
        encoding="utf-8",
    )

    headers, rows = service.load_rows_from_csv_or_tsv(csv_path)
    mapping = {
        "kod": "SKU",
        "nazwa": "Nazwa handlowa",
        "producent": "Producent",
        "typ": "Rodzaj",
        "parametry": "Spec",
        "grubosc": "Grubosc mm",
        "cena_zl": "Cena netto",
    }
    normalized = service.rows_from_import_buffer(headers, rows, mapping)
    merged, added = service.merge_rows([], normalized)
    assert added == 1
    assert merged[0]["kod"] == "TS-001"
    assert merged[0]["cena_zl"] == "299"


def test_producer_library_service_updates_prices_by_code_or_triplet():
    service = ProducerLibraryService()
    library_rows = [
        {"kod": "AA-1", "typ": "front", "nazwa": "Front test", "producent": "X", "parametry": "P", "grubosc": "18", "cena_zl": "350"}
    ]
    material_rows = [
        {"row": "0", "typ": "front", "nazwa": "Front test", "producent": "X", "parametry": "P [KOD:AA-1]", "cena_zl": "300"},
        {"row": "1", "typ": "front", "nazwa": "Front test", "producent": "X", "parametry": "P", "cena_zl": "300"},
    ]

    updated_rows, updated_count = service.update_material_prices(material_rows, library_rows)
    assert updated_count == 2
    assert updated_rows[0]["cena_zl"] == "350"
    assert updated_rows[1]["cena_zl"] == "350"
