from __future__ import annotations

from PyQt6.QtWidgets import QApplication


def test_worker_qr_pdf_export_creates_file(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.worker_models import WorkerDef
    from src.widgets.worker_qr_export import export_workers_qr_pdf

    workers = [
        WorkerDef(name="Jan Kowalski", worker_id="W001", pin_code="246810", role="Produkcja"),
        WorkerDef(name="Anna Nowak", worker_id="W002", pin_code="135790", role="Magazyn"),
    ]

    out_path = export_workers_qr_pdf(workers, tmp_path / "workers_qr.pdf")

    assert out_path.exists()
    assert out_path.stat().st_size > 0


def test_worker_qr_pdf_export_creates_file_in_default_folder(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.worker_models import WorkerDef
    from src.widgets.worker_qr_export import export_workers_qr_pdf_to_default_folder

    workers = [
        WorkerDef(name="Jan Kowalski", worker_id="W001", pin_code="246810", role="Produkcja"),
    ]

    out_path = export_workers_qr_pdf_to_default_folder(workers)

    assert out_path.exists()
    assert out_path.parent.name == "qr_workers"
    assert out_path.stat().st_size > 0
