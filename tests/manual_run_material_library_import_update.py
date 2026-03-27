from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.tabs.baza_materialu.tab_baza_materialu import TabBazaMaterialu


def run() -> None:
    data_dir = Path(os.environ.get("TECH_MODUL_DATA_DIR", "").strip() or "")
    if not data_dir:
        data_dir = Path.cwd() / "tmp_mat_import_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ["TECH_MODUL_DATA_DIR"] = str(data_dir)
    os.environ["TECH_MODUL_TESTING"] = "1"

    app = QApplication.instance() or QApplication([])
    w = TabBazaMaterialu()

    csv_path = data_dir / "import_producent.csv"
    csv_path.write_text(
        "SKU;Nazwa handlowa;Producent;Rodzaj;Spec;Grubosc mm;Cena netto\n"
        "TS-001;Test Swiss Front;Swisskrono;front;U190 PE;18;299\n",
        encoding="utf-8",
    )

    headers, rows = w._load_rows_from_csv_or_tsv(csv_path)
    w._import_headers = headers
    w._import_rows = rows
    w._import_mapping = {
        "kod": "SKU",
        "nazwa": "Nazwa handlowa",
        "producent": "Producent",
        "typ": "Rodzaj",
        "parametry": "Spec",
        "grubosc": "Grubosc mm",
        "cena_zl": "Cena netto",
    }

    mapped = w._rows_from_import_buffer()
    added = w._merge_import_rows_into_library(mapped)
    print("imported into library:", added)
    assert added == 1

    imported = [r for r in w._producer_library_rows if str(r.get("kod", "")) == "TS-001"]
    assert imported
    w._import_library_rows(imported)
    base_rows = [
        (w._row_col_text(r, 1), w._row_col_text(r, 2), w._row_col_text(r, 8), w._row_col_text(r, 7))
        for r in range(w.tbl.rowCount())
    ]
    print("base rows after import:", len(base_rows))
    assert any(name == "Test Swiss Front" for _typ, name, _price, _param in base_rows)

    for item in w._producer_library_rows:
        if str(item.get("kod", "")) == "TS-001":
            item["cena_zl"] = "349"
    w._update_existing_material_prices_from_library()

    updated_rows = [
        (w._row_col_text(r, 2), w._row_col_text(r, 8))
        for r in range(w.tbl.rowCount())
    ]
    assert any(name == "Test Swiss Front" and price == "349" for name, price in updated_rows)
    print("update prices from library: OK")

    w.close()
    app.processEvents()


if __name__ == "__main__":
    run()
