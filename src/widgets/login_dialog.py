"""
Login dialog for TECH_modul workstation authentication.
Supports canonical RBAC roles from src.domain.permissions.
"""

from __future__ import annotations

from typing import Optional, Tuple

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QFont, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.domain.permissions import ROLE_LABELS, normalize_role
from src.domain.worker_models import WorkerDef
from src.storage.worker_store_json import WorkerStoreJson


# ---------------------------------------------------------------------------
# Kolory ról
# ---------------------------------------------------------------------------
_ROLE_COLORS: dict[str, tuple[str, str]] = {
    "wlasciciel": ("#1e3a5f", "#facc15"),   # granat + złoto
    "biuro":      ("#1e4d2b", "#86efac"),   # zieleń + jasna zieleń
    "produkcja":  ("#3b1f6b", "#c4b5fd"),   # fiolet + lawendowy
    "magazyn":    ("#7c2d12", "#fdba74"),   # brąz + pomarańcz
}
_DEFAULT_COLORS = ("#1e293b", "#94a3b8")


def _initials(worker: WorkerDef) -> str:
    fn = worker.get_first_name()
    ln = worker.get_last_name()
    if fn and ln:
        return (fn[0] + ln[0]).upper()
    name = str(worker.name or "").strip()
    parts = name.split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return name[:2].upper() if name else "?"


def _avatar_pixmap(worker: WorkerDef, size: int = 52) -> QPixmap:
    """Renderuje awatar z inicjałami pracownika."""
    role = normalize_role(str(worker.role or ""))
    bg_hex, fg_hex = _ROLE_COLORS.get(role, _DEFAULT_COLORS)

    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Koło tła
    p.setBrush(QColor(bg_hex))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(0, 0, size, size)

    # Inicjały
    p.setPen(QColor(fg_hex))
    font = QFont()
    font.setPixelSize(int(size * 0.38))
    font.setWeight(QFont.Weight.Bold)
    p.setFont(font)
    p.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, _initials(worker))
    p.end()
    return pm


