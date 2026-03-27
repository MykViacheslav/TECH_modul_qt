from __future__ import annotations

from PyQt6.QtWidgets import QApplication


def test_worker_qr_can_be_saved_as_png(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.widgets.qr_utils import save_qr_pixmap_to_path, worker_qr_payload

    payload = worker_qr_payload("W001", "Jan Kowalski")
    out_path = save_qr_pixmap_to_path(payload, tmp_path / "worker_qr.png", size=240)

    assert out_path.exists()
    assert out_path.stat().st_size > 0
