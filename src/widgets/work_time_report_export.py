from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PyQt6.QtGui import QPageLayout, QPageSize, QTextDocument
from PyQt6.QtPrintSupport import QPrinter

from src.domain.work_time_costing import compute_work_time_cost
from src.domain.work_time_models import WorkerMonthSheetDef
from src.domain.worker_models import WorkerDef
from src.storage.data_paths import data_dir


def _safe_text(value: object) -> str:
    return str(value or "").strip()


def _format_pln(value: float) -> str:
    try:
        amount = float(value)
    except Exception:
        amount = 0.0
    return f"{amount:.2f} PLN"


def _format_float(value: float, decimals: int = 2) -> str:
    try:
        amount = float(value)
    except Exception:
        amount = 0.0
    return f"{amount:.{decimals}f}"


def _safe_filename_part(value: str) -> str:
    text = str(value or "").strip()
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_", " ") else "_" for ch in text)
    cleaned = "_".join(part for part in cleaned.split() if part)
    return cleaned or "pracownik"


def build_worker_month_report_html(worker: WorkerDef, sheet: WorkerMonthSheetDef, breakdown) -> str:
    entries = sorted(sheet.entries, key=lambda entry: int(getattr(entry, "day", 0) or 0))
    rows_html: list[str] = []
    for entry in entries:
        rows_html.append(
            """
            <tr>
              <td>{day}</td>
              <td>{date_iso}</td>
              <td>{work_type}</td>
              <td>{start_time}</td>
              <td>{end_time}</td>
              <td class="num">{hours}</td>
              <td class="num">{overtime}</td>
              <td class="num">{extra}</td>
              <td>{note}</td>
            </tr>
            """.format(
                day=int(getattr(entry, "day", 0) or 0) or "",
                date_iso=_safe_text(getattr(entry, "date_iso", "") or ""),
                work_type=_safe_text(getattr(entry, "work_type", "") or ""),
                start_time=_safe_text(getattr(entry, "start_time", "") or ""),
                end_time=_safe_text(getattr(entry, "end_time", "") or ""),
                hours=_format_float(float(getattr(entry, "hours", 0.0) or 0.0)),
                overtime=_format_float(float(getattr(entry, "overtime_hours", 0.0) or 0.0)),
                extra=_format_pln(float(getattr(entry, "extra_pay", 0.0) or 0.0)),
                note=_safe_text(getattr(entry, "note", "") or ""),
            )
        )

    if not rows_html:
        rows_html.append(
            """
            <tr>
              <td colspan="9" class="empty">Brak wpisów w wybranym miesiącu.</td>
            </tr>
            """
        )

    worker_name = _safe_text(getattr(worker, "name", "") or sheet.worker_name or "Pracownik")
    worker_id = _safe_text(getattr(worker, "worker_id", "") or "")
    pin_code = _safe_text(getattr(worker, "pin_code", "") or "")
    pay_mode = _safe_text(getattr(worker, "pay_mode", "") or "Godzinowa") or "Godzinowa"
    hourly_rate = float(getattr(worker, "hourly_rate", 0.0) or 0.0)
    daily_rate = float(getattr(worker, "daily_rate", 0.0) or 0.0)
    year = int(getattr(sheet, "year", 0) or 0)
    month = int(getattr(sheet, "month", 0) or 0)
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    return f"""
    <!doctype html>
    <html lang="pl">
    <head>
      <meta charset="utf-8">
      <style>
        @page {{
          size: A4 landscape;
          margin: 12mm;
        }}
        body {{
          font-family: Arial, sans-serif;
          color: #10233f;
          margin: 0;
          padding: 0;
          background: #fff;
        }}
        .header {{
          display: flex;
          justify-content: space-between;
          gap: 12px;
          align-items: flex-end;
          border-bottom: 2px solid #2b6cb0;
          padding-bottom: 8px;
          margin-bottom: 12px;
        }}
        .header h1 {{
          margin: 0;
          font-size: 22px;
          color: #1a365d;
        }}
        .stamp {{
          font-size: 11px;
          color: #64748b;
        }}
        .meta {{
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 8px;
          margin-bottom: 12px;
        }}
        .card {{
          border: 1px solid #dbe4ee;
          border-radius: 12px;
          padding: 10px 12px;
          background: #f8fbff;
        }}
        .card .label {{
          color: #64748b;
          font-size: 11px;
          margin-bottom: 4px;
        }}
        .card .value {{
          font-size: 18px;
          font-weight: 800;
          color: #0f172a;
        }}
        .details {{
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 8px 16px;
          margin-bottom: 12px;
          font-size: 12px;
          color: #334155;
        }}
        .details strong {{
          color: #0f172a;
        }}
        table {{
          width: 100%;
          border-collapse: collapse;
          font-size: 10.5px;
        }}
        th, td {{
          border: 1px solid #d8e2ec;
          padding: 6px 7px;
          vertical-align: top;
        }}
        th {{
          background: #edf4ff;
          font-size: 10px;
          text-transform: uppercase;
          letter-spacing: 0.03em;
          color: #334155;
        }}
        .num {{
          text-align: right;
          white-space: nowrap;
        }}
        .empty {{
          text-align: center;
          color: #64748b;
          padding: 16px;
        }}
        .footer-box {{
          margin-top: 12px;
          border: 1px solid #dbe4ee;
          border-radius: 12px;
          padding: 10px 12px;
          background: #fcfdff;
          font-size: 11px;
          color: #334155;
        }}
      </style>
    </head>
    <body>
      <div class="header">
        <div>
          <h1>Raport czasu pracy pracownika</h1>
          <div class="stamp">Wygenerowano: {now}</div>
        </div>
        <div class="stamp">Miesiąc: {year:04d}-{month:02d}</div>
      </div>

      <div class="meta">
        <div class="card">
          <div class="label">Pracownik</div>
          <div class="value">{worker_name}</div>
        </div>
        <div class="card">
          <div class="label">Godziny</div>
          <div class="value">{_format_float(float(getattr(breakdown, "total_hours", 0.0) or 0.0))}</div>
        </div>
        <div class="card">
          <div class="label">Nadgodziny</div>
          <div class="value">{_format_float(float(getattr(breakdown, "overtime_hours", 0.0) or 0.0))}</div>
        </div>
        <div class="card">
          <div class="label">Do wypłaty</div>
          <div class="value">{_format_pln(float(getattr(breakdown, "total_cost", 0.0) or 0.0))}</div>
        </div>
      </div>

      <div class="details">
        <div><strong>ID:</strong> {worker_id or "-"}</div>
        <div><strong>PIN:</strong> {pin_code or "-"}</div>
        <div><strong>Tryb rozliczenia:</strong> {pay_mode}</div>
        <div><strong>Stawka godzinowa:</strong> {_format_pln(hourly_rate)}</div>
        <div><strong>Dniowka:</strong> {_format_pln(daily_rate)}</div>
        <div><strong>Wpisy dni:</strong> {int(getattr(breakdown, "tracked_days", 0) or 0)}</div>
      </div>

      <table>
        <thead>
          <tr>
            <th>Dzień</th>
            <th>Data</th>
            <th>Rodzaj pracy</th>
            <th>Od</th>
            <th>Do</th>
            <th>Godz.</th>
            <th>Ndg.</th>
            <th>Dodatki</th>
            <th>Notatka</th>
          </tr>
        </thead>
        <tbody>
          {''.join(rows_html)}
        </tbody>
      </table>

      <div class="footer-box">
        Baza: {_format_pln(float(getattr(breakdown, "base_total", 0.0) or 0.0))} |
        Nadgodziny: {_format_pln(float(getattr(breakdown, "overtime_total", 0.0) or 0.0))} |
        Dodatki etapów: {_format_pln(float(getattr(breakdown, "stage_extra_total", 0.0) or 0.0))} |
        Dodatki ręczne: {_format_pln(float(getattr(breakdown, "manual_extra_total", 0.0) or 0.0))} |
        Razem: {_format_pln(float(getattr(breakdown, "total_cost", 0.0) or 0.0))}
      </div>
    </body>
    </html>
    """


def default_worker_month_report_dir() -> Path:
    target = data_dir() / "work_time_reports"
    target.mkdir(parents=True, exist_ok=True)
    return target


def export_worker_month_report_pdf(
    worker: WorkerDef,
    sheet: WorkerMonthSheetDef,
    output_path: str | Path,
) -> Path:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    workers_by_name = {str(sheet.worker_name or "").strip(): worker}
    breakdown = compute_work_time_cost([sheet], workers_by_name)

    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(str(target))
    printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    printer.setPageOrientation(QPageLayout.Orientation.Landscape)

    document = QTextDocument()
    document.setHtml(build_worker_month_report_html(worker, sheet, breakdown))
    document.print(printer)
    return target


def export_worker_month_report_pdf_to_default_folder(
    worker: WorkerDef,
    sheet: WorkerMonthSheetDef,
) -> Path:
    safe_name = _safe_filename_part(str(getattr(worker, "name", "") or "pracownik"))
    output = default_worker_month_report_dir() / f"report_{safe_name}_{int(sheet.year):04d}_{int(sheet.month):02d}.pdf"
    return export_worker_month_report_pdf(worker, sheet, output)