# ---------------------------------------------------------------------------
# Kafelek jednego pracownika
# ---------------------------------------------------------------------------
class _WorkerTile(QToolButton):
    def __init__(self, worker: WorkerDef, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.worker = worker
        role = normalize_role(str(worker.role or ""))
        bg_hex, _ = _ROLE_COLORS.get(role, _DEFAULT_COLORS)
        role_label = ROLE_LABELS.get(role, role.capitalize() or "—")

        display_name = worker.get_first_name() or str(worker.name or "").split()[0] if str(worker.name or "").strip() else "—"
        last = worker.get_last_name()
        if last:
            display_name = f"{display_name}\n{last}"

        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        pm = _avatar_pixmap(worker, 52)
        from PyQt6.QtGui import QIcon
        self.setIcon(QIcon(pm))
        self.setIconSize(QSize(52, 52))
        self.setText(f"{display_name}\n{role_label}")
        self.setToolTip(f"{worker.name or '—'}  ·  {role_label}")
        self.setFixedSize(110, 110)

        # Subtelne podbarwienie tła roli (mieszanka bg_hex z ciemnym bazowym)
        # Obramowanie zawsze w kolorze roli
        bg_hex, accent = _ROLE_COLORS.get(role, _DEFAULT_COLORS)
        self.setStyleSheet(f"""
            QToolButton {{
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 {bg_hex}, stop:1 #0f172a
                );
                border: 2px solid {accent};
                border-radius: 12px;
                color: #e2e8f0;
                font-size: 10px;
                font-weight: 600;
                padding: 6px 4px 4px 4px;
            }}
            QToolButton:hover {{
                background: {bg_hex};
                border-color: {accent};
                border-width: 3px;
            }}
            QToolButton:pressed {{
                background: {bg_hex};
                border-color: #facc15;
                border-width: 3px;
            }}
        """)


# ---------------------------------------------------------------------------
# Panel PIN (numpad)
# ---------------------------------------------------------------------------
class _PinPanel(QWidget):
    pin_confirmed = pyqtSignal(str)   # emituje wpisany PIN
    cancelled = pyqtSignal()

    def __init__(self, worker: WorkerDef, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.worker = worker
        self._entered = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(10)

        # Kto się loguje
        role = normalize_role(str(worker.role or ""))
        role_label = ROLE_LABELS.get(role, role.capitalize())
        who = QLabel(f"{worker.name or '?'}\n{role_label}")
        who.setAlignment(Qt.AlignmentFlag.AlignCenter)
        who.setStyleSheet("color:#e2e8f0; font-size:13px; font-weight:600; line-height:1.4;")
        layout.addWidget(who)

        # Wyświetlacz PIN (gwiazdki)
        self._pin_display = QLabel("· · · · · ·")
        self._pin_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._pin_display.setStyleSheet(
            "color:#facc15; font-size:22px; letter-spacing:6px; padding:6px;"
            "background:#0f172a; border-radius:8px; border:1px solid #334155;"
        )
        self._pin_display.setFixedHeight(48)
        layout.addWidget(self._pin_display)

        # Numpad
        grid = QGridLayout()
        grid.setSpacing(8)
        digits = [("1","1"), ("2","2"), ("3","3"),
                  ("4","4"), ("5","5"), ("6","6"),
                  ("7","7"), ("8","8"), ("9","9"),
                  ("←","back"), ("0","0"), ("OK","ok")]
        for i, (label, val) in enumerate(digits):
            btn = QPushButton(label)
            btn.setFixedSize(60, 44)
            if val == "ok":
                btn.setStyleSheet(
                    "QPushButton{background:#15803d;color:#fff;border-radius:8px;"
                    "font-size:13px;font-weight:700;border:none;}"
                    "QPushButton:hover{background:#16a34a;}"
                )
            elif val == "back":
                btn.setStyleSheet(
                    "QPushButton{background:#374151;color:#e2e8f0;border-radius:8px;"
                    "font-size:16px;font-weight:700;border:none;}"
                    "QPushButton:hover{background:#4b5563;}"
                )
            else:
                btn.setStyleSheet(
                    "QPushButton{background:#1e293b;color:#e2e8f0;border-radius:8px;"
                    "font-size:15px;font-weight:600;border:1px solid #334155;}"
                    "QPushButton:hover{background:#334155;}"
                )
            btn.clicked.connect(lambda _, v=val: self._digit(v))
            grid.addWidget(btn, i // 3, i % 3)
        layout.addLayout(grid)

        # Anuluj
        btn_cancel = QPushButton("← Wróć")
        btn_cancel.setStyleSheet(
            "QPushButton{background:transparent;color:#64748b;border:none;"
            "font-size:11px;padding:4px;}"
            "QPushButton:hover{color:#94a3b8;}"
        )
        btn_cancel.clicked.connect(self.cancelled)
        layout.addWidget(btn_cancel, 0, Qt.AlignmentFlag.AlignCenter)

        self._update_display()

    def _digit(self, val: str) -> None:
        if val == "back":
            self._entered = self._entered[:-1]
        elif val == "ok":
            self.pin_confirmed.emit(self._entered)
            return
        else:
            if len(self._entered) < 8:
                self._entered += val
        self._update_display()

    def _update_display(self) -> None:
        if not self._entered:
            self._pin_display.setText("· · · · · ·")
        else:
            self._pin_display.setText("●" * len(self._entered))


# ---------------------------------------------------------------------------
# Główny dialog logowania
# ---------------------------------------------------------------------------
class LoginDialog(QDialog):
    """Ekran wyboru pracownika z opcjonalnym PIN."""

    login_success = pyqtSignal(str, str)   # worker_name, role

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("TECH_modul — Zaloguj się")
        self.setModal(True)
        self.setMinimumSize(520, 420)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setStyleSheet(
            "QDialog { background:#0f172a; border:2px solid #334155; border-radius:16px; }"
        )

        self._worker_store = WorkerStoreJson()
        self._logged_worker: WorkerDef | None = None
        self._logged_role: str = ""

        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(0)

        # Stack: strona wyboru / strona PIN
        self._page_select = self._build_select_page()
        self._page_pin: _PinPanel | None = None

        self._root.addWidget(self._page_select)

    # ------------------------------------------------------------------
    # Strona wyboru pracownika
    # ------------------------------------------------------------------
    def _build_select_page(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        vl = QVBoxLayout(page)
        vl.setContentsMargins(28, 24, 28, 20)
        vl.setSpacing(14)

        # Nagłówek
        hdr = QLabel("TECH_modul")
        hdr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hdr.setStyleSheet(
            "color:#f8fafc; font-size:22px; font-weight:800; letter-spacing:2px;"
        )
        vl.addWidget(hdr)

        sub = QLabel("Wybierz pracownika")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet("color:#64748b; font-size:12px;")
        vl.addWidget(sub)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("background:#1e293b; max-height:1px;")
        vl.addWidget(divider)

        # Siatka kafelków pracowników
        workers = self._load_workers()

        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        tile_container = QWidget()
        tile_container.setStyleSheet("background: transparent;")
        grid = QGridLayout(tile_container)
        grid.setSpacing(12)
        grid.setContentsMargins(8, 8, 8, 8)

        cols = 4
        if not workers:
            # Brak pracowników — pokaż kafelek gościa
            workers = [WorkerDef(name="admin", role="wlasciciel")]

        for idx, worker in enumerate(workers):
            tile = _WorkerTile(worker)
            tile.clicked.connect(lambda _, w=worker: self._on_worker_clicked(w))
            grid.addWidget(tile, idx // cols, idx % cols)

        # Elastyczne wypełnienie
        grid.setRowStretch(grid.rowCount(), 1)

        scroll.setWidget(tile_container)
        vl.addWidget(scroll, 1)

        # Stopka
        foot = QLabel("© TECH_modul ERP")
        foot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        foot.setStyleSheet("color:#1e293b; font-size:9px;")
        vl.addWidget(foot)

        return page

    def _load_workers(self) -> list[WorkerDef]:
        try:
            workers = self._worker_store.list_workers()
            # Filtruj puste/nieważne
            workers = [w for w in workers if str(w.name or "").strip()]
            # Sortuj: właściciel/biuro pierwsi, potem reszta alfabetycznie
            order = {"wlasciciel": 0, "biuro": 1, "produkcja": 2, "magazyn": 3}
            workers.sort(key=lambda w: (
                order.get(normalize_role(str(w.role or "")), 9),
                str(w.name or "").lower()
            ))
            return workers
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Kliknięcie w pracownika
    # ------------------------------------------------------------------
    def _on_worker_clicked(self, worker: WorkerDef) -> None:
        pin = str(worker.pin_code or "").strip()
        if pin:
            # Pracownik ma PIN — pokaż numpad
            self._show_pin_page(worker)
        else:
            # Brak PIN — loguj od razu
            self._do_login(worker)

    def _show_pin_page(self, worker: WorkerDef) -> None:
        if self._page_pin is not None:
            self._root.removeWidget(self._page_pin)
            self._page_pin.deleteLater()
            self._page_pin = None

        panel = _PinPanel(worker)
        panel.pin_confirmed.connect(lambda pin: self._check_pin(worker, pin))
        panel.cancelled.connect(self._back_to_select)

        self._page_select.setVisible(False)
        self._page_pin = panel
        self._root.addWidget(panel)

    def _back_to_select(self) -> None:
        if self._page_pin is not None:
            self._root.removeWidget(self._page_pin)
            self._page_pin.deleteLater()
            self._page_pin = None
        self._page_select.setVisible(True)

    def _check_pin(self, worker: WorkerDef, entered: str) -> None:
        expected = str(worker.pin_code or "").strip()
        if entered == expected:
            self._do_login(worker)
        else:
            self._shake_pin_display()

    def _shake_pin_display(self) -> None:
        """Krótka animacja błędu."""
        if self._page_pin is None:
            return
        disp = self._page_pin._pin_display
        orig = disp.styleSheet()
        disp.setStyleSheet(orig.replace("#facc15", "#ef4444"))
        QTimer.singleShot(400, lambda: disp.setStyleSheet(orig))
        self._page_pin._entered = ""
        self._page_pin._update_display()

    def _do_login(self, worker: WorkerDef) -> None:
        role = normalize_role(str(worker.role or "")) or "produkcja"
        self._logged_worker = worker
        self._logged_role = role
        self.login_success.emit(str(worker.name or ""), role)
        self.accept()

    # ------------------------------------------------------------------
    # Publiczne API (kompatybilne z istniejącym main.py)
    # ------------------------------------------------------------------
    def get_logged_in_worker(self) -> Tuple[str, str]:
        if self._logged_worker is None:
            return ("", "produkcja")
        name = str(self._logged_worker.name or "").strip()
        return (name, self._logged_role)


# ---------------------------------------------------------------------------
# QuickSwitchDialog — zmiana użytkownika w trakcie pracy
# ---------------------------------------------------------------------------
class QuickSwitchDialog(QDialog):
    """Szybka zmiana pracownika — pokazuje te same kafelki co LoginDialog."""

    worker_selected = pyqtSignal(str, str)   # worker_name, role

    def __init__(self, current_worker: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Zmień pracownika")
        self.setModal(True)
        self.setMinimumSize(480, 380)
        self.setStyleSheet(
            "QDialog { background:#0f172a; border:2px solid #334155; border-radius:14px; }"
        )
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint
        )

        self._current_worker = current_worker
        self._worker_store = WorkerStoreJson()
        self._page_pin: _PinPanel | None = None

        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)

        self._page_select = self._build_select_page()
        self._root.addWidget(self._page_select)

    def _build_select_page(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        vl = QVBoxLayout(page)
        vl.setContentsMargins(24, 20, 24, 16)
        vl.setSpacing(12)

        hdr = QLabel("Zmień pracownika")
        hdr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hdr.setStyleSheet("color:#f8fafc; font-size:16px; font-weight:700;")
        vl.addWidget(hdr)

        if self._current_worker:
            cur = QLabel(f"Teraz: {self._current_worker}")
            cur.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cur.setStyleSheet("color:#64748b; font-size:11px;")
            vl.addWidget(cur)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("background:#1e293b; max-height:1px;")
        vl.addWidget(divider)

        workers = self._load_workers()
        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        tile_container = QWidget()
        tile_container.setStyleSheet("background: transparent;")
        grid = QGridLayout(tile_container)
        grid.setSpacing(10)
        grid.setContentsMargins(4, 4, 4, 4)

        cols = 4
        for idx, worker in enumerate(workers):
            tile = _WorkerTile(worker)
            tile.clicked.connect(lambda _, w=worker: self._on_worker_clicked(w))
            grid.addWidget(tile, idx // cols, idx % cols)

        scroll.setWidget(tile_container)
        vl.addWidget(scroll, 1)

        btn_cancel = QPushButton("Anuluj")
        btn_cancel.setStyleSheet(
            "QPushButton{background:#1e293b;color:#94a3b8;border:1px solid #334155;"
            "border-radius:8px;padding:6px 20px;font-size:12px;}"
            "QPushButton:hover{background:#334155;}"
        )
        btn_cancel.clicked.connect(self.reject)
        vl.addWidget(btn_cancel, 0, Qt.AlignmentFlag.AlignCenter)

        return page

    def _load_workers(self) -> list[WorkerDef]:
        try:
            workers = self._worker_store.list_workers()
            workers = [w for w in workers if str(w.name or "").strip()]
            order = {"wlasciciel": 0, "biuro": 1, "produkcja": 2, "magazyn": 3}
            workers.sort(key=lambda w: (
                order.get(normalize_role(str(w.role or "")), 9),
                str(w.name or "").lower()
            ))
            return workers
        except Exception:
            return []

    def _on_worker_clicked(self, worker: WorkerDef) -> None:
        pin = str(worker.pin_code or "").strip()
        if pin:
            self._show_pin_page(worker)
        else:
            self._do_select(worker)

    def _show_pin_page(self, worker: WorkerDef) -> None:
        if self._page_pin is not None:
            self._root.removeWidget(self._page_pin)
            self._page_pin.deleteLater()
            self._page_pin = None

        panel = _PinPanel(worker)
        panel.pin_confirmed.connect(lambda pin: self._check_pin(worker, pin))
        panel.cancelled.connect(self._back_to_select)

        self._page_select.setVisible(False)
        self._page_pin = panel
        self._root.addWidget(panel)

    def _back_to_select(self) -> None:
        if self._page_pin is not None:
            self._root.removeWidget(self._page_pin)
            self._page_pin.deleteLater()
            self._page_pin = None
        self._page_select.setVisible(True)

    def _check_pin(self, worker: WorkerDef, entered: str) -> None:
        if entered == str(worker.pin_code or "").strip():
            self._do_select(worker)
        else:
            if self._page_pin:
                disp = self._page_pin._pin_display
                orig = disp.styleSheet()
                disp.setStyleSheet(orig.replace("#facc15", "#ef4444"))
                QTimer.singleShot(400, lambda: disp.setStyleSheet(orig))
                self._page_pin._entered = ""
                self._page_pin._update_display()

    def _do_select(self, worker: WorkerDef) -> None:
        role = normalize_role(str(worker.role or "")) or "produkcja"
        self.worker_selected.emit(str(worker.name or ""), role)
        self.accept()
