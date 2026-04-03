from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path

from PyQt6.QtGui import QTextDocument, QPageLayout, QPageSize
from PyQt6.QtPrintSupport import QPrinter

from src.domain.shopping_models import ShoppingItemDef
from src.storage.data_paths import data_dir


def _safe(value: object) -> str:
    return html.escape(str(value or "").strip())


def _money(value: float) -> str:
    try:
        v = float(value or 0.0)
    except Exception:
        v = 0.0
    return f"{v:,.2f} zl".replace(",", " ").replace(".", ",").replace(" ", ".")


def default_shopping_pdf_path() -> Path:
    export_dir = data_dir() / "export" / "pdf"
    export_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return export_dir / f"lista_zakupow_{stamp}.pdf"


def export_shopping_list_pdf(items: list[ShoppingItemDef], output_path: str | Path | None = None) -> Path:
    target = Path(output_path) if output_path else default_shopping_pdf_path()
    target.parent.mkdir(parents=True, exist_ok=True)

    rows_html: list[str] = []
    total_estimate = 0.0
    for idx, item in enumerate(items, start=1):
        est = float(getattr(item, "price_estimate", 0.0) or 0.0)
        qty = float(getattr(item, "quantity_needed", 0.0) or 0.0)
        total_estimate += est * max(qty, 0.0)
        rows_html.append(
            "<tr>"
            f"<td>{idx}</td>"
            f"<td>{_safe(item.item_id)}</td>"
            f"<td>{_safe(item.material_name)}</td>"
            f"<td style='text-align:right'>{qty:.2f}</td>"
            f"<td>{_safe(item.unit)}</td>"
            f"<td>{_safe(item.status)}</td>"
            f"<td>{_safe(item.supplier)}</td>"
            f"<td style='text-align:right'>{_money(est)}</td>"
            f"<td>{_safe(item.notes)}</td>"
            "</tr>"
        )

    if not rows_html:
        rows_html.append("<tr><td colspan='9'><i>Brak pozycji na liscie zakupow.</i></td></tr>")

    now_label = datetime.now().strftime("%Y-%m-%d %H:%M")
    html_body = f"""
    <html>
    <head>
      <meta charset="utf-8" />
      <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #0f172a; font-size: 10pt; }}
        h1 {{ font-size: 18pt; color: #1d4ed8; margin: 0 0 8pt 0; }}
        .meta {{ color: #475569; margin-bottom: 10pt; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ background: #1e293b; color: #fff; padding: 6px; font-size: 9pt; text-align: left; }}
        td {{ border-bottom: 1px solid #e2e8f0; padding: 5px; font-size: 9pt; vertical-align: top; }}
        tr:nth-child(even) {{ background: #f8fafc; }}
        .sum {{ margin-top: 10pt; font-weight: 700; color: #0f172a; }}
      </style>
    </head>
    <body>
      <h1>Lista zakupow</h1>
      <div class="meta">Wygenerowano: {now_label}</div>
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>ID</th>
            <th>Material</th>
            <th>Ilosc</th>
            <th>Jedn.</th>
            <th>Status</th>
            <th>Dostawca</th>
            <th>Cena szac.</th>
            <th>Uwagi</th>
          </tr>
        </thead>
        <tbody>
          {''.join(rows_html)}
        </tbody>
      </table>
      <div class="sum">Szacowany koszt calkowity: {_money(total_estimate)}</div>
    </body>
    </html>
    """

    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(str(target))
    printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    printer.setPageOrientation(QPageLayout.Orientation.Portrait)

    doc = QTextDocument()
    doc.setHtml(html_body)
    doc.print(printer)
    return target
