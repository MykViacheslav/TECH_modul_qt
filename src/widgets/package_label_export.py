from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QRect, QSize, QSizeF, Qt
from PyQt6.QtGui import QColor, QFont, QPageLayout, QPageSize, QPainter, QPen, QPixmap
from PyQt6.QtPrintSupport import QPrinter

from src.storage.data_paths import data_dir
from src.widgets.qr_utils import qr_pixmap_from_text


@dataclass
class PackageLabelData:
    client_name: str
    order_code: str
    order_id: str = ""
    room_name: str = ""
    item_name: str = ""
    package_index: int = 1
    package_total: int = 1
    note: str = ""

    def safe_package_index(self) -> int:
        return max(1, int(self.package_index or 1))

    def safe_package_total(self) -> int:
        return max(1, int(self.package_total or 1))


def get_default_package_label_export_dir() -> Path:
    output = data_dir() / "labels"
    output.mkdir(parents=True, exist_ok=True)
    return output


def build_package_qr_payload(label: PackageLabelData) -> str:
    order_code = str(label.order_code or "").strip()
    order_id = str(label.order_id or "").strip()
    client_name = str(label.client_name or "").strip()
    room_name = str(label.room_name or "").strip()
    item_name = str(label.item_name or "").strip()
    package_index = label.safe_package_index()
    package_total = label.safe_package_total()
    package_code = f"{package_index:02d}/{package_total:02d}"
    return (
        "TECH_PACK"
        f"|ORDER_CODE={order_code}"
        f"|ORDER_ID={order_id}"
        f"|CLIENT={client_name}"
        f"|ROOM={room_name}"
        f"|ITEM={item_name}"
        f"|PACK={package_code}"
    )


def _fit_qr(payload: str, target_size: int) -> QPixmap:
    source_size = max(360, target_size * 2)
    source = qr_pixmap_from_text(payload, size=source_size)
    if source.isNull():
        return source
    return source.scaled(
        QSize(target_size, target_size),
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def _draw_label_page(painter: QPainter, printer: QPrinter, label: PackageLabelData) -> None:
    page_rect = printer.pageRect(QPrinter.Unit.DevicePixel)
    margin = max(12, int(min(page_rect.width(), page_rect.height()) * 0.035))
    content = page_rect.adjusted(margin, margin, -margin, -margin)

    painter.fillRect(page_rect, QColor("#ffffff"))
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    border_pen = QPen(QColor("#1e293b"))
    border_pen.setWidth(max(1, int(content.width() * 0.003)))
    painter.setPen(border_pen)
    painter.drawRect(content)

    inner = max(10, int(content.width() * 0.03))
    x = int(content.left()) + inner
    y = int(content.top()) + inner
    w = int(content.width()) - inner * 2
    h = int(content.height()) - inner * 2

    package_index = label.safe_package_index()
    package_total = label.safe_package_total()
    payload = build_package_qr_payload(label)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    header_h = max(34, int(h * 0.11))
    meta_h = max(110, int(h * 0.27))
    qr_size = max(180, min(int(h * 0.38), int(w * 0.80)))
    note_h = max(34, int(h * 0.08))
    footer_h = max(48, h - header_h - meta_h - qr_size - note_h - (inner // 2) * 4)

    title_font = QFont("Arial")
    title_font.setBold(True)
    title_font.setPixelSize(max(18, int(w * 0.085)))
    painter.setFont(title_font)
    painter.setPen(QColor("#0f172a"))
    painter.drawText(
        QRect(x, y, int(w * 0.7), header_h),
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        f"PACZKA {package_index}/{package_total}",
    )

    stamp_font = QFont("Arial")
    stamp_font.setPixelSize(max(11, int(w * 0.038)))
    painter.setFont(stamp_font)
    painter.setPen(QColor("#475569"))
    painter.drawText(
        QRect(x + int(w * 0.35), y, int(w * 0.65), header_h),
        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        generated_at,
    )
    y += header_h + max(4, inner // 3)

    meta_rect = QRect(x, y, w, meta_h)
    painter.setPen(QColor("#94a3b8"))
    painter.drawRect(meta_rect)
    meta_font = QFont("Arial")
    meta_font.setPixelSize(max(12, int(w * 0.042)))
    painter.setFont(meta_font)
    painter.setPen(QColor("#0f172a"))
    meta_lines = [
        f"Klient: {str(label.client_name or '').strip() or '-'}",
        f"Zamowienie: {str(label.order_code or '').strip() or '-'}",
        f"ID: {str(label.order_id or '').strip() or '-'}",
        f"Pomieszczenie: {str(label.room_name or '').strip() or '-'}",
        f"Wyrob: {str(label.item_name or '').strip() or '-'}",
    ]
    line_h = max(18, int(meta_rect.height() / 5))
    for idx, line in enumerate(meta_lines):
        painter.drawText(
            QRect(meta_rect.left() + 8, meta_rect.top() + idx * line_h, meta_rect.width() - 16, line_h),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            line,
        )
    y += meta_h + max(4, inner // 3)

    qr_rect = QRect(x + (w - qr_size) // 2, y, qr_size, qr_size)
    painter.setPen(QColor("#dbe2ea"))
    painter.drawRect(qr_rect)
    qr_pix = _fit_qr(payload, qr_size - 6)
    if not qr_pix.isNull():
        target = QRect(qr_rect.left() + 3, qr_rect.top() + 3, qr_rect.width() - 6, qr_rect.height() - 6)
        painter.drawPixmap(target, qr_pix)
    y += qr_size + max(4, inner // 3)

    note_rect = QRect(x, y, w, note_h)
    note_pen = QPen(QColor("#94a3b8"))
    note_pen.setStyle(Qt.PenStyle.DashLine)
    painter.setPen(note_pen)
    painter.drawRect(note_rect)
    note_font = QFont("Arial")
    note_font.setPixelSize(max(11, int(w * 0.038)))
    painter.setFont(note_font)
    painter.setPen(QColor("#334155"))
    painter.drawText(
        note_rect.adjusted(8, 2, -8, -2),
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap,
        str(label.note or "").strip() or " ",
    )
    y += note_h + max(4, inner // 3)

    payload_rect = QRect(x, y, w, footer_h)
    payload_font = QFont("Arial")
    payload_font.setPixelSize(max(9, int(w * 0.03)))
    painter.setFont(payload_font)
    painter.setPen(QColor("#64748b"))
    painter.drawText(
        payload_rect,
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap,
        payload,
    )


def export_package_labels_pdf(labels: list[PackageLabelData], output_path: str | Path) -> Path:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(str(target))
    printer.setPageSize(QPageSize(QSizeF(60.0, 100.0), QPageSize.Unit.Millimeter, "TECH_Label_60x100"))
    printer.setPageOrientation(QPageLayout.Orientation.Portrait)
    printer.setFullPage(True)

    export_labels = list(labels or [])
    if not export_labels:
        export_labels = [PackageLabelData(client_name="-", order_code="-", item_name="Brak etykiety")]

    painter = QPainter()
    if not painter.begin(printer):
        raise RuntimeError("Nie udalo sie rozpoczac druku PDF etykiet.")
    try:
        for index, label in enumerate(export_labels):
            if index > 0:
                printer.newPage()
            _draw_label_page(painter, printer, label)
    finally:
        painter.end()
    return target
