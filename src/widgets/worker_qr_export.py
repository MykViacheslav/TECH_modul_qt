from __future__ import annotations

import base64
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QByteArray, QBuffer, QIODevice
from PyQt6.QtGui import QDesktopServices, QTextDocument
from PyQt6.QtGui import QPageLayout, QPageSize
from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtCore import QUrl

from src.domain.worker_models import WorkerDef
from src.storage.data_paths import data_dir
from src.widgets.qr_utils import qr_pixmap_from_text, worker_qr_payload


def _pixmap_to_data_uri(text: str, size: int = 260) -> str:
    pixmap = qr_pixmap_from_text(text, size=size)
    buffer = QByteArray()
    qbuffer = QBuffer(buffer)
    qbuffer.open(QIODevice.OpenModeFlag.WriteOnly)
    pixmap.save(qbuffer, "PNG")
    qbuffer.close()
    encoded = base64.b64encode(bytes(buffer)).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _safe_text(value: object) -> str:
    return str(value or "").strip()


def build_workers_qr_html(workers: list[WorkerDef]) -> str:
    cards = []
    for index, worker in enumerate(workers, start=1):
        name = _safe_text(getattr(worker, "name", "") or "Pracownik")
        worker_id = _safe_text(getattr(worker, "worker_id", "") or "-")
        pin_code = _safe_text(getattr(worker, "pin_code", "") or "-")
        role = _safe_text(getattr(worker, "role", "") or "-")
        payload = worker_qr_payload(worker_id, name)
        qr_uri = _pixmap_to_data_uri(payload, size=260)
        cards.append(
            f"""
            <section class="card">
              <div class="card-head">
                <div>
                  <div class="name">{name}</div>
                  <div class="meta">ID: {worker_id} &nbsp;|&nbsp; PIN: {pin_code}</div>
                  <div class="meta">Rola: {role}</div>
                </div>
                <div class="number">#{index}</div>
              </div>
              <div class="body">
                <img src="{qr_uri}" alt="QR {name}" />
                <div class="payload">{payload}</div>
              </div>
            </section>
            """
        )

    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    if not cards:
        pages_html = """
        <section class="page">
          <div class="header">
            <h1>Karty QR pracowników</h1>
            <div class="stamp">Wygenerowano: {now}</div>
          </div>
          <div class="empty">Brak pracowników do eksportu.</div>
        </section>
        """.format(now=now)
    else:
        pages = [cards[i:i + 2] for i in range(0, len(cards), 2)]
        page_parts = []
        for page_cards in pages:
            page_parts.append(
                """
                <section class="page">
                  <div class="header">
                    <h1>Karty QR pracowników</h1>
                    <div class="stamp">Wygenerowano: {now}</div>
                  </div>
                  <div class="cards">
                    {cards}
                  </div>
                </section>
                """.format(now=now, cards="".join(page_cards))
            )
        pages_html = "".join(page_parts)

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
        .page {{
          break-after: page;
        }}
        .page:last-child {{
          break-after: auto;
        }}
        .cards {{
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 10mm;
        }}
        .card {{
          border: 1px solid #c7d2e3;
          border-radius: 16px;
          padding: 14px;
          min-height: 125mm;
          box-sizing: border-box;
        }}
        .card-head {{
          display: flex;
          justify-content: space-between;
          gap: 10px;
          align-items: start;
          margin-bottom: 12px;
        }}
        .name {{
          font-size: 20px;
          font-weight: 800;
          margin-bottom: 4px;
        }}
        .meta {{
          font-size: 12px;
          color: #4b5563;
          line-height: 1.35;
        }}
        .number {{
          font-size: 12px;
          color: #64748b;
          font-weight: 700;
        }}
        .body {{
          display: grid;
          grid-template-columns: 1fr;
          justify-items: center;
          gap: 10px;
        }}
        img {{
          width: 70mm;
          height: 70mm;
          border: 1px solid #dbe4ee;
          background: #fff;
        }}
        .payload {{
          font-size: 10px;
          color: #475569;
          word-break: break-all;
          text-align: center;
          padding: 6px 8px;
          border: 1px dashed #dbe4ee;
          border-radius: 10px;
          width: 100%;
          box-sizing: border-box;
        }}
        .empty {{
          padding: 20px;
          font-size: 18px;
          color: #64748b;
        }}
        .header {{
          grid-column: 1 / -1;
          margin-bottom: 4mm;
          display: flex;
          justify-content: space-between;
          align-items: end;
          border-bottom: 2px solid #2b6cb0;
          padding-bottom: 4mm;
        }}
        .header h1 {{
          margin: 0;
          font-size: 22px;
          color: #1a365d;
        }}
        .header .stamp {{
          font-size: 11px;
          color: #64748b;
        }}
      </style>
    </head>
    <body>
      {pages_html}
    </body>
    </html>
    """


def export_workers_qr_pdf(workers: list[WorkerDef], output_path: str | Path) -> Path:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(str(target))
    printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    printer.setPageOrientation(QPageLayout.Orientation.Landscape)

    document = QTextDocument()
    document.setHtml(build_workers_qr_html(workers))
    document.print(printer)
    return target


def default_workers_qr_export_dir() -> Path:
    target = data_dir() / "qr_workers"
    target.mkdir(parents=True, exist_ok=True)
    return target


def export_workers_qr_pdf_to_default_folder(workers: list[WorkerDef]) -> Path:
    safe_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = default_workers_qr_export_dir() / f"workers_qr_{safe_stamp}.pdf"
    return export_workers_qr_pdf(workers, output)


def open_workers_qr_export_dir() -> bool:
    target = default_workers_qr_export_dir()
    return QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))
