from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QFileDialog,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.domain.worker_models import WorkerDef
from src.widgets.qr_utils import qr_pixmap_from_text, save_qr_pixmap_to_path, build_worker_qr_payload

def worker_qr_payload(worker_id: str, worker_name: str = "", bot_username: str = "") -> str:
    return build_worker_qr_payload(worker_id, worker_name, bot_username=bot_username)


class WorkerQrDialog(QDialog):
    def __init__(self, worker: WorkerDef, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._worker = worker
        from src.app.app_settings import load_telegram_settings
        t_settings = load_telegram_settings()
        bot_uname = t_settings.bot_username if t_settings.enabled else ""
        
        self._payload = worker_qr_payload(
            str(getattr(worker, "worker_id", "") or ""),
            str(getattr(worker, "name", "") or ""),
            bot_username=bot_uname
        )

        self.setWindowTitle("Karta QR pracownika")
        self.setModal(True)
        self.setMinimumSize(420, 520)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        title = QLabel(str(getattr(worker, "name", "") or "Pracownik"), self)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: 900; color:#10233f;")
        root.addWidget(title)

        details = QLabel(
            f"ID: {getattr(worker, 'worker_id', '') or '-'}\n"
            f"PIN: {getattr(worker, 'pin_code', '') or '-'}\n"
            f"Rola: {getattr(worker, 'role', '') or '-'}",
            self,
        )
        details.setAlignment(Qt.AlignmentFlag.AlignCenter)
        details.setStyleSheet("color:#4b5563; font-size: 13px;")
        root.addWidget(details)

        self.lab_qr = QLabel(self)
        self.lab_qr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lab_qr.setPixmap(qr_pixmap_from_text(self._payload, size=300))
        root.addWidget(self.lab_qr, 0, Qt.AlignmentFlag.AlignCenter)

        self.lab_payload = QLabel(self._payload, self)
        self.lab_payload.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lab_payload.setWordWrap(True)
        self.lab_payload.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.lab_payload.setStyleSheet(
            "background:#f8fafc; border:1px solid #dbe4ee; border-radius:10px; padding:10px; color:#334155;"
        )
        root.addWidget(self.lab_payload)

        buttons = QHBoxLayout()
        self.btn_copy = QPushButton("Kopiuj kod", self)
        self.btn_save = QPushButton("Zapisz PNG", self)
        self.btn_close = QPushButton("Zamknij", self)
        buttons.addWidget(self.btn_copy)
        buttons.addWidget(self.btn_save)
        buttons.addWidget(self.btn_close)
        root.addLayout(buttons)

        self.btn_copy.clicked.connect(self._copy_payload)
        self.btn_save.clicked.connect(self._save_png)
        self.btn_close.clicked.connect(self.accept)

    def _copy_payload(self) -> None:
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self._payload)

    def _save_png(self) -> None:
        default_name = f"{getattr(self._worker, 'worker_id', '') or 'worker'}_qr.png"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Zapisz QR pracownika",
            default_name,
            "PNG (*.png)",
        )
        if not file_path:
            return
        save_qr_pixmap_to_path(self._payload, file_path, size=300)
