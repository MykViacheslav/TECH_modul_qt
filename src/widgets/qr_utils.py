from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPixmap
from pathlib import Path

from src.domain.worker_qr import build_worker_qr_payload

try:
    import qrcode
except Exception:  # pragma: no cover - optional dependency fallback
    qrcode = None  # type: ignore[assignment]


def worker_qr_payload(worker_id: str, worker_name: str = "") -> str:
    return build_worker_qr_payload(worker_id, worker_name)


def qr_pixmap_from_text(text: str, size: int = 280) -> QPixmap:
    text = str(text or "").strip()
    if not text:
        pixmap = QPixmap(size, size)
        pixmap.fill(QColor("#ffffff"))
        return pixmap

    if qrcode is None:
        return _fallback_pixmap(text, size=size)

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(text)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    return _matrix_to_pixmap(matrix, text, size=size)


def save_qr_pixmap_to_path(text: str, path: str | Path, size: int = 280) -> Path:
    """
    Render a QR pixmap and save it to disk as PNG.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    pixmap = qr_pixmap_from_text(text, size=size)
    pixmap.save(str(target), "PNG")
    return target


def _matrix_to_pixmap(matrix: list[list[bool]], text: str, size: int) -> QPixmap:
    count = len(matrix)
    if count <= 0:
        return _fallback_pixmap(text, size=size)

    pixmap = QPixmap(size, size)
    pixmap.fill(QColor("#ffffff"))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    margin = max(size // 18, 8)
    available = size - margin * 2
    module = max(1, available // count)
    draw_size = module * count
    offset = (size - draw_size) // 2

    painter.fillRect(0, 0, size, size, QColor("#ffffff"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#000000"))

    for y, row in enumerate(matrix):
        for x, value in enumerate(row):
            if value:
                painter.drawRect(offset + x * module, offset + y * module, module, module)

    painter.end()
    return pixmap


def _fallback_pixmap(text: str, size: int) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor("#ffffff"))
    painter = QPainter(pixmap)
    painter.fillRect(0, 0, size, size, QColor("#ffffff"))
    painter.setPen(QColor("#10233f"))
    font = QFont()
    font.setBold(True)
    font.setPointSize(max(10, size // 15))
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, text)
    painter.end()
    return pixmap
