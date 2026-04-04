from __future__ import annotations

from PyQt6.QtWidgets import QApplication


def test_worker_month_report_pdf_export_creates_file(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    app = QApplication.instance() or QApplication([])

    from src.domain.work_time_models import WorkTimeEntryDef, WorkerMonthSheetDef
    from src.domain.worker_models import WorkerDef
    from src.domain.work_time_costing import compute_work_time_cost
    from src.widgets.work_time_report_export import build_worker_month_report_html, export_worker_month_report_pdf

    worker = WorkerDef(
        name="Jan Kowalski",
        worker_id="W001",
        pin_code="246810",
        pay_mode="Godzinowa",
        hourly_rate=50.0,
        overtime_multiplier=1.0,
    )
    sheet = WorkerMonthSheetDef(
        sheet_id="SHEET1",
        worker_name="Jan Kowalski",
        year=2026,
        month=3,
        entries=[
            WorkTimeEntryDef(
                entry_id="E1",
                day=27,
                date_iso="2026-03-27",
                work_type="Produkcja",
                start_time="08:00",
                end_time="17:00",
                hours=8.0,
                overtime_hours=1.0,
                extra_pay=25.0,
                note="Test",
            )
        ],
    )

    breakdown = compute_work_time_cost([sheet], {"Jan Kowalski": worker})
    html = build_worker_month_report_html(worker, sheet, breakdown)
    assert "Jan Kowalski" in html
    assert "475.00 PLN" in html
    assert "8.00" in html

    out_path = export_worker_month_report_pdf(worker, sheet, tmp_path / "report.pdf")
    assert out_path.exists()
    assert out_path.stat().st_size > 0
