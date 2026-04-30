from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.app.app_settings import load_telegram_settings
from src.storage.order_store_json import OrderStoreJson
from src.storage.worker_store_json import WorkerStoreJson
from src.integrations.telegram_production_hub import (
    send_production_status_checklist,
    send_worker_attendance_poll
)
from src.services.telegram_hub_service import TelegramHubService
from src.integrations.telegram_checklist import _load_state, _save_state


@dataclass(frozen=True)
class _ScreenshotItem:
    title: str
    section: str
    path: Path


class _HeaderCard(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            """
            QFrame {
                background: #0f172a;
                border: 1px solid #e8efff;
                border-radius: 24px;
            }
            """
        )

        root = QHBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(16)

        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(6)

        title = QLabel("TECH_modul")
        title.setStyleSheet("color:#ffffff;font-size:30px;font-weight:900;")
        left.addWidget(title)

        subtitle = QLabel(
            "Zapisane screeny, porownania i materialy wizualne do konsultacji. "
            "To jest osobna wkładka na obrazki, zebysmy nie szukali ich po czacie."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color:#cbd5e1;font-size:13px;")
        left.addWidget(subtitle)

        chips = QHBoxLayout()
        chips.setContentsMargins(0, 2, 0, 0)
        chips.setSpacing(8)
        for text, bg, fg in (
            ("Start", "#dbeafe", "#1d4ed8"),
            ("Modul", "#dcfce7", "#166534"),
            ("Wycena", "#ffedd5", "#c2410c"),
            ("Sciana", "#ede9fe", "#6d28d9"),
            ("Telegram", "#fee2e2", "#b91c1c"),
        ):
            chip = QLabel(text)
            chip.setStyleSheet(
                f"background:{bg}; color:{fg}; border-radius:999px; padding:5px 11px; "
                "font-size:12px; font-weight:800;"
            )
            chips.addWidget(chip)
        chips.addStretch(1)
        left.addLayout(chips)
        root.addLayout(left, 3)

        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(8)
        for label, value, color in (
            ("Screeny", "20+", "#60a5fa"),
            ("Sekcje", "8", "#34d399"),
            ("Pliki lokalne", "100%", "#fbbf24"),
        ):
            card = QFrame(); card.setProperty("uiCard", True)
            card.setStyleSheet("QFrame{background:#111827;border:1px solid #243041;border-radius:16px;}")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(14, 12, 14, 12)
            card_layout.setSpacing(2)
            value_label = QLabel(value)
            value_label.setStyleSheet(f"color:{color};font-size:26px;font-weight:900;")
            card_layout.addWidget(value_label)
            label_widget = QLabel(label)
            label_widget.setStyleSheet("color:#cbd5e1;font-size:12px;font-weight:700;")
            card_layout.addWidget(label_widget)
            right.addWidget(card)
        root.addLayout(right, 1)


class _GuideCard(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            """
            QFrame {
                background: transparent;
                border: 1px solid #dbe4f0;
                border-radius: 20px;
            }
            """
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        title = QLabel("Co tu jest")
        title.setStyleSheet("color:#0f172a;font-size:18px;font-weight:900;")
        root.addWidget(title)

        for text, color in (
            ("Miniatury pomagaja szybko ocenic UI bez otwierania czata.", "#2563eb"),
            ("Kazdy kafel otwiera plik lokalny jednym kliknieciem.", "#059669"),
            ("Mozna filtrowac po sekcji: Modul, Sciana, Wycena, Kalendarz.", "#7c3aed"),
            ("To jest miejsce tylko na screeny i porownania wizualne.", "#d97706"),
        ):
            row = QLabel(f"• {text}")
            row.setWordWrap(True)
            row.setStyleSheet(f"color:{color};font-size:12px;font-weight:600;")
            root.addWidget(row)

        root.addStretch(1)


class _ScreenshotCard(QFrame):
    def __init__(self, item: _ScreenshotItem, on_open: Callable[[Path], None], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            """
            QFrame {
                background: transparent;
                border: 1px solid #dbe4f0;
                border-radius: 16px;
            }
            """
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(7)

        thumb = QLabel()
        thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb.setMinimumHeight(140)
        thumb.setStyleSheet("background:#0f172a;border-radius:10px;")

        pixmap = QPixmap(str(item.path))
        if pixmap.isNull():
            thumb.setText("Brak miniatury")
            thumb.setStyleSheet("background:#e2e8f0;color:#64748b;border-radius:10px;font-size:11px;")
        else:
            thumb.setPixmap(
                pixmap.scaled(
                    300,
                    140,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        root.addWidget(thumb)

        title = QLabel(item.title)
        title.setWordWrap(True)
        title.setStyleSheet("color:#0f172a;font-size:12px;font-weight:800;")
        root.addWidget(title)

        section = QLabel(item.section)
        section.setStyleSheet(
            "background:#eef2ff;color:#3730a3;border-radius:999px;padding:3px 9px;font-size:11px;font-weight:800;"
        )
        root.addWidget(section, 0, Qt.AlignmentFlag.AlignLeft)

        open_btn = QPushButton("Otworz plik")
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_btn.setStyleSheet(
            "QPushButton{background:#1d4ed8;color:#ffffff;font-weight:800;padding:7px 11px;border-radius:10px;}"
            "QPushButton:hover{background:#1e40af;}"
        )
        open_btn.clicked.connect(lambda _checked=False: on_open(item.path))
        root.addWidget(open_btn, 0, Qt.AlignmentFlag.AlignLeft)


class _TelegramHubPanel(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            """
            QFrame {
                background: #ffffff;
                border: 1px solid #dbe4f0;
                border-radius: 20px;
            }
            """
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        title = QLabel("TELEGRAM HUB")
        title.setStyleSheet("color:#111827;font-size:18px;font-weight:900;")
        root.addWidget(title)

        desc = QLabel("Zarzadzanie produkcja i czasem pracy przez Telegram.")
        desc.setStyleSheet("color:#6b7280;font-size:12px;")
        root.addWidget(desc)

        self.btn_prod_status = QPushButton("Wyslij Status Produkcji")
        self.btn_attendance = QPushButton("Wyslij Liste Obecnosci")
        self.btn_sync = QPushButton("Synchronizuj Dane")
        
        for btn, color in [
            (self.btn_prod_status, "#1e40af"),
            (self.btn_attendance, "#15803d"),
            (self.btn_sync, "#0f172a"),
        ]:
            btn.setStyleSheet(
                f"QPushButton{{background:{color};color:#ffffff;font-weight:800;padding:10px;border-radius:12px;}}"
                f"QPushButton:hover{{background:#111827;}}"
            )
            root.addWidget(btn)

        self.lab_status = QLabel("Oczekiwanie...")
        self.lab_status.setStyleSheet("color:#94a3b8;font-size:11px;font-weight:600;")
        root.addWidget(self.lab_status)

        self.btn_prod_status.clicked.connect(self._send_prod)
        self.btn_attendance.clicked.connect(self._send_attendance)
        self.btn_sync.clicked.connect(self._sync)

    def _send_prod(self) -> None:
        settings = load_telegram_settings()
        if not settings.enabled: return
        orders = OrderStoreJson().list_orders()
        try:
            send_production_status_checklist(settings.bot_token, settings.chat_id, orders)
            self.lab_status.setText("Wyslano status produkcji.")
        except Exception as e:
            self.lab_status.setText(f"Blad: {str(e)}")

    def _send_attendance(self) -> None:
        settings = load_telegram_settings()
        if not settings.enabled: return
        workers = WorkerStoreJson().list_workers()
        try:
            send_worker_attendance_poll(settings.bot_token, settings.chat_id, workers)
            self.lab_status.setText("Wyslano liste obecnosci.")
        except Exception as e:
            self.lab_status.setText(f"Blad: {str(e)}")

    def _sync(self) -> None:
        try:
            res = TelegramHubService.sync_all()
            if not res.get("ok"):
                self.lab_status.setText(f"Info: {res.get('message')}")
                return
            
            processed = res.get("processed", 0)
            db_upd = res.get("db_updates", 0)
            self.lab_status.setText(f"Sync OK: {processed} msg, {db_upd} zmian w bazie.")
        except Exception as e:
            self.lab_status.setText(f"Blad sync: {str(e)}")


class TabTechModul(QWidget):
    sig_open_tab_requested = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._items: list[_ScreenshotItem] = []
        self.setStyleSheet(
            """
            QWidget {
                background: #eef2f7;
            }
            """
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(12)

        root.addWidget(_HeaderCard(self))

        content = QHBoxLayout()
        content.setSpacing(14)

        left = QVBoxLayout()
        left.setSpacing(12)

        guide = _GuideCard(self)
        left.addWidget(guide, 0)

        top_panel = self._make_panel()
        top_layout = QVBoxLayout(top_panel)
        top_layout.setContentsMargins(16, 16, 16, 16)
        top_layout.setSpacing(10)

        top_head = QHBoxLayout()
        top_head.setContentsMargins(0, 0, 0, 0)
        top_head.setSpacing(8)
        title = QLabel("Filtry i sekcje")
        title.setStyleSheet("color:#0f172a;font-size:18px;font-weight:900;")
        top_head.addWidget(title)
        top_head.addStretch(1)

        self.btn_open_index = QPushButton("Otworz index")
        self.btn_open_index.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_index.setStyleSheet(
            "QPushButton{background:transparent;border:1px solid #cbd5e1;color:#334155;font-weight:700;padding:7px 11px;border-radius:10px;}"
            "QPushButton:hover{background:#eef2f7;}"
        )
        self.btn_open_index.clicked.connect(self._open_index)
        top_head.addWidget(self.btn_open_index)
        top_layout.addLayout(top_head)

        filter_row = QHBoxLayout()
        filter_row.setContentsMargins(0, 0, 0, 0)
        filter_row.setSpacing(8)
        self.cb_section = QComboBox(self)
        self.cb_section.currentIndexChanged.connect(self._rebuild_grid)
        self.ed_search = QLineEdit(self)
        self.ed_search.setPlaceholderText("Szukaj po nazwie pliku")
        self.ed_search.textChanged.connect(self._rebuild_grid)
        filter_row.addWidget(self.cb_section, 0)
        filter_row.addWidget(self.ed_search, 1)
        top_layout.addLayout(filter_row)

        self.lab_count = QLabel("")
        self.lab_count.setStyleSheet("color:#94a3b8;font-size:12px;font-weight:600;")
        top_layout.addWidget(self.lab_count)

        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        self._scroll.setMinimumHeight(460)
        self._host = QWidget(self._scroll)
        self._grid = QGridLayout(self._host)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(10)
        self._grid.setVerticalSpacing(10)
        self._scroll.setWidget(self._host)
        top_layout.addWidget(self._scroll, 1)
        left.addWidget(top_panel, 1)

        content.addLayout(left, 3)

        right = QVBoxLayout()
        right.setSpacing(12)

        info_panel = self._make_panel()
        info_layout = QVBoxLayout(info_panel)
        info_layout.setContentsMargins(16, 16, 16, 16)
        info_layout.setSpacing(10)
        info_layout.addWidget(self._make_title("Do czego to sluzy"))

        for text, color in (
            ("Porownanie wygladu Start / Modul / Sciana / Wycena.", "#2563eb"),
            ("Szybkie sprawdzenie, co juz mamy zebrane do konsultacji.", "#059669"),
            ("Jedno miejsce na lokalne pliki, bez mieszania z biznesem.", "#7c3aed"),
        ):
            row = QFrame()
            row.setStyleSheet("QFrame{background:transparent;border:1px solid #dbe4f0;border-radius:12px;}")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(12, 10, 12, 10)
            row_layout.setSpacing(8)
            dot = QLabel("•")
            dot.setStyleSheet(f"color:{color};font-size:16px;font-weight:900;")
            row_layout.addWidget(dot, 0, Qt.AlignmentFlag.AlignTop)
            label = QLabel(text)
            label.setWordWrap(True)
            label.setStyleSheet("color:#1e293b;font-size:12px;font-weight:700;")
            row_layout.addWidget(label, 1)
            info_layout.addWidget(row)
        info_layout.addStretch(1)
        right.addWidget(info_panel, 1)

        actions_panel = self._make_panel()
        actions_layout = QVBoxLayout(actions_panel)
        actions_layout.setContentsMargins(16, 16, 16, 16)
        actions_layout.setSpacing(10)
        actions_layout.addWidget(self._make_title("Szybkie przejscia"))

        btn_row = QGridLayout()
        btn_row.setHorizontalSpacing(8)
        btn_row.setVerticalSpacing(8)
        for idx, (label, target, color) in enumerate(
            (
                ("Start", "Start", "#1d4ed8"),
                ("Dashboard", "Dashboard", "#0f172a"),
                ("Grafika", "Grafika", "#7c3aed"),
                ("Ekrany", "Ekrany", "#2563eb"),
                ("Kalendarz", "Kalendarz", "#d97706"),
                ("Czas pracy", "Czas pracy", "#059669"),
            )
        ):
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                f"QPushButton{{background:{color};color:#ffffff;font-weight:800;padding:9px 12px;border-radius:12px;}}"
            )
            btn.clicked.connect(lambda _checked=False, name=target: self._open_tab(name))
            btn_row.addWidget(btn, idx // 2, idx % 2)
        actions_layout.addLayout(btn_row)
        right.addWidget(actions_panel, 0)

        content.addLayout(right, 2)
        
        # Add Telegram Hub Panel below info
        right.addWidget(_TelegramHubPanel(self))
        
        root.addLayout(content, 1)

        self.refresh_data()

    def refresh_data(self) -> None:
        self._items = self._build_items()
        sections = ["all"]
        for item in self._items:
            if item.section not in sections:
                sections.append(item.section)

        current = str(self.cb_section.currentData() or "all").strip().lower()
        self.cb_section.blockSignals(True)
        self.cb_section.clear()
        self.cb_section.addItem("Wszystkie sekcje", "all")
        for section in sorted(s for s in sections if s != "all"):
            self.cb_section.addItem(section, section)
        idx = self.cb_section.findData(current)
        if idx >= 0:
            self.cb_section.setCurrentIndex(idx)
        self.cb_section.blockSignals(False)

        self._rebuild_grid()

    def _rebuild_grid(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        selected = str(self.cb_section.currentData() or "all").strip().lower()
        needle = str(self.ed_search.text() or "").strip().lower()

        filtered: list[_ScreenshotItem] = []
        for item in self._items:
            if selected not in ("all", "wszystkie sekcje") and item.section.lower() != selected:
                continue
            if needle and needle not in item.title.lower() and needle not in item.path.name.lower():
                continue
            filtered.append(item)

        if not filtered:
            empty = QLabel("Brak screenow dla wybranego filtra.")
            empty.setStyleSheet("color:#64748b;font-size:12px;font-style:italic;")
            self._grid.addWidget(empty, 0, 0)
        else:
            for idx, item in enumerate(filtered):
                card = _ScreenshotCard(item, self._open_item, self)
                card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                self._grid.addWidget(card, idx // 3, idx % 3)

        self.lab_count.setText(f"Screeny widoczne: {len(filtered)} / {len(self._items)}")

    def _open_item(self, path: Path) -> None:
        if not path.exists():
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _open_index(self) -> None:
        project_root = Path(__file__).resolve().parents[3]
        index_path = project_root / "docs" / "consultation_pack" / "SCREENS_INDEX.md"
        if index_path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(index_path)))

    def _open_tab(self, title: str) -> None:
        self.sig_open_tab_requested.emit(str(title or "").strip())

    def _build_items(self) -> list[_ScreenshotItem]:
        project_root = Path(__file__).resolve().parents[3]

        def p(*parts: str) -> Path:
            return project_root.joinpath(*parts)

        items = [
            # Consultation pack / shared
            _ScreenshotItem("Start compact UI", "Start", p("docs", "consultation_pack", "screens_full", "test_screenshots", "start_compact_ui.png")),
            _ScreenshotItem("Start compact expanded", "Start", p("docs", "consultation_pack", "screens_full", "test_screenshots", "start_compact_ui_expanded.png")),
            _ScreenshotItem("Start instruction library", "Start", p("docs", "consultation_pack", "screens_full", "test_screenshots", "start_instruction_library.png")),
            _ScreenshotItem("Start instruction mode ON", "Start", p("docs", "consultation_pack", "screens_full", "test_screenshots", "start_instruction_mode_on.png")),
            _ScreenshotItem("Start instruction mode OFF", "Start", p("docs", "consultation_pack", "screens_full", "test_screenshots", "start_instruction_mode_off.png")),
            _ScreenshotItem("Start - topleft fixed", "Start", p("docs", "consultation_pack", "screens_full", "test_screenshots_review_real", "start_topleft_fixed.png")),
            _ScreenshotItem("Start - without briefing panel", "Start", p("docs", "consultation_pack", "screens_full", "test_screenshots_review_real", "start_without_briefing_panel.png")),
            _ScreenshotItem("Start overview", "Start", p("docs", "consultation_pack", "screens_full", "qa_full_tab_screens", "01_start.png")),
            _ScreenshotItem("Modul - empty", "Modul", p("docs", "consultation_pack", "screens_full", "test_screenshots", "02_modul_empty.png")),
            _ScreenshotItem("Modul - loaded", "Modul", p("docs", "consultation_pack", "screens_full", "test_screenshots", "03_modul_loaded.png")),
            _ScreenshotItem("Modul", "Modul", p("docs", "consultation_pack", "screens_full", "qa_full_tab_screens", "03_modul.png")),
            _ScreenshotItem("Modul - review empty", "Modul", p("docs", "consultation_pack", "screens_full", "test_screenshots_review_real", "01_modul_empty.png")),
            _ScreenshotItem("Modul - review loaded", "Modul", p("docs", "consultation_pack", "screens_full", "test_screenshots_review_real", "02_modul_loaded.png")),
            _ScreenshotItem("Komplet - empty", "Komplet", p("docs", "consultation_pack", "screens_full", "test_screenshots", "04_komplet_empty.png")),
            _ScreenshotItem("Komplet", "Komplet", p("docs", "consultation_pack", "screens_full", "qa_full_tab_screens", "04_komplet.png")),
            _ScreenshotItem("Komplet - empty review", "Komplet", p("docs", "consultation_pack", "screens_full", "test_screenshots_review_real", "03_komplet_empty.png")),
            _ScreenshotItem("Komplet - review loaded", "Komplet", p("docs", "consultation_pack", "screens_full", "test_screenshots_review_real", "07_komplet_review_loaded.png")),
            _ScreenshotItem("Komplet - attach default", "Komplet", p("docs", "consultation_pack", "screens_full", "qa_flow_screens_live", "komplet_attach_default.png")),
            _ScreenshotItem("Komplet - collision alert", "Komplet", p("docs", "consultation_pack", "screens_full", "qa_flow_screens_live", "komplet_collision_alert.png")),
            _ScreenshotItem("Komplet - free drag", "Komplet", p("docs", "consultation_pack", "screens_full", "qa_flow_screens_live", "komplet_free_drag_module.png")),
            _ScreenshotItem("Komplet - one module", "Komplet", p("docs", "consultation_pack", "screens_full", "qa_flow_screens_live", "komplet_one_module.png")),
            _ScreenshotItem("Komplet - two modules fixed", "Komplet", p("docs", "consultation_pack", "screens_full", "qa_flow_screens_live", "komplet_two_modules_after_fix.png")),
            _ScreenshotItem("Komplet - upper lower zones", "Komplet", p("docs", "consultation_pack", "screens_full", "qa_flow_screens_live", "komplet_upper_lower_zones.png")),
            _ScreenshotItem("Komplet - split view", "Komplet", p("docs", "consultation_pack", "screens_full", "qa_flow_screens_split", "komplet_split.png")),
            _ScreenshotItem("Sciana - empty", "Sciana", p("docs", "consultation_pack", "screens_full", "test_screenshots", "06_sciana_empty.png")),
            _ScreenshotItem("Sciana", "Sciana", p("docs", "consultation_pack", "screens_full", "qa_full_tab_screens", "05_sciana.png")),
            _ScreenshotItem("Sciana - review loaded", "Sciana", p("docs", "consultation_pack", "screens_full", "test_screenshots_review_real", "08_sciana_review_loaded.png")),
            _ScreenshotItem("Bazy moduly", "Bazy", p("docs", "consultation_pack", "screens_full", "qa_full_tab_screens", "06a_bazy_moduly.png")),
            _ScreenshotItem("Nowe zamowienie", "Nowe zamowienie", p("docs", "consultation_pack", "screens_full", "test_screenshots", "09_zamowienie.png")),
            _ScreenshotItem("Nowe zamowienie - required empty", "Nowe zamowienie", p("docs", "consultation_pack", "screens_full", "test_screenshots_review_real", "nowe_zamowienie_required_empty.png")),
            _ScreenshotItem("Nowe zamowienie - required highlight", "Nowe zamowienie", p("docs", "consultation_pack", "screens_full", "test_screenshots_review_real", "nowe_zamowienie_required_highlight.png")),
            _ScreenshotItem("Nowe zamowienie - top clean", "Nowe zamowienie", p("docs", "consultation_pack", "screens_full", "test_screenshots_review_real", "nowe_zamowienie_top_clean_fixed.png")),
            _ScreenshotItem("Nowe zamowienie - overlap fixed", "Nowe zamowienie", p("docs", "consultation_pack", "screens_full", "test_screenshots_review_real", "nowe_zamowienie_overlap_fixed.png")),
            _ScreenshotItem("Nowe zamowienie - spacing", "Nowe zamowienie", p("docs", "consultation_pack", "screens_full", "test_screenshots_review_real", "nowe_zamowienie_spacing_improved.png")),
            _ScreenshotItem("Nowe zamowienie - top issue", "Nowe zamowienie", p("docs", "consultation_pack", "screens_full", "test_screenshots_review_real", "nowe_debug_top_issue.png")),
            _ScreenshotItem("Nowe zamowienie - dates fixed", "Nowe zamowienie", p("docs", "consultation_pack", "screens_full", "test_screenshots_review_real", "nowe_zamowienie_order_dates_fixed.png")),
            _ScreenshotItem("Nowe zamowienie - after start overlap", "Nowe zamowienie", p("docs", "consultation_pack", "screens_full", "test_screenshots_review_real", "nowe_zamowienie_after_start_overlap_check.png")),
            _ScreenshotItem("Nowe zamowienie - static panels top", "Nowe zamowienie", p("docs", "consultation_pack", "screens_full", "test_screenshots_review_real", "nowe_zamowienie_static_panels_top.png")),
            _ScreenshotItem("Nowe zamowienie - static panels bottom", "Nowe zamowienie", p("docs", "consultation_pack", "screens_full", "test_screenshots_review_real", "nowe_zamowienie_static_panels_bottom.png")),
            _ScreenshotItem("Dashboard", "Dashboard", p("docs", "consultation_pack", "screens_full", "test_screenshots", "08_dashboard.png")),
            _ScreenshotItem("Kalendarz - compact", "Kalendarz", p("docs", "consultation_pack", "screens_full", "test_screenshots", "czas_pracy_compact.png")),
            _ScreenshotItem("Czas pracy - team summary", "Czas pracy", p("docs", "consultation_pack", "screens_full", "test_screenshots", "czas_pracy_team_summary.png")),
            _ScreenshotItem("QR telefon - mobile", "Ekrany", p("docs", "consultation_pack", "screens_full", "test_screenshots", "qr_telefon_measure_mobile.png")),
            _ScreenshotItem("QR telefon - mobile window", "Ekrany", p("docs", "consultation_pack", "screens_full", "test_screenshots_review_real", "qr_telefon_mobile_window.png")),
            _ScreenshotItem("QR telefon - tab full", "Ekrany", p("docs", "consultation_pack", "screens_full", "test_screenshots_review_real", "qr_telefon_tab_full.png")),
            _ScreenshotItem("QR telefon - tab only", "Ekrany", p("docs", "consultation_pack", "screens_full", "test_screenshots_review_real", "qr_telefon_tab_only.png")),
            _ScreenshotItem("Briefing tab", "Start", p("docs", "consultation_pack", "screens_full", "test_screenshots_review_real", "briefing_tab.png")),
            # Local downloaded materials
            _ScreenshotItem("Formatki pozycji", "Konsultacje", p("pliki pobrane", "Zrzut ekranu 2026-03-26 190259.png")),
            _ScreenshotItem("WhatsApp - recepcja / receipt", "Konsultacje", p("pliki pobrane", "WhatsApp Image 2026-04-02 at 12.48.19.jpeg")),
            _ScreenshotItem("Telegram - pomiar sciany", "Telegram", p("pliki pobrane", "telegram", "tg_20260330_221142_16_AQADxw5rGy2d.jpg")),
            _ScreenshotItem("Telegram - pomiar sciany 2", "Telegram", p("pliki pobrane", "telegram", "tg_20260330_221142_17_AQADxg5rGy2d.jpg")),
            _ScreenshotItem("Telegram - pomiar sciany 3", "Telegram", p("pliki pobrane", "telegram", "tg_20260330_221142_18_AQADyA5rGy2d.jpg")),
            _ScreenshotItem("Telegram - pomiar sciany 4", "Telegram", p("pliki pobrane", "telegram", "tg_20260330_221142_19_AQADyQ5rGy2d.jpg")),
            _ScreenshotItem("Bazy - glowne", "Bazy", p("docs", "consultation_pack", "screens_full", "qa_full_tab_screens", "06_bazy.png")),
            _ScreenshotItem("Bazy - klienci", "Bazy", p("docs", "consultation_pack", "screens_full", "qa_full_tab_screens", "06b_bazy_klienci.png")),
        ]
        return [item for item in items if item.path.exists()]

    def _make_panel(self) -> QFrame:
        panel = QFrame(self); panel.setProperty("uiCard", True)
        panel.setStyleSheet(
            """
            QFrame {
                background: transparent;
                border: 1px solid #dbe4f0;
                border-radius: 22px;
            }
            """
        )
        return panel

    def _make_title(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet("color:#0f172a;font-size:16px;font-weight:900;")
        return label
