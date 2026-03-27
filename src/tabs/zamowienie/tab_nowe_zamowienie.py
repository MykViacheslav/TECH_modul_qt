from __future__ import annotations

import base64
import os
import re
from collections import defaultdict
from datetime import datetime
from html import escape
from pathlib import Path

from PyQt6.QtCore import QDate, QMimeData, QPoint, QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QDrag, QIcon, QPainter, QPen, QPixmap, QTextDocument
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QFormLayout,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QInputDialog,
    QDateEdit,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSplitter,
    QSpinBox,
    QSizePolicy,
    QTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.app.app_settings import (
    load_drawing_settings,
    load_table_column_widths,
    load_ui_string_list,
    save_table_column_widths,
    save_ui_string_list,
)
from src.domain.assembly_resolution_service import resolve_assembly_items
from src.domain.calendar_event import CalendarEvent
from src.domain.client_models import ClientDef
from src.domain.order_models import OrderDef
from src.domain.worker_models import WorkerDef
from src.storage.assembly_store_json import AssemblyStoreJson
from src.storage.calendar_event_store_json import CalendarEventStoreJson
from src.storage.catalog_store_json import CatalogStoreJson
from src.storage.client_store_json import ClientStoreJson
from src.storage.order_draft_store_json import OrderDraftStoreJson
from src.storage.order_store_json import OrderStoreJson
from src.storage.wall_store_json import WallStoreJson
from src.storage.worker_store_json import WorkerStoreJson
from src.ui.collapsible_block import CollapsibleBlock

# Alarm integration
from src.services.alarm_service import AlarmService
from src.services.alarm_rules import check_material_stock_for_order, check_deadline_conflict

# Calendar integration
from src.services.order_calendar_sync import sync_single_order


ORDER_STATUS_ITEMS: tuple[str, ...] = (
    "Nowe",
    "Wycena",
    "Wycena gotowa",
    "Zaakceptowane",
    "Zakup materialow",
    "W produkcji",
    "Lakiernia",
    "Montaz",
    "Poprawki",
    "Zakonczone",
)

QUOTE_ITEM_TYPES: tuple[str, ...] = (
    "Kuchnia",
    "Szafa",
    "RTV",
    "Lazienka",
    "Garderoba",
    "Biuro",
    "Inne",
)

MATERIAL_SCOPE_ITEMS: tuple[str, ...] = (
    "Korpus",
    "Front",
    "Blat",
    "Okleina",
    "Farba",
    "Uchwyt",
    "Szklo",
    "Inne",
)

MATERIAL_CHOICE_STATUS_ITEMS: tuple[str, ...] = (
    "Probka pokazana",
    "Wariant",
    "Wybrane finalnie",
    "Odrzucone",
)

ATTACHMENT_TARGET_ITEMS: tuple[str, ...] = (
    "Zamowienie",
    "Pozycja do wyceny",
    "Sciana",
    "Komplet",
    "Oferta",
)

IMAGEMETER_IMAGE_SUFFIXES: tuple[str, ...] = (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".heic", ".heif")
IMAGEMETER_PDF_SUFFIXES: tuple[str, ...] = (".pdf",)

CUSTOMER_PAYMENT_STAGE_ITEMS: tuple[str, ...] = (
    "Rezerwacja terminu",
    "Start pracy / 60%",
    "Przed montazem / 30%",
    "Koniec / 10%",
    "Inne",
)


CLIENT_FIELD_MIME = "application/x-tech-modul-client-field"


class ArchitectCropPreview(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(420, 280)
        self._pixmap = QPixmap()
        self._display_rect = QRect()
        self._selection_rect = QRect()
        self._drag_start: QPoint | None = None
        self._message = "Brak podgladu strony."
        self.setMouseTracking(True)

    def set_source_pixmap(self, pixmap: QPixmap | None, message: str = "") -> None:
        self._pixmap = pixmap if isinstance(pixmap, QPixmap) else QPixmap()
        self._selection_rect = QRect()
        self._drag_start = None
        self._message = message or ("Brak podgladu strony." if self._pixmap.isNull() else "")
        self.update()

    def clear_selection(self) -> None:
        self._selection_rect = QRect()
        self.update()

    def has_selection(self) -> bool:
        return not self._selection_rect.isNull() and self._selection_rect.width() > 6 and self._selection_rect.height() > 6

    def set_selection_rect(self, rect: QRect) -> None:
        if rect.isNull():
            self._selection_rect = QRect()
        else:
            self._selection_rect = rect.normalized().intersected(self._display_rect)
        self.update()

    def selected_source_rect(self) -> QRect:
        if self._pixmap.isNull() or self._display_rect.isNull() or not self.has_selection():
            return QRect()
        scale_x = self._pixmap.width() / max(1, self._display_rect.width())
        scale_y = self._pixmap.height() / max(1, self._display_rect.height())
        left = int((self._selection_rect.left() - self._display_rect.left()) * scale_x)
        top = int((self._selection_rect.top() - self._display_rect.top()) * scale_y)
        width = int(self._selection_rect.width() * scale_x)
        height = int(self._selection_rect.height() * scale_y)
        return QRect(left, top, width, height).intersected(self._pixmap.rect())

    def selected_source_pixmap(self) -> QPixmap:
        rect = self.selected_source_rect()
        if rect.isNull():
            return QPixmap()
        return self._pixmap.copy(rect)

    def _recalculate_display_rect(self) -> None:
        if self._pixmap.isNull():
            self._display_rect = QRect()
            return
        margin = 10
        available = self.rect().adjusted(margin, margin, -margin, -margin)
        scaled = self._pixmap.scaled(
            available.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = available.left() + max(0, (available.width() - scaled.width()) // 2)
        y = available.top() + max(0, (available.height() - scaled.height()) // 2)
        self._display_rect = QRect(x, y, scaled.width(), scaled.height())

    def paintEvent(self, _event) -> None:
        self._recalculate_display_rect()
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#fafbfc"))
        painter.setPen(QPen(QColor("#d7dbe2"), 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

        if self._pixmap.isNull():
            painter.setPen(QPen(QColor("#666666")))
            painter.drawText(self.rect().adjusted(12, 12, -12, -12), Qt.AlignmentFlag.AlignCenter, self._message)
            return

        painter.drawPixmap(self._display_rect, self._pixmap)
        painter.setPen(QPen(QColor("#94a3b8"), 1, Qt.PenStyle.DashLine))
        painter.drawRect(self._display_rect)

        if not self._selection_rect.isNull():
            painter.fillRect(self._selection_rect, QColor(59, 130, 246, 40))
            painter.setPen(QPen(QColor("#2563eb"), 2))
            painter.drawRect(self._selection_rect)

        if not self.has_selection():
            info_rect = QRect(self._display_rect.left() + 8, self._display_rect.top() + 8, min(260, self._display_rect.width() - 16), 44)
            painter.fillRect(info_rect, QColor(255, 255, 255, 220))
            painter.setPen(QPen(QColor("#334155")))
            painter.drawText(info_rect.adjusted(8, 6, -8, -6), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "Przeciagnij myszka, aby zaznaczyc fragment strony.")

    def mousePressEvent(self, event) -> None:
        if self._pixmap.isNull() or event.button() != Qt.MouseButton.LeftButton:
            return
        pos = event.position().toPoint()
        if not self._display_rect.contains(pos):
            return
        self._drag_start = pos
        self._selection_rect = QRect(pos, pos)
        self.update()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_start is None:
            return
        pos = event.position().toPoint()
        pos.setX(max(self._display_rect.left(), min(self._display_rect.right(), pos.x())))
        pos.setY(max(self._display_rect.top(), min(self._display_rect.bottom(), pos.y())))
        self._selection_rect = QRect(self._drag_start, pos).normalized().intersected(self._display_rect)
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._drag_start = None
        if self._selection_rect.width() <= 6 or self._selection_rect.height() <= 6:
            self._selection_rect = QRect()
        self.update()


class ClientFieldDragLabel(QLabel):
    def __init__(self, field_key: str, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self._field_key = str(field_key or "").strip()
        self._drag_start_pos: QPoint | None = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return super().mouseMoveEvent(event)
        if self._drag_start_pos is None:
            return super().mouseMoveEvent(event)
        if (event.position().toPoint() - self._drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            return super().mouseMoveEvent(event)

        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(CLIENT_FIELD_MIME, self._field_key.encode("utf-8"))
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.MoveAction)
        self._drag_start_pos = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        self._drag_start_pos = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)


class ClientFieldCell(QFrame):
    sig_field_dropped = pyqtSignal(str, str)

    def __init__(self, field_key: str, label_text: str, editor: QWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.field_key = str(field_key or "").strip()
        self.setProperty("field_key", self.field_key)
        self.setAcceptDrops(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self.label = ClientFieldDragLabel(self.field_key, label_text, self)
        self.label.setStyleSheet("color:#5b6470; font-size:11px;")
        layout.addWidget(self.label)
        layout.addWidget(editor)

    def dragEnterEvent(self, event) -> None:  # type: ignore[override]
        if event.mimeData().hasFormat(CLIENT_FIELD_MIME):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dropEvent(self, event) -> None:  # type: ignore[override]
        if not event.mimeData().hasFormat(CLIENT_FIELD_MIME):
            return super().dropEvent(event)
        try:
            source_key = bytes(event.mimeData().data(CLIENT_FIELD_MIME)).decode("utf-8").strip()
        except Exception:
            source_key = ""
        target_key = self.field_key
        if source_key and target_key and source_key != target_key:
            self.sig_field_dropped.emit(source_key, target_key)
            event.acceptProposedAction()
            return
        super().dropEvent(event)


class TabNoweZamowienie(QWidget):
    sig_open_clients_base_requested = pyqtSignal()
    sig_open_orders_base_requested = pyqtSignal()
    sig_open_workers_base_requested = pyqtSignal()
    sig_open_sciana_requested = pyqtSignal(dict)
    sig_open_komplet_requested = pyqtSignal(dict)
    sig_open_existing_sciana_requested = pyqtSignal(str)

    _ORDER_STAGE_CALENDAR_MAP: tuple[tuple[str, str, str, str], ...] = (
        ("wycena", "date_wycena", "wstepna_wycena", "Biuro"),
        ("projekt", "date_projekt", "zlecenie", "Biuro"),
        ("probki", "date_probki", "inne", "Biuro"),
        ("zakup_mat", "date_zakup_mat", "zamowienie_mat", "Biuro"),
        ("produkcja", "date_produkcja", "zlecenie", "CNC"),
        ("montaz", "date_montaz", "montaz", "ZBORKA"),
        ("poprawki", "date_poprawki", "poprawki", "ZBORKA"),
    )

    def __init__(
        self,
        parent: QWidget | None = None,
        client_store: ClientStoreJson | None = None,
        order_store: OrderStoreJson | None = None,
        worker_store: WorkerStoreJson | None = None,
        wall_store: WallStoreJson | None = None,
        assembly_store: AssemblyStoreJson | None = None,
        catalog: CatalogStoreJson | None = None,
        draft_store: OrderDraftStoreJson | None = None,
        calendar_store: CalendarEventStoreJson | None = None,
    ) -> None:
        super().__init__(parent)

        self._testing_mode = str(os.environ.get("TECH_MODUL_TESTING", "")).strip() == "1"
        self._client_store = client_store if client_store is not None else ClientStoreJson()
        self._order_store = order_store if order_store is not None else OrderStoreJson()
        self._worker_store = worker_store if worker_store is not None else WorkerStoreJson()
        self._wall_store = wall_store if wall_store is not None else WallStoreJson()
        self._assembly_store = assembly_store if assembly_store is not None else AssemblyStoreJson()
        self._catalog = catalog if catalog is not None else CatalogStoreJson()
        self._draft_store = draft_store if draft_store is not None else OrderDraftStoreJson()
        self._calendar_store = calendar_store if calendar_store is not None else CalendarEventStoreJson()
        self._is_restoring_draft = False
        self._architect_preview_pages: list[dict[str, object]] = []
        self._architect_preview_header = ""
        self._offer_reference_items: list[dict[str, str]] = []
        self._offer_reference_pixmap = QPixmap()
        self._quote_reference_items: list[dict[str, str]] = []
        self._quote_reference_pixmap = QPixmap()
        self._current_order_calendar_stage = ""
        self._current_order_calendar_date = ""
        self._current_order_calendar_note = ""
        self._customer_payments: list[dict[str, object]] = []
        self._is_syncing_order_address = False
        self._is_syncing_worker_name = False
        self._generated_order_ids: set[str] = set()
        self._entry_editor_visible = True

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        title = QLabel("NOWE ZAMOWIENIE")
        title.setStyleSheet("font-size: 22px; font-weight: 800; letter-spacing: 0.5px;")
        root.addWidget(title, 0, Qt.AlignmentFlag.AlignLeft)

        subtitle = QLabel("Start projektu: klient, zamowienie, pracownik i pozycje do wyceny.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color:#555555;")
        root.addWidget(subtitle, 0, Qt.AlignmentFlag.AlignLeft)

        self.start_entry_bar = QFrame(self)
        self.start_entry_bar.setObjectName("newOrderEntryBar")
        self.start_entry_bar.setStyleSheet(
            """
            QFrame#newOrderEntryBar {
                border: 1px solid #ddd3c1;
                border-radius: 14px;
                background: #fcfaf6;
            }
            """
        )
        start_entry_layout = QHBoxLayout(self.start_entry_bar)
        start_entry_layout.setContentsMargins(14, 12, 14, 12)
        start_entry_layout.setSpacing(10)
        self.btn_start_new_order = QPushButton("+ Dodaj nowe zamowienie", self.start_entry_bar)
        self._make_compact_button(self.btn_start_new_order, min_width=220, max_width=260)
        self.btn_start_new_order.setMinimumHeight(42)
        start_entry_layout.addWidget(self.btn_start_new_order, 0)
        start_entry_layout.addStretch(1)
        root.addWidget(self.start_entry_bar, 0)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        root.addWidget(self.scroll_area, 1)

        self.page_widget = QWidget(self.scroll_area)
        self.scroll_area.setWidget(self.page_widget)

        page_root = QVBoxLayout(self.page_widget)
        page_root.setContentsMargins(0, 0, 0, 0)
        page_root.setSpacing(14)

        body = QVBoxLayout()
        body.setSpacing(12)
        page_root.addLayout(body, 1)
        self.body_layout = body

        self.grp_client = CollapsibleBlock("Klient", self)
        self.grp_order = CollapsibleBlock("Zamowienie", self)
        self.grp_worker = CollapsibleBlock("Pracownik", self)
        self.grp_actions = CollapsibleBlock("Akcje", self)
        self.grp_architect = CollapsibleBlock("Zalaczniki od architekta", self)
        self.grp_quote_items = CollapsibleBlock("Pozycje do wyceny", self)
        self.grp_material_choices = CollapsibleBlock("Probki i finalne materialy", self)
        self.grp_customer_cash = CollapsibleBlock("Kasa klienta", self)
        self.grp_walls = CollapsibleBlock("Sciany zamowienia", self)
        self.grp_summary = CollapsibleBlock("Podsumowanie zamowienia", self)

        body.addWidget(self.grp_client)
        body.addWidget(self.grp_order)
        body.addWidget(self.grp_worker)
        body.addWidget(self.grp_quote_items)
        body.addWidget(self.grp_actions)
        body.addWidget(self.grp_architect)
        body.addWidget(self.grp_material_choices)
        body.addWidget(self.grp_customer_cash)
        body.addWidget(self.grp_walls)
        body.addWidget(self.grp_summary)
        body.addStretch(1)

        for block in (
            self.grp_client,
            self.grp_order,
            self.grp_worker,
            self.grp_quote_items,
            self.grp_actions,
            self.grp_architect,
            self.grp_material_choices,
            self.grp_customer_cash,
            self.grp_walls,
            self.grp_summary,
        ):
            block.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
            self._apply_collapsible_visual_polish(block)

        self._build_client_group()
        self._build_order_group()
        self._build_worker_group()
        self._build_actions_group()
        self._build_architect_group()
        self._build_quote_items_group()
        self._build_material_choices_group()
        self._build_customer_cash_group()
        self._build_walls_group()
        self._build_summary_group()

        self.grp_architect.set_expanded(False)
        self.grp_material_choices.set_expanded(False)
        self.grp_customer_cash.set_expanded(False)
        self.grp_walls.set_expanded(False)
        self.grp_summary.set_expanded(False)

        self.lab_status = QLabel("")
        self.lab_status.setWordWrap(True)
        self.lab_status.setStyleSheet("color:#666666;")
        page_root.addWidget(self.lab_status)

        page_root.addStretch(1)

        self.cb_client_name.currentTextChanged.connect(self._on_client_name_changed)
        self.cb_worker_name.currentTextChanged.connect(self._on_worker_name_changed)
        self.ed_worker_name_input.textChanged.connect(self._on_worker_name_input_changed)
        self.ed_worker_first_name.textChanged.connect(self._on_worker_name_parts_changed)
        self.ed_worker_last_name.textChanged.connect(self._on_worker_name_parts_changed)
        self.ed_order_id.textChanged.connect(self._refresh_summary)
        self.ed_order_code.textChanged.connect(self._refresh_summary)
        self.cb_order_status.currentTextChanged.connect(self._refresh_summary)
        self.sp_order_progress.valueChanged.connect(self._refresh_summary)
        self.ed_order_address.textChanged.connect(self._on_order_address_text_changed)
        self.ed_order_address.textChanged.connect(self._refresh_summary)
        self.ed_order_site_street.textChanged.connect(self._on_order_address_parts_changed)
        self.ed_order_site_house_number.textChanged.connect(self._on_order_address_parts_changed)
        self.ed_order_site_apartment_number.textChanged.connect(self._on_order_address_parts_changed)
        self.ed_order_site_postal_code.textChanged.connect(self._on_order_address_parts_changed)
        self.ed_order_site_city.textChanged.connect(self._on_order_address_parts_changed)
        self.ed_client_id.textChanged.connect(self._refresh_summary)
        self.ed_client_first_name.textChanged.connect(self._refresh_summary)
        self.ed_client_last_name.textChanged.connect(self._refresh_summary)
        self.ed_client_phone.textChanged.connect(self._refresh_summary)
        self.ed_client_email.textChanged.connect(self._refresh_summary)
        self.ed_client_street.textChanged.connect(self._refresh_summary)
        self.ed_client_house_number.textChanged.connect(self._refresh_summary)
        self.ed_client_apartment_number.textChanged.connect(self._refresh_summary)
        self.ed_client_postal_code.textChanged.connect(self._refresh_summary)
        self.ed_client_city.textChanged.connect(self._refresh_summary)
        self.ed_worker_id.textChanged.connect(self._refresh_summary)
        self.ed_worker_first_name.textChanged.connect(self._refresh_summary)
        self.ed_worker_last_name.textChanged.connect(self._refresh_summary)
        self.ed_worker_role.textChanged.connect(self._refresh_summary)
        self.ed_worker_phone.textChanged.connect(self._refresh_summary)
        self.ed_worker_email.textChanged.connect(self._refresh_summary)

        self.btn_pick_client.clicked.connect(self._on_pick_client_from_base)
        self.btn_save_client.clicked.connect(self._on_save_client_to_base)
        self.btn_start_new_order.clicked.connect(self._on_start_new_order_clicked)
        self.btn_pick_order.clicked.connect(self._on_pick_order_from_base)
        self.btn_save_order.clicked.connect(self._on_save_order_to_base)
        self.btn_pick_worker.clicked.connect(self._on_pick_worker_from_base)
        self.btn_save_worker.clicked.connect(self._on_save_worker_to_base)
        self.btn_open_clients_base.clicked.connect(self.sig_open_clients_base_requested.emit)
        self.btn_open_orders_base.clicked.connect(self.sig_open_orders_base_requested.emit)
        self.btn_open_workers_base.clicked.connect(self.sig_open_workers_base_requested.emit)
        self.btn_go_to_sciana.clicked.connect(self._on_go_to_sciana)
        self.btn_export_offer.clicked.connect(self._on_export_offer)
        self.btn_export_offer_pdf.clicked.connect(self._on_export_offer_pdf)
        self.btn_save_new.clicked.connect(self._on_save_new)
        self.btn_overwrite_all.clicked.connect(self._on_overwrite_all)
        self.btn_save_draft.clicked.connect(lambda: self._save_draft(show_status=True))
        self.btn_clear.clicked.connect(lambda: self.start_new_order(force_blank=True))
        self.btn_pick_architect_file.clicked.connect(self._on_pick_architect_file)
        self.btn_import_imagemeter_files.clicked.connect(self._on_import_imagemeter_files)
        self.btn_add_architect_attachment.clicked.connect(self._on_add_architect_attachment)
        self.btn_remove_architect_attachment.clicked.connect(self._on_remove_architect_attachment)
        self.tbl_architect_attachments.itemSelectionChanged.connect(
            self._on_architect_attachment_selection_changed
        )
        self.btn_save_architect_fragment.clicked.connect(self._on_save_architect_fragment)
        self.btn_clear_architect_fragment.clicked.connect(self.architect_crop_preview.clear_selection)
        self.btn_add_quote_item.clicked.connect(self._on_add_quote_item)
        self.btn_remove_quote_item.clicked.connect(self._on_remove_quote_item)
        self.btn_quote_to_sciana.clicked.connect(self._on_open_quote_item_as_sciana)
        self.btn_quote_to_komplet.clicked.connect(self._on_open_quote_item_as_komplet)
        self.btn_quote_set_fragment_target.clicked.connect(self._on_use_quote_item_as_fragment_target)
        self.tbl_quote_items.itemSelectionChanged.connect(self._on_quote_item_selection_changed)
        self.btn_add_material_choice.clicked.connect(self._on_add_material_choice)
        self.btn_remove_material_choice.clicked.connect(self._on_remove_material_choice)
        self.tbl_material_choices.itemSelectionChanged.connect(self._on_material_choice_selection_changed)
        self.btn_customer_payment_prefill.clicked.connect(self._on_prefill_customer_payments)
        self.btn_add_customer_payment.clicked.connect(self._on_add_customer_payment)
        self.btn_remove_customer_payment.clicked.connect(self._on_remove_customer_payment)
        self.tbl_customer_payments.itemSelectionChanged.connect(self._on_customer_payment_selection_changed)
        self.btn_new_wall.clicked.connect(self._on_go_to_sciana)
        self.btn_open_wall.clicked.connect(self._on_open_selected_wall)
        self.btn_refresh_walls.clicked.connect(self._refresh_order_walls_table)
        self.tbl_walls.itemSelectionChanged.connect(self._on_walls_selection_changed)
        self.tbl_walls.itemDoubleClicked.connect(lambda _item: self._on_open_selected_wall())

        if self._testing_mode:
            self.start_new_order()
        else:
            self.show_new_order_launcher()

    def _set_entry_editor_visible(self, visible: bool) -> None:
        self._entry_editor_visible = bool(visible)
        self.start_entry_bar.setVisible(not visible)
        self.scroll_area.setVisible(visible)
        if hasattr(self, "lab_status"):
            self.lab_status.setVisible(visible)

    def show_new_order_launcher(self) -> None:
        if self._testing_mode:
            self._set_entry_editor_visible(True)
            return
        self.lab_status.clear()
        self._set_entry_editor_visible(False)

    def show_new_order_launcher_if_empty(self) -> None:
        if self._testing_mode:
            return
        if self._has_meaningful_draft(self._draft_payload()):
            self._set_entry_editor_visible(True)
            return
        self.show_new_order_launcher()

    def _on_start_new_order_clicked(self) -> None:
        self.start_new_order(force_blank=True)

    def _build_client_group(self) -> None:
        layout = self.grp_client.content_layout()
        content_parent = layout.parentWidget() or self.grp_client

        self.cb_client_name = QComboBox(self.grp_client)
        self.cb_client_name.setEditable(True)
        self.cb_client_name.setMinimumWidth(280)
        if self.cb_client_name.lineEdit() is not None:
            self.cb_client_name.lineEdit().setPlaceholderText("[wybierz klienta albo wpisz nowego]")
        self.btn_pick_client = QPushButton("Wybierz z bazy", self.grp_client)
        self.btn_save_client = QPushButton("Dodaj do bazy", self.grp_client)
        self.btn_open_clients_base = QPushButton("Bazy", self.grp_client)
        self._make_compact_button(self.btn_pick_client, min_width=120, max_width=150)
        self._make_compact_button(self.btn_save_client, min_width=120, max_width=150)
        self._make_compact_button(self.btn_open_clients_base, min_width=70, max_width=90)
        client_picker_row = QHBoxLayout()
        client_picker_row.setSpacing(8)
        client_picker_row.addWidget(QLabel("Klient:", self.grp_client), 0)
        client_picker_row.addWidget(self.cb_client_name, 1)
        client_picker_row.addWidget(self.btn_pick_client, 0)
        client_picker_row.addWidget(self.btn_save_client, 0)
        client_picker_row.addWidget(self.btn_open_clients_base, 0)
        client_picker_row.addStretch(1)
        layout.addLayout(client_picker_row)

        self.client_identity_splitter = QSplitter(Qt.Orientation.Horizontal, content_parent)
        self.client_identity_splitter.setChildrenCollapsible(False)
        self.client_identity_splitter.setHandleWidth(8)
        self.ed_client_id = QLineEdit(self.grp_client)
        self.ed_client_id.setPlaceholderText("ID")
        self.ed_client_id.setMinimumWidth(52)
        self.ed_client_first_name = QLineEdit(self.grp_client)
        self.ed_client_first_name.setPlaceholderText("Imie")
        self.ed_client_first_name.setMinimumWidth(90)
        self.ed_client_last_name = QLineEdit(self.grp_client)
        self.ed_client_last_name.setPlaceholderText("Nazwisko")
        self.ed_client_last_name.setMinimumWidth(110)
        self.ed_client_phone = QLineEdit(self.grp_client)
        self.ed_client_phone.setPlaceholderText("Telefon")
        self.ed_client_phone.setMinimumWidth(90)
        self.ed_client_email = QLineEdit(self.grp_client)
        self.ed_client_email.setPlaceholderText("E-mail")
        self.ed_client_email.setMinimumWidth(120)
        self._client_field_cells: dict[str, QWidget] = {}
        self._client_identity_defaults = ["id", "first_name", "last_name", "phone", "email"]
        self._client_address_defaults = ["street", "house_number", "apartment_number", "postal_code", "city"]
        self._client_field_cells["id"] = self._make_client_field_cell("id", "ID", self.ed_client_id, self.grp_client)
        self._client_field_cells["first_name"] = self._make_client_field_cell(
            "first_name", "Imie", self.ed_client_first_name, self.grp_client
        )
        self._client_field_cells["last_name"] = self._make_client_field_cell(
            "last_name", "Nazwisko", self.ed_client_last_name, self.grp_client
        )
        self._client_field_cells["phone"] = self._make_client_field_cell(
            "phone", "Telefon", self.ed_client_phone, self.grp_client
        )
        self._client_field_cells["email"] = self._make_client_field_cell(
            "email", "E-mail", self.ed_client_email, self.grp_client
        )
        identity_saved_order = load_ui_string_list("order_client_identity_order", self._client_identity_defaults)
        self._apply_client_field_order(self.client_identity_splitter, identity_saved_order, self._client_identity_defaults)
        self._restore_splitter_widths(
            self.client_identity_splitter,
            "order_client_identity_fields",
            [70, 130, 170, 130, 180],
        )
        self.client_identity_splitter.splitterMoved.connect(
            lambda _pos, _idx: self._save_splitter_widths(self.client_identity_splitter, "order_client_identity_fields")
        )

        self.client_address_splitter = QSplitter(Qt.Orientation.Horizontal, content_parent)
        self.client_address_splitter.setChildrenCollapsible(False)
        self.client_address_splitter.setHandleWidth(8)
        self.ed_client_street = QLineEdit(self.grp_client)
        self.ed_client_street.setPlaceholderText("Ulica")
        self.ed_client_street.setMinimumWidth(100)
        self.ed_client_house_number = QLineEdit(self.grp_client)
        self.ed_client_house_number.setPlaceholderText("Dom")
        self.ed_client_house_number.setMinimumWidth(50)
        self.ed_client_apartment_number = QLineEdit(self.grp_client)
        self.ed_client_apartment_number.setPlaceholderText("Mieszkanie")
        self.ed_client_apartment_number.setMinimumWidth(70)
        self.ed_client_postal_code = QLineEdit(self.grp_client)
        self.ed_client_postal_code.setPlaceholderText("Kod")
        self.ed_client_postal_code.setMinimumWidth(70)
        self.ed_client_city = QLineEdit(self.grp_client)
        self.ed_client_city.setPlaceholderText("Miasto")
        self.ed_client_city.setMinimumWidth(90)
        self._client_field_cells["street"] = self._make_client_field_cell(
            "street", "Ulica", self.ed_client_street, self.grp_client
        )
        self._client_field_cells["house_number"] = self._make_client_field_cell(
            "house_number", "Dom", self.ed_client_house_number, self.grp_client
        )
        self._client_field_cells["apartment_number"] = self._make_client_field_cell(
            "apartment_number", "Mieszkanie", self.ed_client_apartment_number, self.grp_client
        )
        self._client_field_cells["postal_code"] = self._make_client_field_cell(
            "postal_code", "Kod", self.ed_client_postal_code, self.grp_client
        )
        self._client_field_cells["city"] = self._make_client_field_cell(
            "city", "Miasto", self.ed_client_city, self.grp_client
        )
        address_saved_order = load_ui_string_list("order_client_address_order", self._client_address_defaults)
        self._apply_client_field_order(self.client_address_splitter, address_saved_order, self._client_address_defaults)
        self._restore_splitter_widths(
            self.client_address_splitter,
            "order_client_address_fields",
            [210, 80, 100, 100, 140],
        )
        self.client_address_splitter.splitterMoved.connect(
            lambda _pos, _idx: self._save_splitter_widths(self.client_address_splitter, "order_client_address_fields")
        )

        self.client_rows_layout = QVBoxLayout()
        self.client_rows_layout.setContentsMargins(0, 2, 0, 2)
        self.client_rows_layout.setSpacing(8)
        layout.addLayout(self.client_rows_layout)

        self.client_identity_row = QWidget(content_parent)
        identity_row_layout = QHBoxLayout(self.client_identity_row)
        identity_row_layout.setContentsMargins(0, 0, 0, 0)
        identity_row_layout.setSpacing(6)
        identity_row_layout.addWidget(self.client_identity_splitter, 1)

        self.client_address_row = QWidget(content_parent)
        address_row_layout = QHBoxLayout(self.client_address_row)
        address_row_layout.setContentsMargins(0, 0, 0, 0)
        address_row_layout.setSpacing(6)
        address_row_layout.addWidget(self.client_address_splitter, 1)

        self.client_rows_layout.addWidget(self.client_identity_row)
        self.client_rows_layout.addWidget(self.client_address_row)
        self._save_client_field_orders()

        form = QFormLayout()
        self.ed_client_notes = QTextEdit(self.grp_client)
        self.ed_client_notes.setMaximumHeight(52)
        form.addRow("Notatki", self.ed_client_notes)
        layout.addLayout(form)

        note = QLabel("Wybierz klienta z bazy z listy u gory albo wpisz nowego i kliknij 'Dodaj do bazy'.")
        note.setWordWrap(True)
        note.setStyleSheet("color:#666666;")
        layout.addWidget(note)

    def _build_order_group(self) -> None:
        layout = self.grp_order.content_layout()
        content_parent = layout.parentWidget() or self.grp_order

        self.btn_pick_order = QPushButton("Wczytaj z bazy", self.grp_order)
        self.btn_save_order = QPushButton("Zapisz zamowienie", self.grp_order)
        self.btn_open_orders_base = QPushButton("Bazy", self.grp_order)
        self._make_compact_button(self.btn_pick_order, min_width=120, max_width=150)
        self._make_compact_button(self.btn_save_order, min_width=130, max_width=160)
        self._make_compact_button(self.btn_open_orders_base, min_width=70, max_width=90)
        self.btn_pick_order.hide()
        self.btn_save_order.hide()
        self.btn_open_orders_base.hide()

        self.ed_order_id = QLineEdit(self.grp_order)
        self.ed_order_id.setPlaceholderText("ID")
        self.ed_order_id.setMinimumWidth(70)
        self.ed_order_id.setReadOnly(True)
        self.ed_order_id.setToolTip("ID nadaje sie automatycznie.")

        self.ed_order_code = QLineEdit(self.grp_order)
        self.ed_order_code.setPlaceholderText("Kod")
        self.ed_order_code.setMinimumWidth(130)

        self.ed_order_name = QLineEdit(self.grp_order)
        self.ed_order_name.setPlaceholderText("Nazwa zamowienia")
        self.ed_order_name.setMinimumWidth(200)

        self.cb_order_status = QComboBox(self.grp_order)
        for item in ORDER_STATUS_ITEMS:
            self.cb_order_status.addItem(item)
        self.cb_order_status.setMinimumWidth(140)

        self.sp_order_progress = QSpinBox(self.grp_order)
        self.sp_order_progress.setRange(0, 100)
        self.sp_order_progress.setSingleStep(5)
        self.sp_order_progress.setSuffix(" %")
        self.sp_order_progress.setMinimumWidth(100)

        self.ed_order_address = QLineEdit(self.grp_order)
        self.ed_order_address.setPlaceholderText("Adres realizacji")
        self.ed_order_address.hide()

        self.ed_order_site_street = QLineEdit(self.grp_order)
        self.ed_order_site_street.setPlaceholderText("Ulica")
        self.ed_order_site_street.setMinimumWidth(220)
        self.ed_order_site_house_number = QLineEdit(self.grp_order)
        self.ed_order_site_house_number.setPlaceholderText("Dom")
        self.ed_order_site_house_number.setMinimumWidth(90)
        self.ed_order_site_apartment_number = QLineEdit(self.grp_order)
        self.ed_order_site_apartment_number.setPlaceholderText("Mieszkanie")
        self.ed_order_site_apartment_number.setMinimumWidth(90)
        self.ed_order_site_postal_code = QLineEdit(self.grp_order)
        self.ed_order_site_postal_code.setPlaceholderText("Kod")
        self.ed_order_site_postal_code.setMinimumWidth(110)
        self.ed_order_site_city = QLineEdit(self.grp_order)
        self.ed_order_site_city.setPlaceholderText("Miasto")
        self.ed_order_site_city.setMinimumWidth(160)

        self.ed_order_notes = QTextEdit(self.grp_order)
        self.ed_order_notes.setMaximumHeight(110)

        self._order_field_cells: dict[str, QWidget] = {}
        self._order_primary_defaults = ["order_id", "code", "order_name", "status"]
        self._order_address_defaults = ["site_street", "site_house_number", "site_apartment_number", "site_postal_code", "site_city"]

        self.order_primary_splitter = QSplitter(Qt.Orientation.Horizontal, content_parent)
        self.order_primary_splitter.setChildrenCollapsible(False)
        self.order_primary_splitter.setHandleWidth(8)
        self._order_field_cells["order_id"] = self._make_client_field_cell(
            "order_id", "ID", self.ed_order_id, self.grp_order, self._on_order_field_dropped
        )
        self._order_field_cells["code"] = self._make_client_field_cell(
            "code", "Kod", self.ed_order_code, self.grp_order, self._on_order_field_dropped
        )
        self._order_field_cells["order_name"] = self._make_client_field_cell(
            "order_name", "Nazwa", self.ed_order_name, self.grp_order, self._on_order_field_dropped
        )
        self._order_field_cells["status"] = self._make_client_field_cell(
            "status", "Status", self.cb_order_status, self.grp_order, self._on_order_field_dropped
        )
        self._order_field_cells["progress"] = self._make_client_field_cell(
            "progress", "Postep", self.sp_order_progress, self.grp_order, self._on_order_field_dropped
        )
        self._apply_field_order(
            self.order_primary_splitter,
            load_ui_string_list("order_order_primary_order", self._order_primary_defaults),
            self._order_primary_defaults,
            self._order_field_cells,
        )
        self._restore_splitter_widths(
            self.order_primary_splitter,
            "order_order_primary_fields",
            [90, 130, 200, 140],
        )
        self._order_field_cells["progress"].hide()
        self.order_primary_splitter.splitterMoved.connect(
            lambda _pos, _idx: self._save_splitter_widths(self.order_primary_splitter, "order_order_primary_fields")
        )

        self.order_address_splitter = QSplitter(Qt.Orientation.Horizontal, content_parent)
        self.order_address_splitter.setChildrenCollapsible(False)
        self.order_address_splitter.setHandleWidth(8)
        self._order_field_cells["site_street"] = self._make_client_field_cell(
            "site_street", "Ulica", self.ed_order_site_street, self.grp_order, self._on_order_field_dropped
        )
        self._order_field_cells["site_house_number"] = self._make_client_field_cell(
            "site_house_number", "Dom", self.ed_order_site_house_number, self.grp_order, self._on_order_field_dropped
        )
        self._order_field_cells["site_apartment_number"] = self._make_client_field_cell(
            "site_apartment_number", "Mieszkanie", self.ed_order_site_apartment_number, self.grp_order, self._on_order_field_dropped
        )
        self._order_field_cells["site_postal_code"] = self._make_client_field_cell(
            "site_postal_code", "Kod", self.ed_order_site_postal_code, self.grp_order, self._on_order_field_dropped
        )
        self._order_field_cells["site_city"] = self._make_client_field_cell(
            "site_city", "Miasto", self.ed_order_site_city, self.grp_order, self._on_order_field_dropped
        )
        self._apply_field_order(
            self.order_address_splitter,
            load_ui_string_list("order_order_address_order", self._order_address_defaults),
            self._order_address_defaults,
            self._order_field_cells,
        )
        self._restore_splitter_widths(
            self.order_address_splitter,
            "order_order_address_fields",
            [320, 110, 120, 130, 220],
        )
        self.order_address_splitter.splitterMoved.connect(
            lambda _pos, _idx: self._save_splitter_widths(self.order_address_splitter, "order_order_address_fields")
        )

        self.order_rows_layout = QVBoxLayout()
        self.order_rows_layout.setContentsMargins(0, 2, 0, 2)
        self.order_rows_layout.setSpacing(8)
        layout.addLayout(self.order_rows_layout)

        self.order_primary_row = QWidget(content_parent)
        order_primary_row_layout = QHBoxLayout(self.order_primary_row)
        order_primary_row_layout.setContentsMargins(0, 0, 0, 0)
        order_primary_row_layout.setSpacing(6)
        order_primary_row_layout.addWidget(self.order_primary_splitter, 1)

        self.order_address_row = QWidget(content_parent)
        order_address_row_layout = QHBoxLayout(self.order_address_row)
        order_address_row_layout.setContentsMargins(0, 0, 0, 0)
        order_address_row_layout.setSpacing(6)
        order_address_row_layout.addWidget(self.order_address_splitter, 1)

        self.order_rows_layout.addWidget(self.order_primary_row)
        self.order_rows_layout.addWidget(self.order_address_row)
        self._save_order_field_orders()

        order_form = QFormLayout()
        order_form.addRow("Notatki", self.ed_order_notes)
        layout.addLayout(order_form)

        terminy_label = QLabel("Terminy projektu (wybor z kalendarza):", self.grp_order)
        terminy_label.setStyleSheet("font-weight: 700; color: #374151; margin-top: 6px;")
        layout.addWidget(terminy_label)

        terminy_form = QFormLayout()
        terminy_form.setSpacing(4)
        terminy_form.setContentsMargins(0, 0, 0, 0)

        self.ed_date_wycena = self._new_calendar_date_edit(self.grp_order)
        self.ed_date_projekt = self._new_calendar_date_edit(self.grp_order)
        self.ed_date_probki = self._new_calendar_date_edit(self.grp_order)
        self.ed_date_zakup_mat = self._new_calendar_date_edit(self.grp_order)
        self.ed_date_produkcja = self._new_calendar_date_edit(self.grp_order)
        self.ed_date_montaz = self._new_calendar_date_edit(self.grp_order)
        self.ed_date_poprawki = self._new_calendar_date_edit(self.grp_order)

        terminy_form.addRow("Wycena:", self.ed_date_wycena)
        terminy_form.addRow("Projekt:", self.ed_date_projekt)
        terminy_form.addRow("Probki materialow:", self.ed_date_probki)
        terminy_form.addRow("Zakup materialow:", self.ed_date_zakup_mat)
        terminy_form.addRow("Produkcja:", self.ed_date_produkcja)
        terminy_form.addRow("Montaz:", self.ed_date_montaz)
        terminy_form.addRow("Poprawki:", self.ed_date_poprawki)
        layout.addLayout(terminy_form)

        btn_open_calendar = QPushButton("Otworz kalendarz na date montazu", self.grp_order)
        btn_open_calendar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open_calendar.clicked.connect(self._on_open_calendar_for_montaz)
        layout.addWidget(btn_open_calendar)

    def _build_worker_group(self) -> None:
        layout = self.grp_worker.content_layout()
        content_parent = layout.parentWidget() or self.grp_worker

        self.cb_worker_name = QComboBox(self.grp_worker)
        self.cb_worker_name.setEditable(True)
        self.btn_pick_worker = QPushButton("Wybierz z bazy", self.grp_worker)
        self.btn_save_worker = QPushButton("Dodaj do bazy", self.grp_worker)
        self.btn_open_workers_base = QPushButton("Bazy", self.grp_worker)
        self._make_compact_button(self.btn_pick_worker, min_width=120, max_width=150)
        self._make_compact_button(self.btn_save_worker, min_width=120, max_width=150)
        self._make_compact_button(self.btn_open_workers_base, min_width=70, max_width=90)
        self.cb_worker_name.setMinimumWidth(260)
        if self.cb_worker_name.lineEdit() is not None:
            self.cb_worker_name.lineEdit().setPlaceholderText("[wybierz pracownika albo wpisz nowego]")
        worker_picker_row = QHBoxLayout()
        worker_picker_row.setSpacing(8)
        worker_picker_row.addWidget(QLabel("Pracownik:", self.grp_worker), 0)
        worker_picker_row.addWidget(self.cb_worker_name, 1)
        worker_picker_row.addWidget(self.btn_pick_worker, 0)
        worker_picker_row.addWidget(self.btn_save_worker, 0)
        worker_picker_row.addWidget(self.btn_open_workers_base, 0)
        worker_picker_row.addStretch(1)
        layout.addLayout(worker_picker_row)

        self.ed_worker_id = QLineEdit(self.grp_worker)
        self.ed_worker_id.setPlaceholderText("ID")
        self.ed_worker_id.setMinimumWidth(70)
        self.ed_worker_id.setReadOnly(True)
        self.ed_worker_id.setToolTip("ID nadaje sie automatycznie.")
        self.ed_worker_first_name = QLineEdit(self.grp_worker)
        self.ed_worker_first_name.setPlaceholderText("Imie")
        self.ed_worker_first_name.setMinimumWidth(120)
        self.ed_worker_last_name = QLineEdit(self.grp_worker)
        self.ed_worker_last_name.setPlaceholderText("Nazwisko")
        self.ed_worker_last_name.setMinimumWidth(140)
        self.ed_worker_name_input = QLineEdit(self.grp_worker)
        self.ed_worker_name_input.setPlaceholderText("Imie i nazwisko")
        self.ed_worker_name_input.setMinimumWidth(140)
        self.ed_worker_name_input.hide()
        self.ed_worker_role = QLineEdit(self.grp_worker)
        self.ed_worker_role.setPlaceholderText("Rola")
        self.ed_worker_role.setMinimumWidth(120)
        self.ed_worker_phone = QLineEdit(self.grp_worker)
        self.ed_worker_phone.setMinimumWidth(120)
        self.ed_worker_email = QLineEdit(self.grp_worker)
        self.ed_worker_email.setMinimumWidth(140)
        self.ed_worker_notes = QTextEdit(self.grp_worker)
        self.ed_worker_notes.setMaximumHeight(90)

        self._worker_field_cells: dict[str, QWidget] = {}
        self._worker_primary_defaults = ["worker_id", "role", "worker_first_name", "worker_last_name"]

        self.worker_primary_splitter = QSplitter(Qt.Orientation.Horizontal, content_parent)
        self.worker_primary_splitter.setChildrenCollapsible(False)
        self.worker_primary_splitter.setHandleWidth(8)
        self._worker_field_cells["worker_id"] = self._make_client_field_cell(
            "worker_id", "ID", self.ed_worker_id, self.grp_worker, self._on_worker_field_dropped
        )
        self._worker_field_cells["worker_first_name"] = self._make_client_field_cell(
            "worker_first_name", "Imie", self.ed_worker_first_name, self.grp_worker, self._on_worker_field_dropped
        )
        self._worker_field_cells["worker_last_name"] = self._make_client_field_cell(
            "worker_last_name", "Nazwisko", self.ed_worker_last_name, self.grp_worker, self._on_worker_field_dropped
        )
        self._worker_field_cells["role"] = self._make_client_field_cell(
            "role", "Rola", self.ed_worker_role, self.grp_worker, self._on_worker_field_dropped
        )
        self._worker_field_cells["phone"] = self._make_client_field_cell(
            "phone", "Telefon", self.ed_worker_phone, self.grp_worker, self._on_worker_field_dropped
        )
        self._worker_field_cells["email"] = self._make_client_field_cell(
            "email", "E-mail", self.ed_worker_email, self.grp_worker, self._on_worker_field_dropped
        )
        self._apply_field_order(
            self.worker_primary_splitter,
            load_ui_string_list("order_worker_primary_order", self._worker_primary_defaults),
            self._worker_primary_defaults,
            self._worker_field_cells,
        )
        self._restore_splitter_widths(
            self.worker_primary_splitter,
            "order_worker_primary_fields",
            [90, 180, 180, 210],
        )
        self.worker_primary_splitter.splitterMoved.connect(
            lambda _pos, _idx: self._save_splitter_widths(self.worker_primary_splitter, "order_worker_primary_fields")
        )

        self.worker_rows_layout = QVBoxLayout()
        self.worker_rows_layout.setContentsMargins(0, 2, 0, 2)
        self.worker_rows_layout.setSpacing(8)
        layout.addLayout(self.worker_rows_layout)

        self.worker_primary_row = QWidget(content_parent)
        worker_primary_row_layout = QHBoxLayout(self.worker_primary_row)
        worker_primary_row_layout.setContentsMargins(0, 0, 0, 0)
        worker_primary_row_layout.setSpacing(6)
        worker_primary_row_layout.addWidget(self.worker_primary_splitter, 1)
        self.worker_rows_layout.addWidget(self.worker_primary_row)
        self._save_worker_field_orders()

        note = QLabel("Wybierz pracownika z bazy albo wpisz nowego i przypisz role do zamowienia.")
        note.setWordWrap(True)
        note.setStyleSheet("color:#666666;")
        layout.addWidget(note)

    def _build_actions_group(self) -> None:
        layout = self.grp_actions.content_layout()

        info = QLabel("Najpierw zapisz projekt, potem przejdz dalej do Sciana albo eksportu oferty.")
        info.setWordWrap(True)
        info.setStyleSheet("color:#666666;")
        layout.addWidget(info)

        self.btn_save_draft = QPushButton("Zapisz roboczo", self.grp_actions)
        self.btn_save_new = QPushButton("Zapisz nowe", self.grp_actions)
        self.btn_overwrite_all = QPushButton("Nadpisz wszystko", self.grp_actions)
        self.btn_clear = QPushButton("Wyczysc karte", self.grp_actions)
        self.btn_go_to_sciana = QPushButton("Dalej: Sciana", self.grp_actions)
        self.btn_export_offer = QPushButton("Eksport oferte", self.grp_actions)
        self.btn_export_offer_pdf = QPushButton("Eksport PDF", self.grp_actions)

        for button in (
                self.btn_save_draft,
                self.btn_save_new,
                self.btn_overwrite_all,
                self.btn_clear,
                self.btn_go_to_sciana,
                self.btn_export_offer,
                self.btn_export_offer_pdf,
        ):
            self._make_compact_button(button, min_width=130, max_width=160)

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(self.btn_save_draft, 0)
        row.addWidget(self.btn_save_new, 0)
        row.addWidget(self.btn_overwrite_all, 0)
        row.addWidget(self.btn_clear, 0)
        row.addWidget(self.btn_go_to_sciana, 0)
        row.addWidget(self.btn_export_offer, 0)
        row.addWidget(self.btn_export_offer_pdf, 0)
        row.addStretch(1)
        layout.addLayout(row)

    def _build_walls_group(self) -> None:
        layout = self.grp_walls.content_layout()

        note = QLabel("Lista scian przypietych do tego zamowienia.")
        note.setWordWrap(True)
        note.setStyleSheet("color:#555555;")
        layout.addWidget(note)

        btns = QHBoxLayout()
        self.btn_new_wall = QPushButton("Dodaj nowa sciane", self.grp_walls)
        self.btn_open_wall = QPushButton("Otworz zaznaczona", self.grp_walls)
        self.btn_refresh_walls = QPushButton("Odswiez sciany", self.grp_walls)
        for button in (self.btn_new_wall, self.btn_open_wall, self.btn_refresh_walls):
            self._make_compact_button(button, min_width=140, max_width=170)
            btns.addWidget(button, 0)
        btns.addStretch(1)
        layout.addLayout(btns)

        self.tbl_walls = QTableWidget(0, 4, self.grp_walls)
        self.tbl_walls.setHorizontalHeaderLabels(["Sciana", "Typ", "Przeszkody", "Widok"])
        self.tbl_walls.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_walls.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_walls.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_walls.verticalHeader().setVisible(False)
        self.tbl_walls.horizontalHeader().setStretchLastSection(True)
        self.tbl_walls.setAlternatingRowColors(True)
        self.tbl_walls.setMinimumHeight(170)
        self.tbl_walls.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_walls.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_walls.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.tbl_walls)

    def _build_architect_group(self) -> None:
        layout = self.grp_architect.content_layout()

        note = QLabel("PDF-y, zrzuty i referencje od architekta lub pomiarow z ImageMeter Pro do wyceny i oferty.")
        note.setWordWrap(True)
        note.setStyleSheet("color:#555555;")
        layout.addWidget(note)

        self.ed_architect_file = QLineEdit(self.grp_architect)
        self.ed_architect_file.setPlaceholderText("Sciezka do PDF albo obrazu (architekt / ImageMeter Pro)...")
        self.btn_pick_architect_file = QPushButton("Wybierz plik", self.grp_architect)
        self.btn_import_imagemeter_files = QPushButton("Import z ImageMeter", self.grp_architect)
        self._make_compact_button(self.btn_pick_architect_file, min_width=110, max_width=130)
        self._make_compact_button(self.btn_import_imagemeter_files, min_width=160, max_width=190)
        self.cb_architect_kind = QComboBox(self.grp_architect)
        self.cb_architect_kind.addItems(["PDF", "Obraz", "Referencja"])
        self.cb_architect_kind.setMaximumWidth(140)
        self.ed_architect_description = QLineEdit(self.grp_architect)
        self.ed_architect_description.setPlaceholderText("Opis, np. Lazienka master / widok front / wizualizacja...")
        self.btn_add_architect_attachment = QPushButton("Dodaj zalacznik", self.grp_architect)
        self.btn_remove_architect_attachment = QPushButton("Usun zaznaczony", self.grp_architect)
        self._make_compact_button(self.btn_add_architect_attachment, min_width=130, max_width=160)
        self._make_compact_button(self.btn_remove_architect_attachment, min_width=130, max_width=160)

        self.tbl_architect_attachments = QTableWidget(0, 3, self.grp_architect)
        self.tbl_architect_attachments.setHorizontalHeaderLabels(["Plik", "Typ", "Opis"])
        self.tbl_architect_attachments.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_architect_attachments.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_architect_attachments.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_architect_attachments.verticalHeader().setVisible(False)
        self.tbl_architect_attachments.horizontalHeader().setStretchLastSection(True)
        self.tbl_architect_attachments.setAlternatingRowColors(True)
        self.tbl_architect_attachments.setMinimumHeight(150)
        self.tbl_architect_attachments.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_architect_attachments.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        path_row = QHBoxLayout()
        path_row.setSpacing(8)
        path_row.addWidget(self.ed_architect_file, 1)
        path_row.addWidget(self.btn_pick_architect_file, 0)
        path_row.addWidget(self.btn_import_imagemeter_files, 0)
        layout.addLayout(path_row)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(8)
        meta_row.addWidget(self.cb_architect_kind, 0)
        meta_row.addWidget(self.ed_architect_description, 1)
        layout.addLayout(meta_row)

        add_buttons = QHBoxLayout()
        add_buttons.setSpacing(8)
        add_buttons.addWidget(self.btn_add_architect_attachment, 0)
        add_buttons.addWidget(self.btn_remove_architect_attachment, 0)
        add_buttons.addStretch(1)
        layout.addLayout(add_buttons)

        layout.addWidget(self.tbl_architect_attachments)

        preview_note = QLabel(
            "Po zaznaczeniu zalacznika PDF zobaczysz miniatury stron. To bedzie baza pod pozniejsze wycinanie fragmentow do Sciana, Komplet i oferty."
        )
        preview_note.setWordWrap(True)
        preview_note.setStyleSheet("color:#555555;")
        preview_box, preview_layout = self._make_work_panel("Podglad i wycinanie", "")
        preview_layout.addWidget(preview_note)

        self.lab_architect_preview_info = QLabel("Wybierz zalacznik, aby zobaczyc podglad.")
        self.lab_architect_preview_info.setWordWrap(True)
        self.lab_architect_preview_info.setStyleSheet("color:#444444; font-weight:600;")
        preview_layout.addWidget(self.lab_architect_preview_info)

        preview_row = QHBoxLayout()

        self.lst_architect_pages = QListWidget(self.grp_architect)
        self.lst_architect_pages.setViewMode(QListWidget.ViewMode.IconMode)
        self.lst_architect_pages.setMovement(QListWidget.Movement.Static)
        self.lst_architect_pages.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.lst_architect_pages.setWrapping(True)
        self.lst_architect_pages.setIconSize(QSize(110, 150))
        self.lst_architect_pages.setGridSize(QSize(140, 190))
        self.lst_architect_pages.setMinimumHeight(210)
        self.lst_architect_pages.setMaximumHeight(230)
        self.lst_architect_pages.setUniformItemSizes(True)
        preview_row.addWidget(self.lst_architect_pages, 1)

        self.architect_crop_preview = ArchitectCropPreview(self.grp_architect)
        preview_row.addWidget(self.architect_crop_preview, 2)

        preview_layout.addLayout(preview_row)
        self.lst_architect_pages.currentRowChanged.connect(self._on_architect_preview_page_changed)

        fragment_note = QLabel(
            "Zaznacz fragment strony i zapisz go jako osobny obraz przypiety do zamowienia, Sciana, Kompletu albo oferty."
        )
        fragment_note.setWordWrap(True)
        fragment_note.setStyleSheet("color:#555555;")
        preview_layout.addWidget(fragment_note)

        fragment_row = QHBoxLayout()
        self.cb_architect_fragment_target_kind = QComboBox(self.grp_architect)
        self.cb_architect_fragment_target_kind.addItems(list(ATTACHMENT_TARGET_ITEMS))
        self.cb_architect_fragment_target_kind.setMaximumWidth(150)
        self.ed_architect_fragment_target_name = QLineEdit(self.grp_architect)
        self.ed_architect_fragment_target_name.setPlaceholderText("Nazwa celu, np. Kuchnia salon / Sciana A / Oferta klienta")
        fragment_row.addWidget(self.cb_architect_fragment_target_kind, 0)
        fragment_row.addWidget(self.ed_architect_fragment_target_name, 1)
        preview_layout.addLayout(fragment_row)

        self.ed_architect_fragment_description = QLineEdit(self.grp_architect)
        self.ed_architect_fragment_description.setPlaceholderText("Opis fragmentu, np. wizualizacja wyspy albo front szafy")
        preview_layout.addWidget(self.ed_architect_fragment_description)

        fragment_btns = QHBoxLayout()
        self.btn_save_architect_fragment = QPushButton("Zapisz zaznaczony fragment", self.grp_architect)
        self.btn_clear_architect_fragment = QPushButton("Wyczysc zaznaczenie", self.grp_architect)
        self._make_compact_button(self.btn_save_architect_fragment, min_width=180, max_width=220)
        self._make_compact_button(self.btn_clear_architect_fragment, min_width=150, max_width=180)
        fragment_btns.addWidget(self.btn_save_architect_fragment, 0)
        fragment_btns.addWidget(self.btn_clear_architect_fragment, 0)
        fragment_btns.addStretch(1)
        preview_layout.addLayout(fragment_btns)
        layout.addWidget(preview_box)
        self._set_architect_attachments([])

    def _build_quote_items_group(self) -> None:
        layout = self.grp_quote_items.content_layout()

        note = QLabel(
            "Tutaj rozbijasz zamowienie na szybkie pozycje handlowe, np. kuchnia, szafa, RTV albo lazienka."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#555555;")
        layout.addWidget(note)

        self.ed_quote_item_name = QLineEdit(self.grp_quote_items)
        self.ed_quote_item_name.setPlaceholderText("Nazwa pozycji, np. Kuchnia salon")
        self.cb_quote_item_kind = QComboBox(self.grp_quote_items)
        self.cb_quote_item_kind.addItems(list(QUOTE_ITEM_TYPES))
        self.cb_quote_item_kind.setMaximumWidth(150)
        self.sp_quote_item_quantity = QSpinBox(self.grp_quote_items)
        self.sp_quote_item_quantity.setRange(1, 999)
        self.sp_quote_item_quantity.setValue(1)
        self.sp_quote_item_quantity.setPrefix("Ilosc ")
        self.sp_quote_item_quantity.setMaximumWidth(120)
        self.ed_quote_item_description = QLineEdit(self.grp_quote_items)
        self.ed_quote_item_description.setPlaceholderText(
            "Opis / uwagi do wyceny (np. front ryflowany, wyspa, lustro)."
        )
        self.ed_quote_item_id = QLineEdit(self.grp_quote_items)
        self.ed_quote_item_id.setPlaceholderText("ID pozycji")
        self.ed_quote_item_id.setMaximumWidth(100)
        self.btn_add_quote_item = QPushButton("Dodaj pozycje", self.grp_quote_items)
        self.btn_remove_quote_item = QPushButton("Usun zaznaczona", self.grp_quote_items)
        self.btn_quote_to_sciana = QPushButton("Otworz jako Sciana", self.grp_quote_items)
        self.btn_quote_to_komplet = QPushButton("Otworz jako Komplet", self.grp_quote_items)
        self.btn_quote_set_fragment_target = QPushButton("Ustaw jako cel fragmentu", self.grp_quote_items)
        self._make_compact_button(self.btn_add_quote_item, min_width=130, max_width=160)
        self._make_compact_button(self.btn_remove_quote_item, min_width=130, max_width=160)
        self._make_compact_button(self.btn_quote_to_sciana, min_width=150, max_width=180)
        self._make_compact_button(self.btn_quote_to_komplet, min_width=150, max_width=180)
        self._make_compact_button(self.btn_quote_set_fragment_target, min_width=180, max_width=220)

        self.tbl_quote_items = QTableWidget(0, 5, self.grp_quote_items)
        self.tbl_quote_items.setHorizontalHeaderLabels(["Pozycja", "Typ", "Opis", "Ilosc", "ID"])
        self.tbl_quote_items.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_quote_items.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_quote_items.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_quote_items.verticalHeader().setVisible(False)
        self.tbl_quote_items.horizontalHeader().setStretchLastSection(True)
        self.tbl_quote_items.setAlternatingRowColors(True)
        self.tbl_quote_items.setMinimumHeight(160)
        self.tbl_quote_items.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_quote_items.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_quote_items.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_quote_items.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        entry_box, entry_layout = self._make_work_panel(
            "Nowa pozycja",
            "Tutaj wpisujesz handlowy temat wyceny, np. kuchnia, szafa albo lazienka.",
        )
        row = QHBoxLayout()
        row.addWidget(self.ed_quote_item_name, 1)
        row.addWidget(self.cb_quote_item_kind, 0)
        row.addWidget(self.sp_quote_item_quantity, 0)
        entry_layout.addLayout(row)
        entry_layout.addWidget(self.ed_quote_item_description)
        id_row = QHBoxLayout()
        id_row.addWidget(self.ed_quote_item_id, 0)
        id_row.addStretch(1)
        entry_layout.addLayout(id_row)
        entry_layout.addWidget(self.btn_add_quote_item, 0, Qt.AlignmentFlag.AlignLeft)
        top_row.addWidget(entry_box, 3)

        actions_box, actions_layout = self._make_work_panel(
            "Co dalej",
            "Wybrana pozycje otwierasz jako Sciana albo Komplet i mozesz jej przypiac fragment z PDF.",
        )
        actions_buttons = QVBoxLayout()
        actions_buttons.setSpacing(8)
        actions_buttons.addWidget(self.btn_remove_quote_item, 0)
        actions_buttons.addWidget(self.btn_quote_to_sciana, 0)
        actions_buttons.addWidget(self.btn_quote_to_komplet, 0)
        actions_buttons.addWidget(self.btn_quote_set_fragment_target, 0)
        actions_buttons.addStretch(1)
        actions_layout.addLayout(actions_buttons)
        top_row.addWidget(actions_box, 2)

        layout.addLayout(top_row)

        items_box, items_layout = self._make_work_panel(
            "Lista pozycji",
            "To sa glowne pozycje handlowe, z ktorych skladasz cala wycene klienta.",
        )
        items_layout.addWidget(self.tbl_quote_items)
        layout.addWidget(items_box)

        refs_note = QLabel(
            "Do wybranej pozycji mozesz przypinac fragmenty z PDF albo obrazy referencyjne i od razu je tutaj widziec."
        )
        refs_note.setWordWrap(True)
        refs_note.setStyleSheet("color:#555555;")

        self.tbl_quote_item_refs = QTableWidget(0, 3, self.grp_quote_items)
        self.tbl_quote_item_refs.setHorizontalHeaderLabels(["Plik", "Cel", "Opis"])
        self.tbl_quote_item_refs.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_quote_item_refs.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_quote_item_refs.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_quote_item_refs.verticalHeader().setVisible(False)
        self.tbl_quote_item_refs.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_quote_item_refs.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_quote_item_refs.horizontalHeader().setStretchLastSection(True)
        self.tbl_quote_item_refs.setAlternatingRowColors(True)
        self.tbl_quote_item_refs.setMinimumHeight(120)

        self.lab_quote_ref_info = QLabel("Brak referencji dla wybranej pozycji.")
        self.lab_quote_ref_info.setWordWrap(True)
        self.lab_quote_ref_info.setStyleSheet("color:#4b5563;")

        self.lab_quote_ref_preview = QLabel("Brak podgladu referencji pozycji.")
        self.lab_quote_ref_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lab_quote_ref_preview.setMinimumHeight(170)
        self.lab_quote_ref_preview.setStyleSheet(
            "border:1px solid #e5dccd; background:#fcfaf6; color:#6b7280; padding:6px;"
        )
        refs_box, refs_layout = self._make_work_panel("Referencje pozycji", "")
        refs_layout.addWidget(refs_note)
        refs_layout.addWidget(self.tbl_quote_item_refs)
        refs_layout.addWidget(self.lab_quote_ref_info)
        refs_layout.addWidget(self.lab_quote_ref_preview)
        layout.addWidget(refs_box)

        self.tbl_quote_item_refs.itemSelectionChanged.connect(self._on_quote_reference_selection_changed)
        self._set_quote_items([])

    def _build_material_choices_group(self) -> None:
        layout = self.grp_material_choices.content_layout()

        note = QLabel(
            "Tutaj zapisujesz pokazane probki i finalne wybory klienta: korpus, front, blat, farba, uchwyt albo inny material z kolorem i kodem."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#555555;")
        layout.addWidget(note)

        self.cb_material_scope = QComboBox(self.grp_material_choices)
        self.cb_material_scope.addItems(list(MATERIAL_SCOPE_ITEMS))
        self.cb_material_scope.setMaximumWidth(170)
        self.cb_material_choice_status = QComboBox(self.grp_material_choices)
        self.cb_material_choice_status.addItems(list(MATERIAL_CHOICE_STATUS_ITEMS))
        self.cb_material_choice_status.setMaximumWidth(180)
        self.ed_material_choice_material = QLineEdit(self.grp_material_choices)
        self.ed_material_choice_material.setPlaceholderText("Material / producent, np. Egger U702 albo lakier poliuretan")
        self.ed_material_choice_color = QLineEdit(self.grp_material_choices)
        self.ed_material_choice_color.setPlaceholderText("Kolor / dekor, np. Cashmere, dab naturalny")
        self.ed_material_choice_code = QLineEdit(self.grp_material_choices)
        self.ed_material_choice_code.setPlaceholderText("Kod, np. U702 ST9 / RAL 9016")
        self.ed_material_choice_notes = QLineEdit(self.grp_material_choices)
        self.ed_material_choice_notes.setPlaceholderText("Uwagi, np. klient wybral probke nr 2")
        self.ed_material_choice_date = QDateEdit(self.grp_material_choices)
        self.ed_material_choice_date.setCalendarPopup(True)
        self.ed_material_choice_date.setDisplayFormat("yyyy-MM-dd")
        self.ed_material_choice_date.setDate(QDate.currentDate())
        self.ed_material_choice_date.setMaximumWidth(130)
        self.btn_add_material_choice = QPushButton("Dodaj wpis", self.grp_material_choices)
        self.btn_remove_material_choice = QPushButton("Usun zaznaczony", self.grp_material_choices)
        self._make_compact_button(self.btn_add_material_choice, min_width=120, max_width=150)
        self._make_compact_button(self.btn_remove_material_choice, min_width=140, max_width=170)

        self.tbl_material_choices = QTableWidget(0, 7, self.grp_material_choices)
        self.tbl_material_choices.setHorizontalHeaderLabels(["Zakres", "Material", "Kolor", "Kod", "Status", "Data", "Uwagi"])
        self.tbl_material_choices.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_material_choices.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_material_choices.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_material_choices.verticalHeader().setVisible(False)
        self.tbl_material_choices.horizontalHeader().setStretchLastSection(True)
        self.tbl_material_choices.setAlternatingRowColors(True)
        self.tbl_material_choices.setMinimumHeight(170)
        self.tbl_material_choices.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_material_choices.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_material_choices.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_material_choices.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_material_choices.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_material_choices.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        entry_box, entry_layout = self._make_work_panel(
            "Nowy wybor klienta",
            "Tutaj zapisujesz probke albo finalny wybor materialu z kolorem, kodem i uwaga.",
        )
        row_meta = QHBoxLayout()
        row_meta.addWidget(self.cb_material_scope, 0)
        row_meta.addWidget(self.cb_material_choice_status, 0)
        row_meta.addStretch(1)
        entry_layout.addLayout(row_meta)
        row_material = QHBoxLayout()
        row_material.addWidget(self.ed_material_choice_material, 1)
        row_material.addWidget(self.ed_material_choice_color, 1)
        entry_layout.addLayout(row_material)
        row_code = QHBoxLayout()
        row_code.addWidget(self.ed_material_choice_code, 1)
        row_code.addWidget(self.ed_material_choice_date, 0)
        row_code.addWidget(self.ed_material_choice_notes, 1)
        entry_layout.addLayout(row_code)
        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        buttons.addWidget(self.btn_add_material_choice, 0)
        buttons.addWidget(self.btn_remove_material_choice, 0)
        buttons.addStretch(1)
        entry_layout.addLayout(buttons)
        top_row.addWidget(entry_box, 3)

        info_box, info_layout = self._make_work_panel(
            "Po co to zapisujemy",
            "Te dane wracaja po latach. Widzisz potem, jaki korpus, front, kolor, kod i probki byly pokazane klientowi.",
        )
        info_points = QLabel(
            "- probki i warianty\n"
            "- finalny wybor klienta\n"
            "- kod dekoru / farby / materialu\n"
            "- uwagi do zamowienia i pozniejszych poprawek"
        )
        info_points.setStyleSheet("color:#374151;")
        info_points.setWordWrap(True)
        info_layout.addWidget(info_points)
        info_layout.addStretch(1)
        top_row.addWidget(info_box, 2)

        layout.addLayout(top_row)

        history_box, history_layout = self._make_work_panel(
            "Historia probek i finalnych wyborow",
            "To jest pelna lista tego, co bylo pokazane klientowi i co zostalo wybrane.",
        )
        history_layout.addWidget(self.tbl_material_choices)
        layout.addWidget(history_box)
        self._set_material_choices([])

    def _build_customer_cash_group(self) -> None:
        layout = self.grp_customer_cash.content_layout()

        note = QLabel(
            "Tutaj zapisujesz harmonogram wplat klienta: rezerwacja terminu, start pracy, przed montazem i rozliczenie koncowe."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#555555;")
        layout.addWidget(note)

        self.cb_customer_payment_stage = QComboBox(self.grp_customer_cash)
        self.cb_customer_payment_stage.addItems(list(CUSTOMER_PAYMENT_STAGE_ITEMS))
        self.cb_customer_payment_stage.setMaximumWidth(220)
        self.sp_customer_payment_amount = QDoubleSpinBox(self.grp_customer_cash)
        self.sp_customer_payment_amount.setRange(0.0, 9_999_999.99)
        self.sp_customer_payment_amount.setDecimals(2)
        self.sp_customer_payment_amount.setSuffix(" zl")
        self.sp_customer_payment_amount.setMaximumWidth(160)
        self.chk_customer_payment_paid = QCheckBox("Oplacone", self.grp_customer_cash)

        self.ed_customer_payment_date = QDateEdit(self.grp_customer_cash)
        self.ed_customer_payment_date.setCalendarPopup(True)
        self.ed_customer_payment_date.setDisplayFormat("yyyy-MM-dd")
        self.ed_customer_payment_date.setDate(QDate.currentDate())
        self.ed_customer_payment_date.setMaximumWidth(130)

        self.ed_customer_payment_id = QLineEdit(self.grp_customer_cash)
        self.ed_customer_payment_id.setPlaceholderText("ID platnosci")
        self.ed_customer_payment_id.setMaximumWidth(100)

        self.ed_customer_payment_note = QLineEdit(self.grp_customer_cash)
        self.ed_customer_payment_note.setPlaceholderText(
            "Uwagi, np. zadatek na rezerwacje terminu / 60% po akceptacji projektu"
        )

        self.btn_customer_payment_prefill = QPushButton("Wstaw etapy", self.grp_customer_cash)
        self.btn_add_customer_payment = QPushButton("Dodaj / zapisz", self.grp_customer_cash)
        self.btn_remove_customer_payment = QPushButton("Usun zaznaczony", self.grp_customer_cash)
        self._make_compact_button(self.btn_customer_payment_prefill, min_width=110, max_width=130)
        self._make_compact_button(self.btn_add_customer_payment, min_width=120, max_width=150)
        self._make_compact_button(self.btn_remove_customer_payment, min_width=140, max_width=170)

        self.tbl_customer_payments = QTableWidget(0, 6, self.grp_customer_cash)
        self.tbl_customer_payments.setHorizontalHeaderLabels(["Etap", "Kwota", "Oplacone", "Data", "ID", "Uwagi"])
        self.tbl_customer_payments.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_customer_payments.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_customer_payments.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_customer_payments.verticalHeader().setVisible(False)
        self.tbl_customer_payments.horizontalHeader().setStretchLastSection(True)
        self.tbl_customer_payments.setAlternatingRowColors(True)
        self.tbl_customer_payments.setMinimumHeight(150)
        self.tbl_customer_payments.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_customer_payments.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_customer_payments.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_customer_payments.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_customer_payments.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        entry_box, entry_layout = self._make_work_panel(
            "Nowa wplata klienta",
            "Tutaj wpisujesz etap, kwote i status pojedynczej wplaty albo szybko wstawiasz standardowy podzial.",
        )
        row_meta = QHBoxLayout()
        row_meta.addWidget(self.cb_customer_payment_stage, 0)
        row_meta.addWidget(self.sp_customer_payment_amount, 0)
        row_meta.addWidget(self.chk_customer_payment_paid, 0)
        row_meta.addWidget(self.ed_customer_payment_date, 0)
        row_meta.addWidget(self.ed_customer_payment_id, 0)
        row_meta.addStretch(1)
        entry_layout.addLayout(row_meta)
        entry_layout.addWidget(self.ed_customer_payment_note)
        btns = QHBoxLayout()
        btns.setSpacing(8)
        btns.addWidget(self.btn_customer_payment_prefill, 0)
        btns.addWidget(self.btn_add_customer_payment, 0)
        btns.addWidget(self.btn_remove_customer_payment, 0)
        btns.addStretch(1)
        entry_layout.addLayout(btns)
        entry_layout.addStretch(1)
        top_row.addWidget(entry_box, 3)

        info_box, info_layout = self._make_work_panel(
            "Podzial platnosci",
            "Domyslnie mozesz szybko wstawic: rezerwacje terminu, start pracy, przed montazem i rozliczenie koncowe.",
        )
        info_points = QLabel(
            "- maly zadatek na rezerwacje terminu\n"
            "- glowna zaliczka po starcie pracy\n"
            "- kolejna platnosc przed montazem\n"
            "- koncowe rozliczenie po zakonczeniu"
        )
        info_points.setWordWrap(True)
        info_points.setStyleSheet("color:#374151;")
        info_layout.addWidget(info_points)
        info_layout.addStretch(1)
        top_row.addWidget(info_box, 2)

        layout.addLayout(top_row)

        history_box, history_layout = self._make_work_panel(
            "Historia wplat klienta",
            "Tutaj widzisz caly plan wplat i od razu sprawdzasz, co jest juz oplacone, a co jeszcze zostalo.",
        )
        history_layout.addWidget(self.tbl_customer_payments)
        layout.addWidget(history_box)

        self.lab_customer_cash_detail = QLabel("")
        self.lab_customer_cash_detail.setWordWrap(True)
        self.lab_customer_cash_detail.setStyleSheet(
            "color:#1f2937; background:#f8fafc; border:1px solid #dbeafe; border-radius:6px; padding:8px;"
        )
        layout.addWidget(self.lab_customer_cash_detail)
        self._set_customer_payments([])

    def _normalize_customer_payment(self, item: dict | None) -> dict[str, object] | None:
        if not isinstance(item, dict):
            return None
        stage = str(item.get("stage", "") or "").strip()
        amount = float(item.get("amount", 0.0) or 0.0)
        paid = bool(item.get("paid", False))
        date_val = str(item.get("date", "") or "").strip()
        payment_id = str(item.get("payment_id", "") or "").strip()
        note = str(item.get("note", "") or "").strip()
        if not stage and abs(amount) <= 0.0001 and not note:
            return None
        return {
            "stage": stage or "Inne",
            "amount": amount,
            "paid": paid,
            "date": date_val,
            "payment_id": payment_id,
            "note": note,
        }

    def _set_customer_payments(self, items: list[dict] | None) -> None:
        normalized: list[dict[str, object]] = []
        for item in items or []:
            entry = self._normalize_customer_payment(item)
            if entry is not None:
                normalized.append(entry)
        self._customer_payments = normalized
        self._refresh_customer_payments_table()

    def _refresh_customer_payments_table(self) -> None:
        if not hasattr(self, "tbl_customer_payments"):
            return
        self.tbl_customer_payments.setRowCount(len(self._customer_payments))
        for row, payment in enumerate(self._customer_payments):
            items = (
                QTableWidgetItem(str(payment.get("stage", "") or "Inne")),
                QTableWidgetItem(f'{float(payment.get("amount", 0.0) or 0.0):.2f} zl'),
                QTableWidgetItem("Tak" if bool(payment.get("paid", False)) else "Nie"),
                QTableWidgetItem(str(payment.get("date", "") or "")),
                QTableWidgetItem(str(payment.get("payment_id", "") or "")),
                QTableWidgetItem(str(payment.get("note", "") or "")),
            )
            for col, item in enumerate(items):
                item.setData(Qt.ItemDataRole.UserRole, row)
                self.tbl_customer_payments.setItem(row, col, item)
        self.tbl_customer_payments.resizeColumnsToContents()
        self._on_customer_payment_selection_changed()

    def _selected_customer_payment_index(self) -> int:
        selection = (
            self.tbl_customer_payments.selectionModel().selectedRows()
            if self.tbl_customer_payments.selectionModel() is not None
            else []
        )
        if not selection:
            return -1
        return int(selection[0].row())

    def _clear_customer_payment_form(self) -> None:
        if hasattr(self, "cb_customer_payment_stage"):
            self.cb_customer_payment_stage.setCurrentIndex(0)
        if hasattr(self, "sp_customer_payment_amount"):
            self.sp_customer_payment_amount.setValue(0.0)
        if hasattr(self, "chk_customer_payment_paid"):
            self.chk_customer_payment_paid.setChecked(False)
        if hasattr(self, "ed_customer_payment_date"):
            self.ed_customer_payment_date.setDate(QDate.currentDate())
        if hasattr(self, "ed_customer_payment_id"):
            self.ed_customer_payment_id.clear()
        if hasattr(self, "ed_customer_payment_note"):
            self.ed_customer_payment_note.clear()
        if hasattr(self, "btn_add_customer_payment"):
            self.btn_add_customer_payment.setText("Dodaj / zapisz")

    def _on_customer_payment_selection_changed(self) -> None:
        index = self._selected_customer_payment_index()
        if hasattr(self, "btn_remove_customer_payment"):
            self.btn_remove_customer_payment.setEnabled(index >= 0)
        if index < 0 or index >= len(self._customer_payments):
            self._clear_customer_payment_form()
            return
        payment = self._customer_payments[index]
        stage = str(payment.get("stage", "") or "Inne")
        stage_index = self.cb_customer_payment_stage.findText(stage)
        self.cb_customer_payment_stage.setCurrentIndex(stage_index if stage_index >= 0 else 0)
        self.sp_customer_payment_amount.setValue(float(payment.get("amount", 0.0) or 0.0))
        self.chk_customer_payment_paid.setChecked(bool(payment.get("paid", False)))
        self.ed_customer_payment_note.setText(str(payment.get("note", "") or ""))
        self.btn_add_customer_payment.setText("Zapisz wiersz")

    def _on_prefill_customer_payments(self) -> None:
        today = QDate.currentDate().toString("yyyy-MM-dd")
        self._set_customer_payments(
            [
                {"stage": "Rezerwacja terminu", "amount": 0.0, "paid": False, "date": today, "payment_id": f"PAY-001", "note": "Pierwszy zadatek klienta"},
                {"stage": "Start pracy / 60%", "amount": 0.0, "paid": False, "date": today, "payment_id": f"PAY-002", "note": "Po starcie realizacji"},
                {"stage": "Przed montazem / 20%", "amount": 0.0, "paid": False, "date": today, "payment_id": f"PAY-003", "note": "Przed wyjazdem na montaz"},
                {"stage": "Koniec / 10%", "amount": 0.0, "paid": False, "date": today, "payment_id": f"PAY-004", "note": "Rozliczenie koncowe"},
            ]
        )
        self._refresh_summary()
        self._set_status("Wstawiono standardowy harmonogram wplat klienta.", ok=True)

    def _on_add_customer_payment(self) -> None:
        payment_id = self.ed_customer_payment_id.text().strip()
        if not payment_id:
            payment_id = f"PAY-{datetime.now().strftime('%y%m%d%H%M%S')}"
        entry = self._normalize_customer_payment(
            {
                "stage": self.cb_customer_payment_stage.currentText().strip(),
                "amount": float(self.sp_customer_payment_amount.value()),
                "paid": bool(self.chk_customer_payment_paid.isChecked()),
                "date": self.ed_customer_payment_date.date().toString("yyyy-MM-dd"),
                "payment_id": payment_id,
                "note": self.ed_customer_payment_note.text().strip(),
            }
        )
        if entry is None:
            self._set_status("Wpisz etap albo kwote wplaty klienta.", ok=False)
            return
        index = self._selected_customer_payment_index()
        if 0 <= index < len(self._customer_payments):
            self._customer_payments[index] = entry
            message = "Zaktualizowano wplate klienta."
        else:
            self._customer_payments.append(entry)
            message = "Dodano wplate klienta."
        self._refresh_customer_payments_table()
        self._clear_customer_payment_form()
        self._refresh_summary()
        self._set_status(message, ok=True)

    def _on_remove_customer_payment(self) -> None:
        index = self._selected_customer_payment_index()
        if index < 0 or index >= len(self._customer_payments):
            self._set_status("Wybierz wplate klienta do usuniecia.", ok=False)
            return
        self._customer_payments.pop(index)
        self._refresh_customer_payments_table()
        self._clear_customer_payment_form()
        self._refresh_summary()
        self._set_status("Usunieto wpis harmonogramu wplat klienta.", ok=True)

    def _normalize_attachment(self, item: dict | None) -> dict[str, str] | None:
        if not isinstance(item, dict):
            return None
        path = str(item.get("path", "") or "").strip()
        kind = str(item.get("kind", "") or "").strip() or "PDF"
        description = str(item.get("description", "") or "").strip()
        target_kind = str(item.get("target_kind", "") or "").strip()
        target_name = str(item.get("target_name", "") or "").strip()
        source_path = str(item.get("source_path", "") or "").strip()
        source_page = str(item.get("source_page", "") or "").strip()
        source_app = str(item.get("source_app", "") or "").strip()
        if not path:
            return None
        return {
            "path": path,
            "kind": kind,
            "description": description,
            "target_kind": target_kind,
            "target_name": target_name,
            "source_path": source_path,
            "source_page": source_page,
            "source_app": source_app,
        }

    def _set_architect_attachments(self, items: list[dict] | None) -> None:
        normalized: list[dict[str, str]] = []
        for item in items or []:
            entry = self._normalize_attachment(item)
            if entry is not None:
                normalized.append(entry)
        self._architect_attachments = normalized
        self._refresh_architect_attachments_table()

    def _refresh_architect_attachments_table(self) -> None:
        if not hasattr(self, "tbl_architect_attachments"):
            return
        self.tbl_architect_attachments.setRowCount(len(self._architect_attachments))
        for row, attachment in enumerate(self._architect_attachments):
            file_name = Path(str(attachment.get("path", "") or "")).name or str(attachment.get("path", "") or "")
            target_kind = str(attachment.get("target_kind", "") or "").strip()
            target_name = str(attachment.get("target_name", "") or "").strip()
            description = str(attachment.get("description", "") or "")
            if target_kind and target_name:
                description = f"{description}\nCel: {target_kind} / {target_name}".strip()
            elif target_kind:
                description = f"{description}\nCel: {target_kind}".strip()
            items = (
                QTableWidgetItem(file_name),
                QTableWidgetItem(str(attachment.get("kind", "") or "PDF")),
                QTableWidgetItem(description),
            )
            for col, item in enumerate(items):
                item.setData(Qt.ItemDataRole.UserRole, str(attachment.get("path", "") or ""))
                item.setToolTip(str(attachment.get("path", "") or ""))
                self.tbl_architect_attachments.setItem(row, col, item)
        self.tbl_architect_attachments.resizeColumnsToContents()
        self._on_architect_attachment_selection_changed()

    def _selected_architect_attachment_index(self) -> int:
        selection = (
            self.tbl_architect_attachments.selectionModel().selectedRows()
            if self.tbl_architect_attachments.selectionModel() is not None
            else []
        )
        if not selection:
            return -1
        return int(selection[0].row())

    def _on_architect_attachment_selection_changed(self) -> None:
        selected_index = self._selected_architect_attachment_index()
        if hasattr(self, "btn_remove_architect_attachment"):
            self.btn_remove_architect_attachment.setEnabled(selected_index >= 0)
        self._load_selected_architect_preview()

    def _on_pick_architect_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Wybierz zalacznik od architekta",
            "",
            "Pliki PDF i obrazy (*.pdf *.png *.jpg *.jpeg *.bmp);;Wszystkie pliki (*.*)",
        )
        if not file_path:
            return
        self.ed_architect_file.setText(str(file_path))

    @staticmethod
    def _is_imagemeter_supported_path(path_str: str) -> bool:
        suffix = Path(str(path_str or "").strip()).suffix.lower()
        return suffix in set(IMAGEMETER_IMAGE_SUFFIXES + IMAGEMETER_PDF_SUFFIXES)

    def _import_imagemeter_paths(self, paths: list[str]) -> tuple[int, int, int]:
        imported = 0
        skipped = 0
        duplicates = 0
        existing_paths = {
            str(item.get("path", "") or "").strip()
            for item in list(getattr(self, "_architect_attachments", []) or [])
            if str(item.get("path", "") or "").strip()
        }

        for raw_path in paths:
            path = str(raw_path or "").strip()
            if not path:
                skipped += 1
                continue
            if not self._is_imagemeter_supported_path(path):
                skipped += 1
                continue
            if path in existing_paths:
                duplicates += 1
                continue

            entry = self._normalize_attachment(
                {
                    "path": path,
                    "kind": "ImageMeter Pro",
                    "description": "ImageMeter Pro - pomiar",
                }
            )
            if entry is None:
                skipped += 1
                continue

            entry["source_app"] = "ImageMeter Pro"
            self._architect_attachments.append(entry)
            existing_paths.add(path)
            imported += 1

        if imported > 0:
            self._refresh_architect_attachments_table()
            self._refresh_summary()

        return imported, skipped, duplicates

    def _on_import_imagemeter_files(self) -> None:
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Import z ImageMeter Pro",
            "",
            "Pliki ImageMeter (*.pdf *.png *.jpg *.jpeg *.bmp *.webp *.heic *.heif);;Wszystkie pliki (*.*)",
        )
        if not file_paths:
            return

        imported, skipped, duplicates = self._import_imagemeter_paths([str(path) for path in file_paths])
        if imported <= 0:
            self._set_status(
                f"Nie zaimportowano plikow z ImageMeter. Pominiete: {skipped}, duplikaty: {duplicates}.",
                ok=False,
            )
            return

        self._set_status(
            f"Import ImageMeter Pro: dodano {imported}, pominieto {skipped}, duplikaty {duplicates}.",
            ok=True,
        )

    def _on_add_architect_attachment(self) -> None:
        path = str(self.ed_architect_file.text().strip())
        if not path:
            self._set_status("Wybierz plik albo wpisz sciezke do zalacznika od architekta.", ok=False)
            return
        entry = self._normalize_attachment(
            {
                "path": path,
                "kind": self.cb_architect_kind.currentText().strip() or "PDF",
                "description": self.ed_architect_description.text().strip(),
            }
        )
        if entry is None:
            self._set_status("Nie udalo sie dodac zalacznika.", ok=False)
            return
        if any(str(item.get("path", "") or "") == entry["path"] for item in self._architect_attachments):
            self._set_status("Ten zalacznik jest juz przypiety do zamowienia.", ok=False)
            return
        self._architect_attachments.append(entry)
        self.ed_architect_file.clear()
        self.ed_architect_description.clear()
        self._refresh_architect_attachments_table()
        self._refresh_summary()
        self._set_status("Dodano zalacznik od architekta.", ok=True)

    def _on_remove_architect_attachment(self) -> None:
        index = self._selected_architect_attachment_index()
        if index < 0 or index >= len(self._architect_attachments):
            self._set_status("Wybierz zalacznik do usuniecia.", ok=False)
            return
        self._architect_attachments.pop(index)
        self._refresh_architect_attachments_table()
        self._refresh_summary()
        self._set_status("Usunieto zalacznik od architekta.", ok=True)

    def _clear_architect_preview(self, message: str = "Wybierz zalacznik, aby zobaczyc podglad.") -> None:
        self._architect_preview_pages = []
        self._architect_preview_header = ""
        if hasattr(self, "lst_architect_pages"):
            self.lst_architect_pages.clear()
        if hasattr(self, "lab_architect_preview_info"):
            self.lab_architect_preview_info.setText(message)
        if hasattr(self, "architect_crop_preview"):
            self.architect_crop_preview.set_source_pixmap(None, message)

    def _selected_architect_attachment(self) -> dict[str, str] | None:
        index = self._selected_architect_attachment_index()
        if index < 0 or index >= len(self._architect_attachments):
            return None
        return dict(self._architect_attachments[index])

    def _load_selected_architect_preview(self) -> None:
        attachment = self._selected_architect_attachment()
        if attachment is None:
            self._clear_architect_preview()
            return

        path = Path(str(attachment.get("path", "") or "").strip())
        if not path.exists():
            self._clear_architect_preview("Nie znaleziono pliku zalacznika.")
            return

        kind = str(attachment.get("kind", "") or "").strip() or "PDF"
        suffix = path.suffix.lower()

        if kind == "PDF" or suffix == ".pdf":
            self._load_architect_pdf_preview(path)
            return
        if kind == "Obraz" or suffix in {".png", ".jpg", ".jpeg", ".bmp"}:
            self._load_architect_image_preview(path)
            return

        self._clear_architect_preview("Referencja nie ma jeszcze podgladu wizualnego.")

    def _load_architect_pdf_preview(self, path: Path) -> None:
        pages = self._build_pdf_page_previews(path)
        if not pages:
            self._clear_architect_preview("Nie udalo sie odczytac stron PDF.")
            return

        self._architect_preview_pages = pages
        self._architect_preview_header = f"{path.name} | PDF | {len(pages)} stron"
        self.lst_architect_pages.clear()
        for page in pages:
            item = QListWidgetItem(str(page.get("label", "") or "Strona"))
            thumb = page.get("thumb")
            if isinstance(thumb, QPixmap) and not thumb.isNull():
                item.setIcon(QIcon(thumb))
            item.setData(Qt.ItemDataRole.UserRole, int(page.get("index", 0) or 0))
            self.lst_architect_pages.addItem(item)
        self.lab_architect_preview_info.setText(self._architect_preview_header)
        self.lst_architect_pages.setCurrentRow(0)

    def _load_architect_image_preview(self, path: Path) -> None:
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self._clear_architect_preview("Nie udalo sie odczytac obrazu.")
            return
        thumb = pixmap.scaled(110, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        full = pixmap.scaled(640, 420, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self._architect_preview_pages = [
            {
                "index": 0,
                "label": "Obraz",
                "thumb": thumb,
                "full": full,
            }
        ]
        self._architect_preview_header = f"{path.name} | Obraz"
        self.lst_architect_pages.clear()
        item = QListWidgetItem("Obraz")
        item.setIcon(QIcon(thumb))
        item.setData(Qt.ItemDataRole.UserRole, 0)
        self.lst_architect_pages.addItem(item)
        self.lab_architect_preview_info.setText(self._architect_preview_header)
        self.lst_architect_pages.setCurrentRow(0)

    def _build_pdf_page_previews(self, path: Path) -> list[dict[str, object]]:
        document = QPdfDocument(self)
        error = document.load(str(path))
        if error != QPdfDocument.Error.None_:
            return []

        pages: list[dict[str, object]] = []
        for page_index in range(document.pageCount()):
            thumb_image = document.render(page_index, QSize(110, 150))
            full_image = document.render(page_index, QSize(640, 420))
            thumb = QPixmap.fromImage(thumb_image)
            full = QPixmap.fromImage(full_image)
            label = str(document.pageLabel(page_index) or f"Strona {page_index + 1}")
            pages.append(
                {
                    "index": page_index,
                    "label": label,
                    "thumb": thumb,
                    "full": full,
                }
            )
        return pages

    def _on_architect_preview_page_changed(self, current_row: int) -> None:
        if current_row < 0 or current_row >= len(self._architect_preview_pages):
            if hasattr(self, "architect_crop_preview") and not self._architect_preview_pages:
                self.architect_crop_preview.set_source_pixmap(None, "Brak podgladu strony.")
            return

        page = self._architect_preview_pages[current_row]
        pixmap = page.get("full")
        label = str(page.get("label", "") or "")
        if isinstance(pixmap, QPixmap) and not pixmap.isNull():
            self.architect_crop_preview.set_source_pixmap(pixmap, "")
        else:
            self.architect_crop_preview.set_source_pixmap(None, "Brak podgladu strony.")
        if self._architect_preview_header:
            self.lab_architect_preview_info.setText(f"{self._architect_preview_header} | {label}")

    def _current_preview_page(self) -> dict[str, object] | None:
        row = int(self.lst_architect_pages.currentRow()) if hasattr(self, "lst_architect_pages") else -1
        if row < 0 or row >= len(self._architect_preview_pages):
            return None
        return self._architect_preview_pages[row]

    def _attachments_output_dir(self) -> Path:
        env = os.environ.get("TECH_MODUL_DATA_DIR", "").strip()
        root = Path(env) if env else Path(__file__).resolve().parents[3] / "data"
        output = root / "architect_fragments"
        output.mkdir(parents=True, exist_ok=True)
        return output

    def _offer_output_dir(self) -> Path:
        env = os.environ.get("TECH_MODUL_DATA_DIR", "").strip()
        root = Path(env) if env else Path(__file__).resolve().parents[3] / "data"
        output = root / "offers"
        output.mkdir(parents=True, exist_ok=True)
        return output

    def _image_file_to_data_uri(self, path_str: str) -> str:
        path = Path(str(path_str or "").strip())
        if not path.exists() or not path.is_file():
            return ""
        mime_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".bmp": "image/bmp",
            ".webp": "image/webp",
        }
        mime = mime_map.get(path.suffix.lower())
        if not mime:
            return ""
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{data}"

    def _append_architect_attachment(self, entry: dict[str, str]) -> None:
        normalized = self._normalize_attachment(entry)
        if normalized is None:
            return
        self._architect_attachments.append(normalized)
        self._refresh_architect_attachments_table()
        self._refresh_summary()

    def _on_save_architect_fragment(self) -> None:
        attachment = self._selected_architect_attachment()
        if attachment is None:
            self._set_status("Wybierz zalacznik, z ktorego chcesz wyciac fragment.", ok=False)
            return
        page = self._current_preview_page()
        if page is None:
            self._set_status("Wybierz strone albo obraz do wyciecia fragmentu.", ok=False)
            return
        if not self.architect_crop_preview.has_selection():
            self._set_status("Zaznacz myszka fragment na podgladzie.", ok=False)
            return

        cropped = self.architect_crop_preview.selected_source_pixmap()
        if cropped.isNull():
            self._set_status("Nie udalo sie wyciac zaznaczonego fragmentu.", ok=False)
            return

        order_code = str(self.ed_order_code.text().strip() or "draft")
        target_kind = str(self.cb_architect_fragment_target_kind.currentText().strip() or "Zamowienie")
        target_name = str(self.ed_architect_fragment_target_name.text().strip())
        description = str(self.ed_architect_fragment_description.text().strip())
        source_path = str(attachment.get("path", "") or "").strip()
        source_page = str(page.get("label", "") or "")
        safe_order = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in order_code) or "draft"
        safe_target = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in (target_name or target_kind)) or "fragment"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        output_path = self._attachments_output_dir() / f"{safe_order}_{safe_target}_{timestamp}.png"

        if not cropped.save(str(output_path), "PNG"):
            self._set_status("Nie udalo sie zapisac fragmentu jako obrazu.", ok=False)
            return

        description_parts = [description or "Fragment z PDF"]
        if source_page:
            description_parts.append(source_page)
        self._append_architect_attachment(
            {
                "path": str(output_path),
                "kind": "Obraz",
                "description": " | ".join(part for part in description_parts if part),
                "target_kind": target_kind,
                "target_name": target_name,
                "source_path": source_path,
                "source_page": source_page,
            }
        )
        self.ed_architect_fragment_description.clear()
        self.architect_crop_preview.clear_selection()
        self._set_status("Zapisano zaznaczony fragment z PDF.", ok=True)

    def _normalize_quote_item(self, item: dict | None) -> dict[str, str] | None:
        if not isinstance(item, dict):
            return None
        name = str(item.get("name", "") or "").strip()
        kind = str(item.get("kind", "") or "").strip() or "Inne"
        description = str(item.get("description", "") or "").strip()
        try:
            quantity = int(float(item.get("quantity", item.get("qty", 1)))) or 1
        except Exception:
            quantity = 1
        quantity = max(1, quantity)
        quote_item_id = str(item.get("quote_item_id", "") or "").strip()
        if not name:
            return None
        return {
            "name": name,
            "kind": kind,
            "description": description,
            "quantity": str(quantity),
            "quote_item_id": quote_item_id,
        }

    def _set_quote_items(self, items: list[dict] | None) -> None:
        normalized: list[dict[str, str]] = []
        for item in items or []:
            entry = self._normalize_quote_item(item)
            if entry is not None:
                normalized.append(entry)
        self._quote_items = normalized
        self._refresh_quote_items_table()

    def _refresh_quote_items_table(self) -> None:
        if not hasattr(self, "tbl_quote_items"):
            return
        self.tbl_quote_items.setRowCount(len(self._quote_items))
        for row, quote_item in enumerate(self._quote_items):
            items = (
                QTableWidgetItem(str(quote_item.get("name", "") or "")),
                QTableWidgetItem(str(quote_item.get("kind", "") or "Inne")),
                QTableWidgetItem(str(quote_item.get("description", "") or "")),
                QTableWidgetItem(str(quote_item.get("quantity", "") or "1")),
                QTableWidgetItem(str(quote_item.get("quote_item_id", "") or "")),
            )
            for col, item in enumerate(items):
                item.setData(Qt.ItemDataRole.UserRole, str(quote_item.get("name", "") or ""))
                self.tbl_quote_items.setItem(row, col, item)
        self.tbl_quote_items.resizeColumnsToContents()
        self._on_quote_item_selection_changed()

    def _selected_quote_item_index(self) -> int:
        selection = (
            self.tbl_quote_items.selectionModel().selectedRows()
            if self.tbl_quote_items.selectionModel() is not None
            else []
        )
        if not selection:
            return -1
        return int(selection[0].row())

    def _on_quote_item_selection_changed(self) -> None:
        has_selection = self._selected_quote_item_index() >= 0
        if hasattr(self, "btn_remove_quote_item"):
            self.btn_remove_quote_item.setEnabled(has_selection)
        if hasattr(self, "btn_quote_to_sciana"):
            self.btn_quote_to_sciana.setEnabled(has_selection)
        if hasattr(self, "btn_quote_to_komplet"):
            self.btn_quote_to_komplet.setEnabled(has_selection)
        if hasattr(self, "btn_quote_set_fragment_target"):
            self.btn_quote_set_fragment_target.setEnabled(has_selection)
        self._refresh_quote_item_references()

    def _on_add_quote_item(self) -> None:
        quote_item_id = self.ed_quote_item_id.text().strip()
        if not quote_item_id:
            quote_item_id = f"Q-{datetime.now().strftime('%y%m%d%H%M%S')}"
        entry = self._normalize_quote_item(
            {
                "name": self.ed_quote_item_name.text().strip(),
                "kind": self.cb_quote_item_kind.currentText().strip() or "Inne",
                "description": self.ed_quote_item_description.text().strip(),
                "quantity": int(self.sp_quote_item_quantity.value()),
                "quote_item_id": quote_item_id,
            }
        )
        if entry is None:
            self._set_status("Podaj nazwe pozycji do wyceny.", ok=False)
            return
        self._quote_items.append(entry)
        self.ed_quote_item_name.clear()
        self.ed_quote_item_description.clear()
        self.ed_quote_item_id.clear()
        self.sp_quote_item_quantity.setValue(1)
        self._refresh_quote_items_table()
        self._refresh_summary()
        self._set_status("Dodano pozycje do wyceny.", ok=True)

    def _on_remove_quote_item(self) -> None:
        index = self._selected_quote_item_index()
        if index < 0 or index >= len(self._quote_items):
            self._set_status("Wybierz pozycje do usuniecia.", ok=False)
            return
        self._quote_items.pop(index)
        self._refresh_quote_items_table()
        self._refresh_summary()
        self._set_status("Usunieto pozycje do wyceny.", ok=True)

    def _selected_quote_item(self) -> dict[str, str] | None:
        index = self._selected_quote_item_index()
        if index < 0 or index >= len(self._quote_items):
            return None
        return dict(self._quote_items[index])

    def _quote_item_context(self) -> dict[str, str] | None:
        quote_item = self._selected_quote_item()
        if quote_item is None:
            return None
        payload = dict(self.current_order_context())
        payload["quote_item_name"] = str(quote_item.get("name", "") or "").strip()
        payload["quote_item_kind"] = str(quote_item.get("kind", "") or "Inne").strip() or "Inne"
        payload["quote_item_description"] = str(quote_item.get("description", "") or "").strip()
        payload["quote_item_quantity"] = int(float(quote_item.get("quantity", 1) or 1))
        return payload

    def _open_selected_quote_item(self, target: str) -> None:
        payload = self._quote_item_context()
        if payload is None:
            self._set_status("Wybierz pozycje do wyceny.", ok=False)
            return

        ok, message = self._ensure_context_saved_for_next_step()
        if not ok:
            self._set_status(message, ok=False)
            return

        self._save_draft(show_status=False)
        quote_name = str(payload.get("quote_item_name", "") or "").strip() or "pozycje"
        if target == "komplet":
            if message:
                self._set_status(message, ok=True)
            self.sig_open_komplet_requested.emit(payload)
            self._set_status(f'Otwieram pozycje "{quote_name}" jako komplet.', ok=True)
            return

        if message:
            self._set_status(message, ok=True)
        self.sig_open_sciana_requested.emit(payload)
        self._set_status(f'Otwieram pozycje "{quote_name}" jako sciane.', ok=True)

    def _on_open_quote_item_as_sciana(self) -> None:
        self._open_selected_quote_item("sciana")

    def _on_open_quote_item_as_komplet(self) -> None:
        self._open_selected_quote_item("komplet")

    def _on_use_quote_item_as_fragment_target(self) -> None:
        quote_item = self._selected_quote_item()
        if quote_item is None:
            self._set_status("Wybierz pozycje do wyceny.", ok=False)
            return
        self.cb_architect_fragment_target_kind.setCurrentText("Pozycja do wyceny")
        self.ed_architect_fragment_target_name.setText(str(quote_item.get("name", "") or "").strip())
        if not self.ed_architect_fragment_description.text().strip():
            kind = str(quote_item.get("kind", "") or "Pozycja").strip()
            self.ed_architect_fragment_description.setText(f"Referencja dla pozycji: {kind}")
        self.grp_architect.set_expanded(True)
        self.ed_architect_fragment_description.setFocus()
        self._set_status(
            f'Ustawiono pozycje "{str(quote_item.get("name", "") or "").strip()}" jako cel fragmentu.',
            ok=True,
        )

    def _collect_quote_item_reference_attachments(self, quote_item_name: str) -> list[dict[str, str]]:
        normalized_name = str(quote_item_name or "").strip()
        if not normalized_name:
            return []
        results: list[dict[str, str]] = []
        seen_paths: set[str] = set()
        for attachment in list(self._architect_attachments):
            path = str(attachment.get("path", "") or "").strip()
            if not path or path in seen_paths:
                continue
            kind = str(attachment.get("kind", "") or "").strip().lower()
            suffix = Path(path).suffix.lower()
            if kind not in {"obraz", "referencja"} and suffix not in {".png", ".jpg", ".jpeg", ".bmp", ".webp"}:
                continue
            target_kind = str(attachment.get("target_kind", "") or "").strip().lower()
            target_name = str(attachment.get("target_name", "") or "").strip()
            if target_kind != "pozycja do wyceny" or target_name != normalized_name:
                continue
            seen_paths.add(path)
            results.append(
                {
                    "path": path,
                    "target": target_name,
                    "description": str(attachment.get("description", "") or "").strip(),
                }
            )
        return results

    def _selected_quote_reference_path(self) -> str:
        selection = (
            self.tbl_quote_item_refs.selectionModel().selectedRows()
            if hasattr(self, "tbl_quote_item_refs") and self.tbl_quote_item_refs.selectionModel() is not None
            else []
        )
        if not selection:
            return ""
        item = self.tbl_quote_item_refs.item(int(selection[0].row()), 0)
        if item is None:
            return ""
        return str(item.data(Qt.ItemDataRole.UserRole) or "").strip()

    def _refresh_quote_item_references(self) -> None:
        if not hasattr(self, "tbl_quote_item_refs"):
            return
        quote_item = self._selected_quote_item()
        selected_path = self._selected_quote_reference_path()
        quote_name = str(quote_item.get("name", "") or "").strip() if quote_item else ""
        self._quote_reference_items = self._collect_quote_item_reference_attachments(quote_name)
        self.tbl_quote_item_refs.setRowCount(len(self._quote_reference_items))
        for row, entry in enumerate(self._quote_reference_items):
            path_item = QTableWidgetItem(Path(str(entry.get("path", "") or "")).name)
            path_item.setData(Qt.ItemDataRole.UserRole, str(entry.get("path", "") or ""))
            target_item = QTableWidgetItem(str(entry.get("target", "") or quote_name or "-"))
            description_item = QTableWidgetItem(str(entry.get("description", "") or "-"))
            self.tbl_quote_item_refs.setItem(row, 0, path_item)
            self.tbl_quote_item_refs.setItem(row, 1, target_item)
            self.tbl_quote_item_refs.setItem(row, 2, description_item)
        self.tbl_quote_item_refs.resizeColumnsToContents()

        if self._quote_reference_items:
            target_row = 0
            if selected_path:
                for row in range(self.tbl_quote_item_refs.rowCount()):
                    item = self.tbl_quote_item_refs.item(row, 0)
                    if item is not None and str(item.data(Qt.ItemDataRole.UserRole) or "") == selected_path:
                        target_row = row
                        break
            self.tbl_quote_item_refs.selectRow(target_row)
            return

        self.tbl_quote_item_refs.clearSelection()
        self._quote_reference_pixmap = QPixmap()
        if quote_name:
            self.lab_quote_ref_info.setText(f'Brak referencji dla pozycji "{quote_name}".')
        else:
            self.lab_quote_ref_info.setText("Brak referencji dla wybranej pozycji.")
        self.lab_quote_ref_preview.setPixmap(QPixmap())
        self.lab_quote_ref_preview.setText("Brak podgladu referencji pozycji.")

    def _update_quote_reference_preview(self) -> None:
        if self._quote_reference_pixmap.isNull():
            self.lab_quote_ref_preview.setPixmap(QPixmap())
            return
        target_size = self.lab_quote_ref_preview.size()
        scaled = self._quote_reference_pixmap.scaled(
            max(40, target_size.width() - 12),
            max(40, target_size.height() - 12),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.lab_quote_ref_preview.setPixmap(scaled)

    def _on_quote_reference_selection_changed(self) -> None:
        selection = (
            self.tbl_quote_item_refs.selectionModel().selectedRows()
            if hasattr(self, "tbl_quote_item_refs") and self.tbl_quote_item_refs.selectionModel() is not None
            else []
        )
        if not selection:
            quote_item = self._selected_quote_item()
            quote_name = str(quote_item.get("name", "") or "").strip() if quote_item else ""
            self._quote_reference_pixmap = QPixmap()
            self.lab_quote_ref_info.setText(
                f'Brak referencji dla pozycji "{quote_name}".' if quote_name else "Brak referencji dla wybranej pozycji."
            )
            self.lab_quote_ref_preview.setPixmap(QPixmap())
            self.lab_quote_ref_preview.setText("Brak podgladu referencji pozycji.")
            return
        row = int(selection[0].row())
        if row < 0 or row >= len(self._quote_reference_items):
            return
        entry = self._quote_reference_items[row]
        path = str(entry.get("path", "") or "").strip()
        info_parts = [
            Path(path).name,
            str(entry.get("target", "") or "").strip(),
            str(entry.get("description", "") or "").strip(),
        ]
        self.lab_quote_ref_info.setText(" | ".join(part for part in info_parts if part))
        pixmap = QPixmap(path)
        if pixmap.isNull():
            self._quote_reference_pixmap = QPixmap()
            self.lab_quote_ref_preview.setPixmap(QPixmap())
            self.lab_quote_ref_preview.setText("Nie udalo sie odczytac obrazu pozycji.")
            return
        self._quote_reference_pixmap = pixmap
        self.lab_quote_ref_preview.setText("")
        self._update_quote_reference_preview()

    def _normalize_material_choice(self, item: dict | None) -> dict[str, str] | None:
        if not isinstance(item, dict):
            return None
        scope = str(item.get("scope", "") or "").strip() or "Inne"
        material = str(item.get("material", "") or "").strip()
        color = str(item.get("color", "") or "").strip()
        code = str(item.get("code", "") or "").strip()
        status = str(item.get("status", "") or "").strip() or "Probka pokazana"
        date_val = str(item.get("date", "") or "").strip()
        notes = str(item.get("notes", "") or "").strip()
        if not any((scope, material, color, code, status, notes)):
            return None
        return {
            "scope": scope,
            "material": material,
            "color": color,
            "code": code,
            "status": status,
            "date": date_val,
            "notes": notes,
        }

    def _set_material_choices(self, items: list[dict] | None) -> None:
        normalized: list[dict[str, str]] = []
        for item in items or []:
            entry = self._normalize_material_choice(item)
            if entry is not None:
                normalized.append(entry)
        self._material_choices = normalized
        self._refresh_material_choices_table()

    def _refresh_material_choices_table(self) -> None:
        if not hasattr(self, "tbl_material_choices"):
            return
        self.tbl_material_choices.setRowCount(len(self._material_choices))
        for row, entry in enumerate(self._material_choices):
            items = (
                QTableWidgetItem(str(entry.get("scope", "") or "Inne")),
                QTableWidgetItem(str(entry.get("material", "") or "")),
                QTableWidgetItem(str(entry.get("color", "") or "")),
                QTableWidgetItem(str(entry.get("code", "") or "")),
                QTableWidgetItem(str(entry.get("status", "") or "Probka pokazana")),
                QTableWidgetItem(str(entry.get("date", "") or "")),
                QTableWidgetItem(str(entry.get("notes", "") or "")),
            )
            for col, item in enumerate(items):
                item.setData(Qt.ItemDataRole.UserRole, f"{entry.get('scope','')}|{entry.get('material','')}")
                self.tbl_material_choices.setItem(row, col, item)
        self.tbl_material_choices.resizeColumnsToContents()
        self._on_material_choice_selection_changed()

    def _selected_material_choice_index(self) -> int:
        selection = (
            self.tbl_material_choices.selectionModel().selectedRows()
            if self.tbl_material_choices.selectionModel() is not None
            else []
        )
        if not selection:
            return -1
        return int(selection[0].row())

    def _on_material_choice_selection_changed(self) -> None:
        if hasattr(self, "btn_remove_material_choice"):
            self.btn_remove_material_choice.setEnabled(self._selected_material_choice_index() >= 0)

    def _on_add_material_choice(self) -> None:
        entry = self._normalize_material_choice(
            {
                "scope": self.cb_material_scope.currentText().strip() or "Inne",
                "material": self.ed_material_choice_material.text().strip(),
                "color": self.ed_material_choice_color.text().strip(),
                "code": self.ed_material_choice_code.text().strip(),
                "status": self.cb_material_choice_status.currentText().strip() or "Probka pokazana",
                "date": self.ed_material_choice_date.date().toString("yyyy-MM-dd"),
                "notes": self.ed_material_choice_notes.text().strip(),
            }
        )
        if entry is None:
            self._set_status("Podaj dane probki albo finalnego materialu.", ok=False)
            return
        self._material_choices.append(entry)
        self.ed_material_choice_material.clear()
        self.ed_material_choice_color.clear()
        self.ed_material_choice_code.clear()
        self.ed_material_choice_notes.clear()
        self.ed_material_choice_date.setDate(QDate.currentDate())
        self._refresh_material_choices_table()
        self._refresh_summary()
        self._set_status("Dodano wpis probki / materialu.", ok=True)

    def _on_remove_material_choice(self) -> None:
        index = self._selected_material_choice_index()
        if index < 0 or index >= len(self._material_choices):
            self._set_status("Wybierz wpis probki / materialu do usuniecia.", ok=False)
            return
        self._material_choices.pop(index)
        self._refresh_material_choices_table()
        self._refresh_summary()
        self._set_status("Usunieto wpis probki / materialu.", ok=True)

    def _build_summary_group(self) -> None:
        layout = self.grp_summary.content_layout()

        note = QLabel(
            "Szybki podglad calego zamowienia: sciany, komplety, koszt laczny i materialy."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#555555;")
        layout.addWidget(note)

        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(10)
        self.card_walls, self.lab_metric_walls = self._build_metric_card("Sciany")
        self.card_assemblies, self.lab_metric_assemblies = self._build_metric_card("Komplety")
        self.card_total, self.lab_metric_total = self._build_metric_card("Razem")
        metrics_row.addWidget(self.card_walls, 1)
        metrics_row.addWidget(self.card_assemblies, 1)
        metrics_row.addWidget(self.card_total, 1)
        layout.addLayout(metrics_row)

        self.lab_summary = QLabel("")
        self.lab_summary.setWordWrap(True)
        self.lab_summary.setStyleSheet("color:#444444; background:#fafafa; border:1px solid #e9e9e9; border-radius:6px; padding:8px;")
        layout.addWidget(self.lab_summary)

        self.lab_cost_summary = QLabel("")
        self.lab_cost_summary.setWordWrap(True)
        self.lab_cost_summary.setStyleSheet("color:#1f1f1f; font-weight:600; background:#f7fbff; border:1px solid #dbeafe; border-radius:6px; padding:8px;")
        layout.addWidget(self.lab_cost_summary)

        cash_title = QLabel("Kasa klienta")
        cash_title.setStyleSheet("font-weight:600; color:#333333;")
        layout.addWidget(cash_title)

        self.lab_customer_cash_summary = QLabel("")
        self.lab_customer_cash_summary.setWordWrap(True)
        self.lab_customer_cash_summary.setStyleSheet(
            "color:#1f2937; background:#fffaf3; border:1px solid #eadfcb; border-radius:6px; padding:8px;"
        )
        layout.addWidget(self.lab_customer_cash_summary)

        assemblies_title = QLabel("Komplety w zamowieniu")
        assemblies_title.setStyleSheet("font-weight:600; color:#333333;")
        layout.addWidget(assemblies_title)

        self.tbl_order_assemblies = QTableWidget(0, 6, self.grp_summary)
        self.tbl_order_assemblies.setHorizontalHeaderLabels(
            ["Komplet", "Sciana", "Moduly", "Materialy", "Okleina", "RAZEM"]
        )
        self.tbl_order_assemblies.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_order_assemblies.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_order_assemblies.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_order_assemblies.verticalHeader().setVisible(False)
        self.tbl_order_assemblies.horizontalHeader().setStretchLastSection(True)
        self.tbl_order_assemblies.setAlternatingRowColors(True)
        self.tbl_order_assemblies.setMinimumHeight(150)
        self.tbl_order_assemblies.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_order_assemblies.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_order_assemblies.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.tbl_order_assemblies)

        materials_title = QLabel("Materialy w calym zamowieniu")
        materials_title.setStyleSheet("font-weight:600; color:#333333;")
        layout.addWidget(materials_title)

        self.tbl_order_materials = QTableWidget(0, 4, self.grp_summary)
        self.tbl_order_materials.setHorizontalHeaderLabels(["Material", "Szt", "m2", "Koszt"])
        self.tbl_order_materials.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_order_materials.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_order_materials.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_order_materials.verticalHeader().setVisible(False)
        self.tbl_order_materials.horizontalHeader().setStretchLastSection(True)
        self.tbl_order_materials.setAlternatingRowColors(True)
        self.tbl_order_materials.setMinimumHeight(160)
        self.tbl_order_materials.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_order_materials.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_order_materials.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.tbl_order_materials)

        offer_title = QLabel("Oferta klienta")
        offer_title.setStyleSheet("font-weight:600; color:#333333;")
        layout.addWidget(offer_title)

        self.lab_offer_summary = QLabel("")
        self.lab_offer_summary.setWordWrap(True)
        self.lab_offer_summary.setStyleSheet(
            "color:#334155; background:#fffdf7; border:1px solid #eadfcb; border-radius:6px; padding:8px;"
        )
        layout.addWidget(self.lab_offer_summary)

        self.tbl_offer_refs = QTableWidget(0, 3, self.grp_summary)
        self.tbl_offer_refs.setHorizontalHeaderLabels(["Plik", "Cel", "Opis"])
        self.tbl_offer_refs.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_offer_refs.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_offer_refs.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_offer_refs.verticalHeader().setVisible(False)
        self.tbl_offer_refs.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_offer_refs.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_offer_refs.horizontalHeader().setStretchLastSection(True)
        self.tbl_offer_refs.setAlternatingRowColors(True)
        self.tbl_offer_refs.setMinimumHeight(130)
        layout.addWidget(self.tbl_offer_refs)

        self.lab_offer_ref_info = QLabel("Brak obrazow przypietych do oferty.")
        self.lab_offer_ref_info.setWordWrap(True)
        self.lab_offer_ref_info.setStyleSheet("color:#4b5563;")
        layout.addWidget(self.lab_offer_ref_info)

        self.lab_offer_ref_preview = QLabel("Brak podgladu obrazu oferty.")
        self.lab_offer_ref_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lab_offer_ref_preview.setMinimumHeight(180)
        self.lab_offer_ref_preview.setStyleSheet(
            "border:1px solid #e5dccd; background:#fcfaf6; color:#6b7280; padding:6px;"
        )
        layout.addWidget(self.lab_offer_ref_preview)

        self.tbl_offer_refs.itemSelectionChanged.connect(self._on_offer_reference_selection_changed)

    def _build_metric_card(self, title: str) -> tuple[QFrame, QLabel]:
        card = QFrame(self.grp_summary)
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setStyleSheet(
            "QFrame {"
            " background:#f8fafc;"
            " border:1px solid #e2e8f0;"
            " border-radius:8px;"
            "}"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)

        title_label = QLabel(title, card)
        title_label.setStyleSheet("color:#64748b; font-size:11px; font-weight:600;")
        value_label = QLabel("-", card)
        value_label.setStyleSheet("color:#0f172a; font-size:18px; font-weight:800;")

        layout.addWidget(title_label)
        layout.addWidget(value_label)
        return card, value_label

    def _make_compact_button(self, button: QPushButton, min_width: int = 120, max_width: int = 160) -> None:
        button.setMinimumWidth(min_width)
        button.setMaximumWidth(max_width)
        button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    @staticmethod
    def _apply_collapsible_visual_polish(block: CollapsibleBlock) -> None:
        block.setStyleSheet(
            "QToolButton {"
            "padding: 12px 14px;"
            "font-size: 15px;"
            "font-weight: 800;"
            "text-align: left;"
            "border: 1px solid #d9cfbe;"
            "border-radius: 12px;"
            "background: #fffdf9;"
            "color: #1f2a37;"
            "}"
            "QToolButton:hover {"
            "background: #f8f1e6;"
            "border-color: #cdbca0;"
            "}"
            "QToolButton:checked {"
            "background: #efe4d2;"
            "border-color: #beaa86;"
            "color: #1b2430;"
            "}"
            "QToolButton:checked:hover {"
            "background: #e9dcc8;"
            "border-color: #b4996f;"
            "}"
            "QFrame#contentPanel {"
            "border: 1px solid #e7dccd;"
            "border-top: 0px;"
            "border-bottom-left-radius: 12px;"
            "border-bottom-right-radius: 12px;"
            "background: #fefcf8;"
            "}"
        )
        content_layout = block.content_layout()
        content_layout.setContentsMargins(16, 13, 16, 15)
        content_layout.setSpacing(10)

    def _make_client_field_cell(
        self,
        field_key: str,
        label_text: str,
        editor: QWidget,
        parent: QWidget,
        drop_handler=None,
    ) -> QWidget:
        cell = ClientFieldCell(field_key, label_text, editor, parent)
        cell.sig_field_dropped.connect(drop_handler or self._on_client_field_dropped)
        return cell

    def _restore_splitter_widths(self, splitter: QSplitter, key: str, fallback: list[int]) -> None:
        sizes = load_table_column_widths(key, fallback)
        if len(sizes) != splitter.count():
            sizes = list(fallback)
        splitter.setSizes([max(40, int(value)) for value in sizes])

    def _save_splitter_widths(self, splitter: QSplitter, key: str) -> None:
        save_table_column_widths(key, [int(v) for v in splitter.sizes()])

    @staticmethod
    def _splitter_keys(splitter: QSplitter) -> list[str]:
        out: list[str] = []
        for idx in range(splitter.count()):
            widget = splitter.widget(idx)
            key = str(widget.property("field_key") or "").strip() if widget is not None else ""
            if key:
                out.append(key)
        return out

    @staticmethod
    def _normalize_client_field_order(proposed: list[str], allowed: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for key in proposed:
            norm = str(key or "").strip()
            if norm in allowed and norm not in seen:
                out.append(norm)
                seen.add(norm)
        for key in allowed:
            if key not in seen:
                out.append(key)
        return out

    def _apply_field_order(
        self,
        splitter: QSplitter,
        order: list[str],
        defaults: list[str],
        cells_map: dict[str, QWidget],
    ) -> None:
        normalized = self._normalize_client_field_order(order, defaults)
        for idx, key in enumerate(normalized):
            cell = cells_map.get(key)
            if cell is None:
                continue
            splitter.insertWidget(idx, cell)

    def _apply_client_field_order(self, splitter: QSplitter, order: list[str], defaults: list[str]) -> None:
        self._apply_field_order(splitter, order, defaults, self._client_field_cells)

    def _save_client_field_orders(self) -> None:
        save_ui_string_list("order_client_identity_order", self._splitter_keys(self.client_identity_splitter))
        save_ui_string_list("order_client_address_order", self._splitter_keys(self.client_address_splitter))

    def _save_order_field_orders(self) -> None:
        save_ui_string_list("order_order_primary_order", self._splitter_keys(self.order_primary_splitter))
        save_ui_string_list("order_order_address_order", self._splitter_keys(self.order_address_splitter))

    def _save_worker_field_orders(self) -> None:
        save_ui_string_list("order_worker_primary_order", self._splitter_keys(self.worker_primary_splitter))

    @staticmethod
    def _splitter_index_of(splitter: QSplitter, widget: QWidget) -> int:
        for idx in range(splitter.count()):
            if splitter.widget(idx) is widget:
                return idx
        return -1

    def _find_splitter_for_field_key(
        self,
        field_key: str,
        cells_map: dict[str, QWidget] | None = None,
        splitters: tuple[QSplitter, ...] | None = None,
    ) -> tuple[QSplitter | None, QWidget | None]:
        active_cells = cells_map if cells_map is not None else self._client_field_cells
        active_splitters = (
            splitters
            if splitters is not None
            else (self.client_identity_splitter, self.client_address_splitter)
        )
        cell = active_cells.get(field_key)
        if cell is None:
            return None, None
        for splitter in active_splitters:
            if self._splitter_index_of(splitter, cell) >= 0:
                return splitter, cell
        return None, cell

    def _handle_field_dropped(
        self,
        source_key: str,
        target_key: str,
        cells_map: dict[str, QWidget],
        splitters: tuple[QSplitter, ...],
        splitter_width_keys: tuple[str, ...],
        order_save_handler,
    ) -> None:
        source_splitter, source_cell = self._find_splitter_for_field_key(source_key, cells_map, splitters)
        target_splitter, target_cell = self._find_splitter_for_field_key(target_key, cells_map, splitters)
        if source_splitter is None or source_cell is None or target_splitter is None or target_cell is None:
            return

        source_idx = self._splitter_index_of(source_splitter, source_cell)
        target_idx = self._splitter_index_of(target_splitter, target_cell)
        if source_idx < 0 or target_idx < 0:
            return
        if source_splitter is target_splitter and source_idx == target_idx:
            return

        if source_splitter is target_splitter and source_idx < target_idx:
            target_idx -= 1
        target_splitter.insertWidget(target_idx, source_cell)

        for splitter, key in zip(splitters, splitter_width_keys):
            self._save_splitter_widths(splitter, key)
        order_save_handler()

    def _on_client_field_dropped(self, source_key: str, target_key: str) -> None:
        self._handle_field_dropped(
            source_key,
            target_key,
            self._client_field_cells,
            (self.client_identity_splitter, self.client_address_splitter),
            ("order_client_identity_fields", "order_client_address_fields"),
            self._save_client_field_orders,
        )

    def _on_order_field_dropped(self, source_key: str, target_key: str) -> None:
        self._handle_field_dropped(
            source_key,
            target_key,
            self._order_field_cells,
            (self.order_primary_splitter, self.order_address_splitter),
            ("order_order_primary_fields", "order_order_address_fields"),
            self._save_order_field_orders,
        )

    def _on_worker_field_dropped(self, source_key: str, target_key: str) -> None:
        self._handle_field_dropped(
            source_key,
            target_key,
            self._worker_field_cells,
            (self.worker_primary_splitter,),
            ("order_worker_primary_fields",),
            self._save_worker_field_orders,
        )

    def _set_client_rows_swapped(self, swapped: bool) -> None:
        self._client_rows_swapped = bool(swapped)
        if not hasattr(self, "client_rows_layout"):
            return
        if not hasattr(self, "client_identity_row") or not hasattr(self, "client_address_row"):
            return
        self.client_rows_layout.removeWidget(self.client_identity_row)
        self.client_rows_layout.removeWidget(self.client_address_row)
        if self._client_rows_swapped:
            self.client_rows_layout.addWidget(self.client_address_row)
            self.client_rows_layout.addWidget(self.client_identity_row)
        else:
            self.client_rows_layout.addWidget(self.client_identity_row)
            self.client_rows_layout.addWidget(self.client_address_row)
        if hasattr(self, "btn_client_row_down"):
            self.btn_client_row_down.setEnabled(not self._client_rows_swapped)
        if hasattr(self, "btn_client_row_up"):
            self.btn_client_row_up.setEnabled(self._client_rows_swapped)

    def _make_work_panel(self, title: str, subtitle: str = "") -> tuple[QFrame, QVBoxLayout]:
        panel = QFrame(self)
        panel.setStyleSheet(
            "QFrame {"
            " background:#fffdf8;"
            " border:1px solid #e6d9c8;"
            " border-radius:12px;"
            "}"
        )
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        head = QLabel(title, panel)
        head.setStyleSheet("font-size:15px; font-weight:800; color:#2f241b;")
        layout.addWidget(head)
        if subtitle:
            sub = QLabel(subtitle, panel)
            sub.setWordWrap(True)
            sub.setStyleSheet("color:#6b5b4b;")
            layout.addWidget(sub)
        return panel, layout

    def _build_order_address_from_parts(self) -> str:
        street = str(self.ed_order_site_street.text().strip())
        house = str(self.ed_order_site_house_number.text().strip())
        apartment = str(self.ed_order_site_apartment_number.text().strip())
        postal_code = str(self.ed_order_site_postal_code.text().strip())
        city = str(self.ed_order_site_city.text().strip())

        address_main = street
        if house:
            address_main = f"{address_main} {house}".strip()
        if apartment:
            suffix = f"/{apartment}" if house else f"m.{apartment}"
            address_main = f"{address_main}{suffix}".strip()

        location = " ".join(part for part in (postal_code, city) if part).strip()

        if address_main and location:
            return f"{address_main}, {location}"
        return address_main or location

    @staticmethod
    def _split_site_street_block(value: str) -> tuple[str, str, str]:
        text = str(value or "").strip()
        if not text:
            return "", "", ""
        match = re.match(r"^(.*?)(?:\\s+(\\d+[A-Za-z]?)(?:/(\\d+[A-Za-z]?))?)?$", text)
        if match is None:
            return text, "", ""
        street = str(match.group(1) or "").strip()
        house = str(match.group(2) or "").strip()
        apartment = str(match.group(3) or "").strip()
        return street, house, apartment

    @staticmethod
    def _split_site_city_block(value: str) -> tuple[str, str]:
        text = str(value or "").strip()
        if not text:
            return "", ""
        match = re.match(r"^(\\d{2}-\\d{3})\\s+(.+)$", text)
        if match is None:
            return "", text
        return str(match.group(1) or "").strip(), str(match.group(2) or "").strip()

    def _set_order_address_parts_from_text(self, address_text: str) -> None:
        text = str(address_text or "").strip()
        street = ""
        house = ""
        apartment = ""
        postal_code = ""
        city = ""

        parts = [part.strip() for part in text.split(",") if part.strip()]
        if len(parts) >= 2:
            first_part = parts[0]
            second_part = parts[1]
            if any(ch.isdigit() for ch in first_part) and not any(ch.isdigit() for ch in second_part):
                street, house, apartment = self._split_site_street_block(first_part)
                postal_code, city = self._split_site_city_block(second_part)
            elif any(ch.isdigit() for ch in second_part):
                street, house, apartment = self._split_site_street_block(second_part)
                postal_code, city = self._split_site_city_block(first_part)
            else:
                street = second_part
                city = first_part
        elif parts:
            single = parts[0]
            if any(ch.isdigit() for ch in single):
                street, house, apartment = self._split_site_street_block(single)
            else:
                city = single
        else:
            street, house, apartment = self._split_site_street_block(text)

        self.ed_order_site_street.setText(street)
        self.ed_order_site_house_number.setText(house)
        self.ed_order_site_apartment_number.setText(apartment)
        self.ed_order_site_postal_code.setText(postal_code)
        self.ed_order_site_city.setText(city)

    def _on_order_address_parts_changed(self, _text: str = "") -> None:
        if self._is_syncing_order_address:
            return
        self._is_syncing_order_address = True
        try:
            self.ed_order_address.setText(self._build_order_address_from_parts())
        finally:
            self._is_syncing_order_address = False

    def _on_order_address_text_changed(self, text: str) -> None:
        if self._is_syncing_order_address:
            return
        self._is_syncing_order_address = True
        try:
            self._set_order_address_parts_from_text(text)
        finally:
            self._is_syncing_order_address = False

    def start_new_order(self, force_blank: bool = False) -> None:
        self._set_entry_editor_visible(True)
        if not force_blank and self._load_draft(show_status=False):
            if not self.ed_order_id.text().strip():
                self.ed_order_id.setText(self._generate_next_order_id())
            self.lab_status.clear()
            self.ed_order_code.setFocus()
            return

        if force_blank:
            self._draft_store.clear()

        self._reload_client_choices()
        self._reload_worker_choices()

        self.cb_client_name.setCurrentText("")
        self.ed_client_id.clear()
        self.ed_client_first_name.clear()
        self.ed_client_last_name.clear()
        self.ed_client_phone.clear()
        self.ed_client_email.clear()
        self.ed_client_street.clear()
        self.ed_client_house_number.clear()
        self.ed_client_apartment_number.clear()
        self.ed_client_postal_code.clear()
        self.ed_client_city.clear()
        self.ed_client_notes.clear()

        self.ed_order_id.setText(self._generate_next_order_id())
        self.ed_order_code.clear()
        self.cb_order_status.setCurrentIndex(0)
        self.sp_order_progress.setValue(0)
        self._current_order_calendar_stage = ""
        self._current_order_calendar_date = ""
        self._current_order_calendar_note = ""
        self.ed_order_address.clear()
        self.ed_order_site_street.clear()
        self.ed_order_site_house_number.clear()
        self.ed_order_site_apartment_number.clear()
        self.ed_order_site_postal_code.clear()
        self.ed_order_site_city.clear()
        self.ed_order_notes.clear()
        self._set_date_edit_from_text(self.ed_date_wycena, "")
        self._set_date_edit_from_text(self.ed_date_produkcja, "")
        self._set_date_edit_from_text(self.ed_date_zakup_mat, "")
        self._set_date_edit_from_text(self.ed_date_montaz, "")
        self._set_date_edit_from_text(self.ed_date_poprawki, "")
        self._set_date_edit_from_text(self.ed_date_projekt, "")
        self._set_date_edit_from_text(self.ed_date_probki, "")

        self.ed_worker_id.clear()
        self.cb_worker_name.setCurrentText("")
        self.ed_worker_first_name.clear()
        self.ed_worker_last_name.clear()
        self.ed_worker_name_input.clear()
        self.ed_worker_role.clear()
        self.ed_worker_phone.clear()
        self.ed_worker_email.clear()
        self.ed_worker_notes.clear()

        self.ed_architect_file.clear()
        self.cb_architect_kind.setCurrentIndex(0)
        self.ed_architect_description.clear()
        self.cb_architect_fragment_target_kind.setCurrentIndex(0)
        self.ed_architect_fragment_target_name.clear()
        self.ed_architect_fragment_description.clear()
        self._set_architect_attachments([])
        self.ed_quote_item_name.clear()
        self.cb_quote_item_kind.setCurrentIndex(0)
        self.sp_quote_item_quantity.setValue(1)
        self.ed_quote_item_description.clear()
        self._set_quote_items([])
        self.cb_material_scope.setCurrentIndex(0)
        self.cb_material_choice_status.setCurrentIndex(0)
        self.ed_material_choice_material.clear()
        self.ed_material_choice_color.clear()
        self.ed_material_choice_code.clear()
        self.ed_material_choice_notes.clear()
        self._set_material_choices([])
        self._set_customer_payments([])
        self._clear_customer_payment_form()

        self.lab_status.clear()
        self._refresh_summary()
        self.ed_order_code.setFocus()
        self._refresh_order_walls_table()

        if force_blank:
            self._set_status("Wyczyszczono karte i zapis roboczy.", ok=True)

    def start_new_order_from_context(self, context: dict | None = None) -> None:
        self._set_entry_editor_visible(True)
        payload = context if isinstance(context, dict) else {}

        client_name = str(payload.get("client_name", "") or "").strip()
        order_id = str(payload.get("order_id", "") or "").strip()
        order_name = str(payload.get("order_name", "") or "").strip()
        worker_name = str(payload.get("worker_name", "") or "").strip()
        order_status = str(payload.get("order_status", "") or "").strip()
        order_progress_percent = int(float(payload.get("order_progress_percent", 0.0) or 0.0))
        order_calendar_stage = str(payload.get("order_calendar_stage", "") or "").strip()
        order_calendar_date = str(payload.get("order_calendar_date", "") or "").strip()
        site_address = str(payload.get("site_address", "") or "").strip()
        site_street = str(payload.get("site_street", "") or "").strip()
        site_house_number = str(payload.get("site_house_number", "") or "").strip()
        site_apartment_number = str(payload.get("site_apartment_number", "") or "").strip()
        site_postal_code = str(payload.get("site_postal_code", "") or "").strip()
        site_city = str(payload.get("site_city", "") or "").strip()

        self._reload_client_choices()
        self._reload_worker_choices()

        client = self._client_store.get(client_name) if client_name else None
        worker = self._worker_store.get(worker_name) if worker_name else None
        order_code = str(payload.get("order_code", "") or "").strip()
        order = self._order_store.get(order_code) if order_code else None

        self._is_restoring_draft = True
        try:
            self.cb_client_name.setCurrentText(client_name)
            parsed_client_id, parsed_full_name = self._split_client_key(client_name)
            parsed_first_name, parsed_last_name = self._split_full_name(parsed_full_name)
            self.ed_client_id.setText(str(getattr(client, "client_id", "") or parsed_client_id))
            self.ed_client_first_name.setText(str(getattr(client, "first_name", "") or parsed_first_name))
            self.ed_client_last_name.setText(str(getattr(client, "last_name", "") or parsed_last_name))
            self.ed_client_phone.setText(str(getattr(client, "phone", "") or ""))
            self.ed_client_email.setText(str(getattr(client, "email", "") or ""))
            self.ed_client_street.setText(str(getattr(client, "street", "") or ""))
            self.ed_client_house_number.setText(str(getattr(client, "house_number", "") or ""))
            self.ed_client_apartment_number.setText(str(getattr(client, "apartment_number", "") or ""))
            self.ed_client_postal_code.setText(str(getattr(client, "postal_code", "") or ""))
            self.ed_client_city.setText(str(getattr(client, "city", "") or ""))
            self.ed_client_notes.setPlainText(str(getattr(client, "notes", "") or ""))

            self.ed_order_id.setText(str(getattr(order, "order_id", "") or order_id or self._generate_next_order_id()))
            self.ed_order_code.setText(str(getattr(order, "code", "") or order_code or ""))
            self.ed_order_name.setText(str(getattr(order, "order_name", "") or order_name or ""))
            effective_status = str(getattr(order, "status", "") or order_status or ORDER_STATUS_ITEMS[0])
            idx = self.cb_order_status.findText(effective_status)
            self.cb_order_status.setCurrentIndex(idx if idx >= 0 else 0)
            effective_progress = int(round(float(getattr(order, "progress_percent", 0.0) or order_progress_percent or 0.0)))
            self.sp_order_progress.setValue(max(0, min(100, effective_progress)))
            self._current_order_calendar_stage = str(getattr(order, "calendar_stage", "") or order_calendar_stage)
            date_montaz = str(getattr(order, "date_montaz", "") or "").strip()
            self._current_order_calendar_date = date_montaz if date_montaz else str(getattr(order, "calendar_date", "") or order_calendar_date)
            self._current_order_calendar_note = str(getattr(order, "calendar_note", "") or "")
            effective_site_address = str(getattr(order, "site_address", "") or site_address)
            self.ed_order_address.setText(effective_site_address)
            self.ed_order_site_street.setText(str(getattr(order, "site_street", "") or site_street))
            self.ed_order_site_house_number.setText(str(getattr(order, "site_house_number", "") or site_house_number))
            self.ed_order_site_apartment_number.setText(
                str(getattr(order, "site_apartment_number", "") or site_apartment_number)
            )
            self.ed_order_site_postal_code.setText(str(getattr(order, "site_postal_code", "") or site_postal_code))
            self.ed_order_site_city.setText(str(getattr(order, "site_city", "") or site_city))
            if not any(
                (
                    self.ed_order_site_street.text().strip(),
                    self.ed_order_site_house_number.text().strip(),
                    self.ed_order_site_apartment_number.text().strip(),
                    self.ed_order_site_postal_code.text().strip(),
                    self.ed_order_site_city.text().strip(),
                )
            ):
                self._set_order_address_parts_from_text(effective_site_address)
            self.ed_order_notes.setPlainText(str(getattr(order, "notes", "") or ""))
            self._set_date_edit_from_text(self.ed_date_wycena, str(getattr(order, "date_wycena", "") or ""))
            self._set_date_edit_from_text(self.ed_date_produkcja, str(getattr(order, "date_produkcja", "") or ""))
            self._set_date_edit_from_text(self.ed_date_zakup_mat, str(getattr(order, "date_zakup_mat", "") or ""))
            self._set_date_edit_from_text(self.ed_date_montaz, str(getattr(order, "date_montaz", "") or ""))
            self._set_date_edit_from_text(self.ed_date_poprawki, str(getattr(order, "date_poprawki", "") or ""))
            self._set_date_edit_from_text(self.ed_date_projekt, str(getattr(order, "date_projekt", "") or ""))
            self._set_date_edit_from_text(self.ed_date_probki, str(getattr(order, "date_probki", "") or ""))

            worker_first_name, worker_last_name = self._split_full_name(worker_name)
            self.ed_worker_id.setText(str(getattr(worker, "worker_id", "") or ""))
            self.cb_worker_name.setCurrentText(worker_name)
            self.ed_worker_first_name.setText(worker_first_name)
            self.ed_worker_last_name.setText(worker_last_name)
            self.ed_worker_name_input.setText(worker_name)
            self.ed_worker_role.setText(str(getattr(worker, "role", "") or ""))
            self.ed_worker_phone.setText(str(getattr(worker, "phone", "") or ""))
            self.ed_worker_email.setText(str(getattr(worker, "email", "") or ""))
            self.ed_worker_notes.setPlainText(str(getattr(worker, "notes", "") or ""))
            self._set_architect_attachments(list(getattr(order, "attachments", []) or []))
            self._set_quote_items(list(getattr(order, "quote_items", []) or []))
            self._set_material_choices(list(getattr(order, "material_choices", []) or []))
            self._set_customer_payments(list(getattr(order, "customer_payments", []) or []))
        finally:
            self._is_restoring_draft = False

        self._refresh_summary()
        self._save_draft(show_status=False)
        self.ed_order_code.setFocus()
        self._set_status("Przywrocono dane zamowienia z kompletu.", ok=True)

    def _refresh_summary(self) -> None:
        client_id = self.ed_client_id.text().strip()
        client_full_name = " ".join(
            part for part in (self.ed_client_first_name.text().strip(), self.ed_client_last_name.text().strip()) if part
        ).strip()
        client_name = self._build_client_key(
            client_id=client_id,
            first_name=self.ed_client_first_name.text().strip(),
            last_name=self.ed_client_last_name.text().strip(),
            fallback_name=self.cb_client_name.currentText().strip(),
        ) or "-"
        if client_full_name:
            client_name = f"{client_id} | {client_full_name}" if client_id else client_full_name
        order_code = self.ed_order_code.text().strip() or "-"
        worker_name = self._worker_name_from_fields() or "-"
        status_name = self.cb_order_status.currentText().strip() or "-"
        progress_percent = int(self.sp_order_progress.value())
        calendar_stage = str(self._current_order_calendar_stage or "").strip()
        calendar_date = str(self._current_order_calendar_date or "").strip()
        wall_count = len(self._current_order_wall_names())
        assembly_count = len(self._current_order_assemblies())
        attachment_count = len(self._architect_attachments)
        quote_item_count = len(self._quote_items)
        material_choice_count = len(self._material_choices)
        customer_payment_count = len(self._customer_payments)
        final_material_choices = [
            entry
            for entry in self._material_choices
            if str(entry.get("status", "") or "").strip().lower() == "wybrane finalnie"
        ]
        final_material_parts = []
        for entry in final_material_choices[:4]:
            scope = str(entry.get("scope", "") or "Inne").strip()
            material = str(entry.get("material", "") or "-").strip() or "-"
            color = str(entry.get("color", "") or "").strip()
            code = str(entry.get("code", "") or "").strip()
            details = " / ".join(part for part in (material, color, code) if part)
            final_material_parts.append(f"{scope}: {details}")
        if hasattr(self, "lab_metric_walls"):
            self.lab_metric_walls.setText(str(wall_count))
        if hasattr(self, "lab_metric_assemblies"):
            self.lab_metric_assemblies.setText(str(assembly_count))
        payments_total = sum(float(item.get("amount", 0.0) or 0.0) for item in self._customer_payments)
        payments_paid_total = sum(
            float(item.get("amount", 0.0) or 0.0)
            for item in self._customer_payments
            if bool(item.get("paid", False))
        )
        payments_remaining_total = max(0.0, payments_total - payments_paid_total)
        self.lab_summary.setText(
            f"Klient: {client_name}\n"
            f"Zamowienie: {order_code}\n"
            f"Status: {status_name}\n"
            f"Zaawansowanie: {progress_percent}%\n"
            f"Pracownik: {worker_name}\n"
            f"Zalaczniki od architekta: {attachment_count}\n"
            f"Pozycje do wyceny: {quote_item_count}\n"
            f"Probki / materialy: {material_choice_count}\n"
            f"Finalne wybory: {len(final_material_choices)}\n"
            f"Wplaty klienta: {customer_payment_count} | Oplacone: {payments_paid_total:.2f} zl | Pozostalo: {payments_remaining_total:.2f} zl"
        )
        if final_material_parts:
            self.lab_summary.setText(self.lab_summary.text() + "\nWybrane: " + "; ".join(final_material_parts))
        if calendar_stage or calendar_date:
            self.lab_summary.setText(
                self.lab_summary.text()
                + f"\nKalendarz: {calendar_stage or '-'}"
                + (f" | {calendar_date}" if calendar_date else "")
            )
        quote_names = [
            str(entry.get("name", "") or "").strip()
            for entry in self._quote_items
            if str(entry.get("name", "") or "").strip()
        ]
        offer_lines = [
            f"Pozycje do oferty: {', '.join(quote_names[:4]) if quote_names else '-'}",
            f"Finalne materialy: {len(final_material_choices)}",
            f"Referencje obrazu do oferty: {len(self._collect_offer_reference_attachments())}",
        ]
        if final_material_parts:
            offer_lines.append("Wybrane materialy: " + "; ".join(final_material_parts[:3]))
        self.lab_offer_summary.setText("\n".join(offer_lines))

        cash_summary_text = (
            f"Harmonogram wplat: {customer_payment_count}\n"
            f"Planowana kwota: {payments_total:.2f} zl\n"
            f"Oplacone: {payments_paid_total:.2f} zl\n"
            f"Pozostalo: {payments_remaining_total:.2f} zl"
        )
        if hasattr(self, "lab_customer_cash_summary"):
            self.lab_customer_cash_summary.setText(cash_summary_text)
        if hasattr(self, "lab_customer_cash_detail"):
            self.lab_customer_cash_detail.setText(cash_summary_text)

        self._refresh_order_walls_table()
        self._refresh_order_cost_summary()
        self._refresh_offer_references()
        self._refresh_quote_item_references()
        self._autosave_draft()

    def _on_open_calendar_for_montaz(self) -> None:
        date_val = self.ed_date_montaz.date()
        if date_val.isValid():
            from src.app.main_window import MainWindow
            for w in QApplication.topLevelWidgets():
                if isinstance(w, MainWindow):
                    target_date = date_val.toString("yyyy-MM-dd")
                    w._open_calendar(target_date)
                    break

    def _collect_offer_reference_attachments(self) -> list[dict[str, str]]:
        results: list[dict[str, str]] = []
        seen_paths: set[str] = set()
        for attachment in list(self._architect_attachments):
            path = str(attachment.get("path", "") or "").strip()
            if not path or path in seen_paths:
                continue
            kind = str(attachment.get("kind", "") or "").strip().lower()
            suffix = Path(path).suffix.lower()
            if kind not in {"obraz", "referencja"} and suffix not in {".png", ".jpg", ".jpeg", ".bmp", ".webp"}:
                continue
            target_kind = str(attachment.get("target_kind", "") or "").strip()
            if target_kind.lower() != "oferta":
                continue
            seen_paths.add(path)
            results.append(
                {
                    "path": path,
                    "target": str(attachment.get("target_name", "") or "").strip() or "Oferta",
                    "description": str(attachment.get("description", "") or "").strip(),
                }
            )
        return results

    def _refresh_offer_references(self) -> None:
        if not hasattr(self, "tbl_offer_refs"):
            return
        selected_path = self._selected_offer_reference_path()
        self._offer_reference_items = self._collect_offer_reference_attachments()
        self.tbl_offer_refs.setRowCount(len(self._offer_reference_items))
        for row, entry in enumerate(self._offer_reference_items):
            path_item = QTableWidgetItem(Path(str(entry.get("path", "") or "")).name)
            path_item.setData(Qt.ItemDataRole.UserRole, str(entry.get("path", "") or ""))
            target_item = QTableWidgetItem(str(entry.get("target", "") or "Oferta"))
            description_item = QTableWidgetItem(str(entry.get("description", "") or "-"))
            self.tbl_offer_refs.setItem(row, 0, path_item)
            self.tbl_offer_refs.setItem(row, 1, target_item)
            self.tbl_offer_refs.setItem(row, 2, description_item)
        self.tbl_offer_refs.resizeColumnsToContents()

        if self._offer_reference_items:
            target_row = 0
            if selected_path:
                for row in range(self.tbl_offer_refs.rowCount()):
                    item = self.tbl_offer_refs.item(row, 0)
                    if item is not None and str(item.data(Qt.ItemDataRole.UserRole) or "") == selected_path:
                        target_row = row
                        break
            self.tbl_offer_refs.selectRow(target_row)
        else:
            self.tbl_offer_refs.clearSelection()
            self._offer_reference_pixmap = QPixmap()
            self.lab_offer_ref_info.setText("Brak obrazow przypietych do oferty.")
            self.lab_offer_ref_preview.setPixmap(QPixmap())
            self.lab_offer_ref_preview.setText("Brak podgladu obrazu oferty.")

    def _selected_offer_reference_path(self) -> str:
        selection = (
            self.tbl_offer_refs.selectionModel().selectedRows()
            if self.tbl_offer_refs.selectionModel() is not None
            else []
        )
        if not selection:
            return ""
        item = self.tbl_offer_refs.item(int(selection[0].row()), 0)
        if item is None:
            return ""
        return str(item.data(Qt.ItemDataRole.UserRole) or "").strip()

    def _update_offer_reference_preview(self) -> None:
        if self._offer_reference_pixmap.isNull():
            self.lab_offer_ref_preview.setPixmap(QPixmap())
            return
        target_size = self.lab_offer_ref_preview.size()
        scaled = self._offer_reference_pixmap.scaled(
            max(40, target_size.width() - 12),
            max(40, target_size.height() - 12),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.lab_offer_ref_preview.setPixmap(scaled)

    def _on_offer_reference_selection_changed(self) -> None:
        selection = (
            self.tbl_offer_refs.selectionModel().selectedRows()
            if self.tbl_offer_refs.selectionModel() is not None
            else []
        )
        if not selection:
            self._offer_reference_pixmap = QPixmap()
            self.lab_offer_ref_info.setText("Brak obrazow przypietych do oferty.")
            self.lab_offer_ref_preview.setPixmap(QPixmap())
            self.lab_offer_ref_preview.setText("Brak podgladu obrazu oferty.")
            return
        row = int(selection[0].row())
        if row < 0 or row >= len(self._offer_reference_items):
            return
        entry = self._offer_reference_items[row]
        path = str(entry.get("path", "") or "").strip()
        info_parts = [
            Path(path).name,
            str(entry.get("target", "") or "").strip(),
            str(entry.get("description", "") or "").strip(),
        ]
        self.lab_offer_ref_info.setText(" | ".join(part for part in info_parts if part))
        pixmap = QPixmap(path)
        if pixmap.isNull():
            self._offer_reference_pixmap = QPixmap()
            self.lab_offer_ref_preview.setPixmap(QPixmap())
            self.lab_offer_ref_preview.setText("Nie udalo sie odczytac obrazu oferty.")
            return
        self._offer_reference_pixmap = pixmap
        self.lab_offer_ref_preview.setText("")
        self._update_offer_reference_preview()

    def _current_order_wall_names(self) -> list[str]:
        order_code = str(self.ed_order_code.text().strip())
        client_name = str(self.cb_client_name.currentText().strip())
        if not order_code:
            return []

        names: list[str] = []
        for wall in self._wall_store.list_layouts():
            wall_order = str(getattr(wall, "order_name", "") or "").strip()
            wall_client = str(getattr(wall, "client_name", "") or "").strip()
            if wall_order != order_code:
                continue
            if client_name and wall_client and wall_client != client_name:
                continue
            names.append(str(getattr(wall, "name", "") or "").strip())
        return names

    def _current_order_assemblies(self):
        order_code = str(self.ed_order_code.text().strip())
        client_name = str(self.cb_client_name.currentText().strip())
        if not order_code:
            return []

        assemblies = []
        for assembly in self._assembly_store.list_assemblies():
            assembly_order = str(getattr(assembly, "order_name", "") or "").strip()
            assembly_client = str(getattr(assembly, "client_name", "") or "").strip()
            if assembly_order != order_code:
                continue
            if client_name and assembly_client and assembly_client != client_name:
                continue
            assemblies.append(assembly)
        return assemblies

    def _collect_offer_export_data(self) -> dict[str, object]:
        assemblies = self._current_order_assemblies()
        wall_count = len(self._current_order_wall_names())
        auto_double_width = float(load_drawing_settings().auto_double_front_width_mm or 600.0)

        material_total = 0.0
        edgeband_total = 0.0
        hardware_total = 0.0
        commercial_total = 0.0
        margin_total = 0.0
        modules_total = 0
        assembly_rows: list[dict[str, float | int | str]] = []
        material_acc: dict[str, dict[str, float | str]] = defaultdict(
            lambda: {"label": "", "count": 0.0, "area": 0.0, "cost": 0.0}
        )

        for assembly in assemblies:
            wall_name = str(getattr(assembly, "wall_name", "") or "").strip()
            linked_wall = self._wall_store.get(wall_name) if wall_name else None
            resolved_items = resolve_assembly_items(
                assembly,
                self._catalog,
                auto_double_front_width_mm=auto_double_width,
                linked_wall=linked_wall,
            )
            assembly_modules = len(resolved_items)
            modules_total += assembly_modules
            assembly_material_total = 0.0
            assembly_edgeband_total = 0.0
            assembly_hardware_total = 0.0

            for resolved in resolved_items:
                breakdown = resolved.cost_breakdown
                resolved_material_total = float(breakdown.material_total_pln)
                resolved_edgeband_total = float(breakdown.edgeband_total_pln)
                resolved_hardware_total = float(breakdown.hardware_total_pln)

                material_total += resolved_material_total
                edgeband_total += resolved_edgeband_total
                hardware_total += resolved_hardware_total

                assembly_material_total += resolved_material_total
                assembly_edgeband_total += resolved_edgeband_total
                assembly_hardware_total += resolved_hardware_total

                for line in breakdown.material_lines:
                    entry = material_acc[str(line.key or "-")]
                    entry["label"] = str(line.label or line.key or "-")
                    entry["count"] = float(entry["count"]) + float(line.count)
                    entry["area"] = float(entry["area"]) + float(line.area_m2)
                    entry["cost"] = float(entry["cost"]) + float(line.cost_pln)

            assembly_grand_total = assembly_material_total + assembly_edgeband_total + assembly_hardware_total
            assembly_commercial = float(assembly.commercial_sale_total(assembly_grand_total))

            assembly_rows.append(
                {
                    "name": str(getattr(assembly, "name", "") or "-"),
                    "wall_name": str(getattr(assembly, "wall_name", "") or "-"),
                    "modules": int(assembly_modules),
                    "material_total": float(assembly_material_total),
                    "edgeband_total": float(assembly_edgeband_total),
                    "hardware_total": float(assembly_hardware_total),
                    "grand_total": float(assembly_grand_total),
                    "commercial_total": float(assembly_commercial),
                }
            )

            commercial_total += assembly_commercial
            margin_total += float(
                assembly_commercial
                - (
                        assembly_grand_total
                        + float(getattr(assembly, "labor_cost_pln", 0.0) or 0.0)
                        + float(getattr(assembly, "transport_cost_pln", 0.0) or 0.0)
                        + float(getattr(assembly, "montage_cost_pln", 0.0) or 0.0)
                )
            )

        return {
            "wall_count": wall_count,
            "assemblies": sorted(
                assembly_rows,
                key=lambda item: (-float(item["grand_total"]), str(item["name"]).lower()),
            ),
            "materials": sorted(
                material_acc.values(),
                key=lambda item: (-float(item["cost"]), str(item["label"]).lower()),
            ),
            "modules_total": modules_total,
            "material_total": material_total,
            "edgeband_total": edgeband_total,
            "hardware_total": hardware_total,
            "grand_total": material_total + edgeband_total + hardware_total,
            "commercial_total": commercial_total,
            "margin_total": margin_total,
            "customer_payments": [dict(item) for item in self._customer_payments],
        }

    def _build_offer_html(self) -> str:
        order_code = str(self.ed_order_code.text().strip() or "-")
        client_name = str(self.cb_client_name.currentText().strip() or "-")
        worker_name = str(self._worker_name_from_fields() or "-")
        status_name = str(self.cb_order_status.currentText().strip() or "-")
        progress_percent = int(self.sp_order_progress.value())
        calendar_stage = str(self._current_order_calendar_stage or "").strip() or "-"
        calendar_date = str(self._current_order_calendar_date or "").strip() or "-"
        site_address = str(self._build_order_address_from_parts() or self.ed_order_address.text().strip() or "-")
        order_notes = str(self.ed_order_notes.toPlainText().strip())
        quote_items = [dict(item) for item in self._quote_items]
        final_material_choices = [
            dict(item)
            for item in self._material_choices
            if str(item.get("status", "") or "").strip().lower() == "wybrane finalnie"
        ]
        offer_refs = self._collect_offer_reference_attachments()
        export_data = self._collect_offer_export_data()

        def _row(cells: list[str]) -> str:
            return "<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>"

        def _build_ref_card(title: str, description: str, path_str: str) -> str:
            data_uri = self._image_file_to_data_uri(path_str)
            image_html = (
                f'<img src="{data_uri}" alt="{escape(description)}" />'
                if data_uri
                else '<div class="image-missing">Brak podgladu obrazu</div>'
            )
            return (
                "<div class=\"ref-card\">"
                f"{image_html}"
                f"<div class=\"ref-meta\"><strong>{escape(title)}</strong><br>{escape(description)}</div>"
                "</div>"
            )

        quote_rows = "".join(
            _row(
                [
                    escape(str(entry.get("name", "") or "-")),
                    escape(str(entry.get("kind", "") or "-")),
                    escape(str(entry.get("description", "") or "-")),
                    str(max(1, int(float(entry.get("quantity", 1) or 1)))),
                ]
            )
            for entry in quote_items
        ) or '<tr><td colspan="4">Brak pozycji do oferty.</td></tr>'

        material_rows = "".join(
            _row(
                [
                    escape(str(entry.get("scope", "") or "-")),
                    escape(str(entry.get("material", "") or "-")),
                    escape(str(entry.get("color", "") or "-")),
                    escape(str(entry.get("code", "") or "-")),
                    escape(str(entry.get("notes", "") or "-")),
                ]
            )
            for entry in final_material_choices
        ) or '<tr><td colspan="5">Brak finalnych wyborow materialowych.</td></tr>'

        assembly_rows = "".join(
            _row(
                [
                    escape(str(entry["name"] or "-")),
                    escape(str(entry["wall_name"] or "-")),
                    str(int(entry["modules"])),
                    f'{float(entry["material_total"]):.2f} zl',
                    f'{float(entry["edgeband_total"]):.2f} zl',
                    f'{float(entry["hardware_total"]):.2f} zl',
                    f'{float(entry["grand_total"]):.2f} zl',
                ]
            )
            for entry in list(export_data["assemblies"])
        ) or '<tr><td colspan="7">Brak zapisanych kompletow dla tego zamowienia.</td></tr>'

        aggregate_material_rows = "".join(
            _row(
                [
                    escape(str(entry["label"] or "-")),
                    str(int(round(float(entry["count"])))),
                    f'{float(entry["area"]):.3f}',
                    f'{float(entry["cost"]):.2f} zl',
                ]
            )
            for entry in list(export_data["materials"])
        ) or '<tr><td colspan="4">Brak materialow w zapisanych kompletach.</td></tr>'

        customer_payments = list(export_data.get("customer_payments", []))
        customer_payment_rows = "".join(
            _row(
                [
                    escape(str(entry.get("stage", "") or "-")),
                    f'{float(entry.get("amount", 0.0) or 0.0):.2f} zl',
                    "Tak" if bool(entry.get("paid", False)) else "Nie",
                    escape(str(entry.get("note", "") or "-")),
                ]
            )
            for entry in customer_payments
        ) or '<tr><td colspan="4">Brak wpisanego harmonogramu wplat klienta.</td></tr>'
        customer_payment_total = sum(float(entry.get("amount", 0.0) or 0.0) for entry in customer_payments)
        customer_payment_paid = sum(
            float(entry.get("amount", 0.0) or 0.0) for entry in customer_payments if bool(entry.get("paid", False))
        )
        customer_payment_remaining = max(0.0, customer_payment_total - customer_payment_paid)

        ref_cards: list[str] = []
        for entry in offer_refs:
            ref_cards.append(
                _build_ref_card(
                    str(entry.get("target", "") or "Oferta"),
                    str(entry.get("description", "") or "") or "Referencja wizualna",
                    str(entry.get("path", "") or ""),
                )
            )
        refs_html = "".join(ref_cards) or "<p>Brak obrazow przypietych do oferty.</p>"

        quote_item_ref_sections: list[str] = []
        for entry in quote_items:
            quote_name = str(entry.get("name", "") or "").strip()
            if not quote_name:
                continue
            refs_for_item = self._collect_quote_item_reference_attachments(quote_name)
            if not refs_for_item:
                continue
            cards_html = "".join(
                _build_ref_card(
                    str(ref.get("target", "") or quote_name),
                    str(ref.get("description", "") or "") or "Referencja pozycji",
                    str(ref.get("path", "") or ""),
                )
                for ref in refs_for_item
            )
            quote_item_ref_sections.append(
                "<div class=\"quote-ref-group\">"
                f"<h3>{escape(quote_name)}</h3>"
                f"<p class=\"quote-ref-subtitle\">{escape(str(entry.get('kind', '') or '-'))} | {escape(str(entry.get('description', '') or '-'))}</p>"
                f"<div class=\"refs\">{cards_html}</div>"
                "</div>"
            )
        quote_item_refs_html = (
            "".join(quote_item_ref_sections) if quote_item_ref_sections else "<p>Brak referencji przypietych do pozycji do wyceny.</p>"
        )

        notes_html = f"<p><strong>Notatki:</strong> {escape(order_notes)}</p>" if order_notes else ""

        return f"""<!DOCTYPE html>
<html lang="pl">
<head>
  <meta charset="utf-8">
  <title>Oferta {escape(order_code)}</title>
  <style>
    body {{ font-family: Segoe UI, Arial, sans-serif; margin: 24px; color: #1f2937; }}
    h1, h2 {{ margin-bottom: 8px; }}
    h1 {{ font-size: 26px; }}
    h2 {{ margin-top: 26px; font-size: 18px; border-bottom: 1px solid #e5e7eb; padding-bottom: 4px; }}
    .meta {{ display: grid; grid-template-columns: repeat(2, minmax(220px, 1fr)); gap: 8px 20px; margin-bottom: 16px; }}
    .summary {{ background: #f8fafc; border: 1px solid #dbeafe; border-radius: 8px; padding: 12px 14px; margin: 12px 0 20px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
    th, td {{ border: 1px solid #e5e7eb; padding: 8px 10px; text-align: left; vertical-align: top; }}
    th {{ background: #f8fafc; }}
    .refs {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; margin-top: 12px; }}
    .ref-card {{ border: 1px solid #e5dccd; border-radius: 8px; padding: 10px; background: #fcfaf6; }}
    .ref-card img {{ width: 100%; max-height: 260px; object-fit: contain; display: block; background: white; border: 1px solid #e5e7eb; }}
    .ref-meta {{ margin-top: 8px; color: #475569; }}
    .quote-ref-group {{ margin-top: 14px; padding-top: 8px; border-top: 1px dashed #d6d3d1; }}
    .quote-ref-group h3 {{ margin: 0 0 4px; font-size: 16px; }}
    .quote-ref-subtitle {{ margin: 0 0 8px; color: #64748b; }}
    .image-missing {{ min-height: 140px; display:flex; align-items:center; justify-content:center; color:#6b7280; border:1px dashed #cbd5e1; background:white; }}
  </style>
</head>
<body>
  <h1>Oferta klienta</h1>
    <div class="meta">
      <div><strong>Klient:</strong> {escape(client_name)}</div>
      <div><strong>Zamowienie:</strong> {escape(order_code)}</div>
      <div><strong>Pracownik:</strong> {escape(worker_name)}</div>
      <div><strong>Status:</strong> {escape(status_name)}</div>
      <div><strong>Zaawansowanie:</strong> {progress_percent}%</div>
      <div><strong>Etap kalendarza:</strong> {escape(calendar_stage)}</div>
      <div><strong>Adres realizacji:</strong> {escape(site_address)}</div>
      <div><strong>Termin etapu:</strong> {escape(calendar_date)}</div>
      <div><strong>Data eksportu:</strong> {escape(datetime.now().strftime("%Y-%m-%d %H:%M"))}</div>
    </div>
  <div class="summary">
    <strong>Podsumowanie orientacyjne</strong><br>
    Sciany: {int(export_data["wall_count"])}<br>
    Komplety: {len(list(export_data["assemblies"]))}<br>
    Moduly: {int(export_data["modules_total"])}<br>
    Materialy: {float(export_data["material_total"]):.2f} zl<br>
    Okleina: {float(export_data["edgeband_total"]):.2f} zl<br>
    Okucia: {float(export_data["hardware_total"]):.2f} zl<br>
    <strong>Koszt techniczny orientacyjnie: {float(export_data["grand_total"]):.2f} zl</strong><br>
    <strong>Cena handlowa orientacyjna: {float(export_data["commercial_total"]):.2f} zl</strong><br>
    <strong>Marza kwotowo: {float(export_data["margin_total"]):.2f} zl</strong><br>
    Harmonogram wplat: {len(customer_payments)}<br>
    Oplacone: {customer_payment_paid:.2f} zl<br>
    Pozostalo: {customer_payment_remaining:.2f} zl
  </div>
  {notes_html}
  <h2>Pozycje do oferty</h2>
  <table>
    <thead><tr><th>Pozycja</th><th>Typ</th><th>Opis</th><th>Ilosc</th></tr></thead>
    <tbody>{quote_rows}</tbody>
  </table>
  <h2>Finalne materialy</h2>
  <table>
    <thead><tr><th>Zakres</th><th>Material</th><th>Kolor / dekor</th><th>Kod</th><th>Uwagi</th></tr></thead>
    <tbody>{material_rows}</tbody>
  </table>
  <h2>Komplety i koszt orientacyjny</h2>
  <table>
    <thead><tr><th>Komplet</th><th>Sciana</th><th>Moduly</th><th>Materialy</th><th>Okleina</th><th>Okucia</th><th>Razem</th></tr></thead>
    <tbody>{assembly_rows}</tbody>
  </table>
  <h2>Materialy w zamowieniu</h2>
  <table>
    <thead><tr><th>Material</th><th>Szt</th><th>m2</th><th>Koszt</th></tr></thead>
    <tbody>{aggregate_material_rows}</tbody>
  </table>
  <h2>Harmonogram wplat klienta</h2>
  <div class="summary">
    Planowana kwota: {customer_payment_total:.2f} zl<br>
    Oplacone: {customer_payment_paid:.2f} zl<br>
    Pozostalo: {customer_payment_remaining:.2f} zl
  </div>
  <table>
    <thead><tr><th>Etap</th><th>Kwota</th><th>Oplacone</th><th>Uwagi</th></tr></thead>
    <tbody>{customer_payment_rows}</tbody>
  </table>
  <h2>Referencje wizualne</h2>
  <div class="refs">{refs_html}</div>
  <h2>Referencje pozycji do wyceny</h2>
  {quote_item_refs_html}
</body>
</html>
"""

    def _build_offer_document(self) -> QTextDocument:
        document = QTextDocument(self)
        document.setDocumentMargin(22.0)
        document.setHtml(self._build_offer_html())
        return document

    def _on_export_offer(self) -> None:
        order_code = str(self.ed_order_code.text().strip() or "oferta")
        safe_code = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in order_code) or "oferta"
        default_path = self._offer_output_dir() / f"{safe_code}_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Eksport oferty klienta",
            str(default_path),
            "Pliki HTML (*.html);;Wszystkie pliki (*.*)",
        )
        if not file_path:
            return
        output_path = Path(file_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self._build_offer_html(), encoding="utf-8")
        self._set_status(f'Wyeksportowano oferte do "{output_path.name}".', ok=True)

    def _on_export_offer_pdf(self) -> None:
        order_code = str(self.ed_order_code.text().strip() or "oferta")
        safe_code = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in order_code) or "oferta"
        default_path = self._offer_output_dir() / f"{safe_code}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Eksport PDF oferty klienta",
            str(default_path),
            "Pliki PDF (*.pdf);;Wszystkie pliki (*.*)",
        )
        if not file_path:
            return
        output_path = Path(file_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(str(output_path))

        document = self._build_offer_document()
        document.print(printer)
        self._set_status(f'Wyeksportowano PDF oferty do "{output_path.name}".', ok=True)

    def _refresh_order_cost_summary(self) -> None:
        if (
                not hasattr(self, "lab_cost_summary")
                or not hasattr(self, "tbl_order_materials")
                or not hasattr(self, "tbl_order_assemblies")
        ):
            return

        assemblies = self._current_order_assemblies()
        wall_count = len(self._current_order_wall_names())
        auto_double_width = float(load_drawing_settings().auto_double_front_width_mm or 600.0)

        material_total = 0.0
        edgeband_total = 0.0
        hardware_total = 0.0
        commercial_total = 0.0
        margin_total = 0.0
        modules_total = 0
        assembly_rows: list[dict[str, float | int | str]] = []
        material_acc: dict[str, dict[str, float | str]] = defaultdict(
            lambda: {"label": "", "count": 0.0, "area": 0.0, "cost": 0.0}
        )

        for assembly in assemblies:
            wall_name = str(getattr(assembly, "wall_name", "") or "").strip()
            linked_wall = self._wall_store.get(wall_name) if wall_name else None
            resolved_items = resolve_assembly_items(
                assembly,
                self._catalog,
                auto_double_front_width_mm=auto_double_width,
                linked_wall=linked_wall,
            )
            assembly_modules = len(resolved_items)
            modules_total += assembly_modules
            assembly_material_total = 0.0
            assembly_edgeband_total = 0.0
            assembly_hardware_total = 0.0

            for resolved in resolved_items:
                breakdown = resolved.cost_breakdown
                resolved_material_total = float(breakdown.material_total_pln)
                resolved_edgeband_total = float(breakdown.edgeband_total_pln)
                resolved_hardware_total = float(breakdown.hardware_total_pln)

                material_total += resolved_material_total
                edgeband_total += resolved_edgeband_total
                hardware_total += resolved_hardware_total

                assembly_material_total += resolved_material_total
                assembly_edgeband_total += resolved_edgeband_total
                assembly_hardware_total += resolved_hardware_total

                for line in breakdown.material_lines:
                    entry = material_acc[str(line.key or "-")]
                    entry["label"] = str(line.label or line.key or "-")
                    entry["count"] = float(entry["count"]) + float(line.count)
                    entry["area"] = float(entry["area"]) + float(line.area_m2)
                    entry["cost"] = float(entry["cost"]) + float(line.cost_pln)

            assembly_grand_total = assembly_material_total + assembly_edgeband_total + assembly_hardware_total
            assembly_commercial = float(assembly.commercial_sale_total(assembly_grand_total))

            assembly_rows.append(
                {
                    "name": str(getattr(assembly, "name", "") or "-"),
                    "wall_name": str(getattr(assembly, "wall_name", "") or "-"),
                    "modules": int(assembly_modules),
                    "material_total": float(assembly_material_total),
                    "edgeband_total": float(assembly_edgeband_total),
                    "hardware_total": float(assembly_hardware_total),
                    "grand_total": float(assembly_grand_total),
                    "commercial_total": float(assembly_commercial),
                }
            )

            commercial_total += assembly_commercial
            margin_total += float(
                assembly_commercial
                - (
                        assembly_grand_total
                        + float(getattr(assembly, "labor_cost_pln", 0.0) or 0.0)
                        + float(getattr(assembly, "transport_cost_pln", 0.0) or 0.0)
                        + float(getattr(assembly, "montage_cost_pln", 0.0) or 0.0)
                )
            )

        grand_total = material_total + edgeband_total + hardware_total
        if hasattr(self, "lab_metric_total"):
            self.lab_metric_total.setText(f"{commercial_total:.2f} zl")

        if assemblies:
            assembly_names = ", ".join(str(getattr(item, "name", "") or "-") for item in assemblies[:4])
            if len(assemblies) > 4:
                assembly_names += ", ..."
            self.lab_cost_summary.setText(
                f"Sciany: {wall_count}\n"
                f"Komplety: {len(assemblies)}\n"
                f"Moduly w kompletach: {modules_total}\n"
                f"Koszt techniczny: {grand_total:.2f} zl\n"
                f"Materialy: {material_total:.2f} zl\n"
                f"Okleina: {edgeband_total:.2f} zl\n"
                f"Okucia: {hardware_total:.2f} zl\n"
                f"Marza kwotowo: {margin_total:.2f} zl\n"
                f"Cena handlowa: {commercial_total:.2f} zl\n"
                f"Komplety w zamowieniu: {assembly_names}"
            )
        else:
            self.lab_cost_summary.setText(
                f"Sciany: {wall_count}\n"
                "Komplety: 0\n"
                "Koszt techniczny: 0.00 zl\n"
                "Materialy: 0.00 zl\n"
                "Okleina: 0.00 zl\n"
                "Okucia: 0.00 zl\n"
                "Marza kwotowo: 0.00 zl\n"
                "Cena handlowa: 0.00 zl\n"
                "Brak zapisanych kompletow dla tego zamowienia."
            )

        assembly_rows = sorted(
            assembly_rows,
            key=lambda item: (-float(item["grand_total"]), str(item["name"]).lower()),
        )
        self.tbl_order_assemblies.setRowCount(len(assembly_rows))
        for row, entry in enumerate(assembly_rows):
            items = (
                QTableWidgetItem(str(entry["name"] or "-")),
                QTableWidgetItem(str(entry["wall_name"] or "-")),
                QTableWidgetItem(str(int(entry["modules"]))),
                QTableWidgetItem(f'{float(entry["material_total"]):.2f} zl'),
                QTableWidgetItem(f'{float(entry["edgeband_total"]):.2f} zl'),
                QTableWidgetItem(f'{float(entry["grand_total"]):.2f} zl'),
            )
            for col, item in enumerate(items):
                self.tbl_order_assemblies.setItem(row, col, item)

        rows = sorted(
            material_acc.values(),
            key=lambda item: (-float(item["cost"]), str(item["label"]).lower()),
        )
        self.tbl_order_materials.setRowCount(len(rows))
        for row, entry in enumerate(rows):
            items = (
                QTableWidgetItem(str(entry["label"] or "-")),
                QTableWidgetItem(str(int(round(float(entry["count"]))))),
                QTableWidgetItem(f'{float(entry["area"]):.3f}'),
                QTableWidgetItem(f'{float(entry["cost"]):.2f} zl'),
            )
            for col, item in enumerate(items):
                self.tbl_order_materials.setItem(row, col, item)

        self.tbl_order_assemblies.resizeColumnsToContents()
        self.tbl_order_materials.resizeColumnsToContents()

    def _refresh_order_walls_table(self) -> None:
        if not hasattr(self, "tbl_walls"):
            return

        selected_name = self._selected_wall_name()
        walls = []
        for wall_name in self._current_order_wall_names():
            wall = self._wall_store.get(wall_name)
            if wall is not None:
                walls.append(wall)

        self.tbl_walls.setRowCount(len(walls))
        for row, wall in enumerate(walls):
            obstacle_count = len(getattr(wall, "obstacles", []) or [])
            layout_label = str(getattr(wall, "layout_type", "line") or "line")
            if layout_label == "line":
                layout_label = "Prosta"
            elif layout_label == "l":
                layout_label = "L"
            elif layout_label == "c":
                layout_label = "C"

            view_side = str(getattr(wall, "front_view_wall_side", "A") or "A").strip() or "A"
            items = (
                QTableWidgetItem(str(getattr(wall, "name", "") or "")),
                QTableWidgetItem(layout_label),
                QTableWidgetItem(str(obstacle_count)),
                QTableWidgetItem(f"Sciana {view_side}"),
            )
            for col, item in enumerate(items):
                item.setData(Qt.ItemDataRole.UserRole, str(getattr(wall, "name", "") or ""))
                self.tbl_walls.setItem(row, col, item)

        if walls:
            target_name = selected_name if selected_name else str(getattr(walls[0], "name", "") or "")
            for row in range(self.tbl_walls.rowCount()):
                row_name = str(self.tbl_walls.item(row, 0).data(Qt.ItemDataRole.UserRole) or "")
                if row_name == target_name:
                    self.tbl_walls.selectRow(row)
                    break
        self._on_walls_selection_changed()

    def _selected_wall_name(self) -> str:
        rows = self.tbl_walls.selectionModel().selectedRows() if self.tbl_walls.selectionModel() is not None else []
        if not rows:
            return ""
        item = self.tbl_walls.item(int(rows[0].row()), 0)
        if item is None:
            return ""
        return str(item.data(Qt.ItemDataRole.UserRole) or "").strip()

    def _on_walls_selection_changed(self) -> None:
        self.btn_open_wall.setEnabled(bool(self._selected_wall_name()))

    def _draft_payload(self) -> dict[str, object]:
        return {
            "client_name": str(self.cb_client_name.currentText().strip()),
            "client_id": str(self.ed_client_id.text().strip()),
            "client_first_name": str(self.ed_client_first_name.text().strip()),
            "client_last_name": str(self.ed_client_last_name.text().strip()),
            "client_phone": str(self.ed_client_phone.text().strip()),
            "client_email": str(self.ed_client_email.text().strip()),
            "client_street": str(self.ed_client_street.text().strip()),
            "client_house_number": str(self.ed_client_house_number.text().strip()),
            "client_apartment_number": str(self.ed_client_apartment_number.text().strip()),
            "client_postal_code": str(self.ed_client_postal_code.text().strip()),
            "client_city": str(self.ed_client_city.text().strip()),
            "client_notes": str(self.ed_client_notes.toPlainText().strip()),
            "order_id": str(self.ed_order_id.text().strip()),
            "order_code": str(self.ed_order_code.text().strip()),
            "order_status": str(self.cb_order_status.currentText().strip()),
            "order_progress_percent": int(self.sp_order_progress.value()),
            "order_calendar_stage": str(self._current_order_calendar_stage or ""),
            "order_calendar_date": str(self._current_order_calendar_date or ""),
            "order_calendar_note": str(self._current_order_calendar_note or ""),
            "order_address": str(self.ed_order_address.text().strip()),
            "order_site_street": str(self.ed_order_site_street.text().strip()),
            "order_site_house_number": str(self.ed_order_site_house_number.text().strip()),
            "order_site_apartment_number": str(self.ed_order_site_apartment_number.text().strip()),
            "order_site_postal_code": str(self.ed_order_site_postal_code.text().strip()),
            "order_site_city": str(self.ed_order_site_city.text().strip()),
            "order_notes": str(self.ed_order_notes.toPlainText().strip()),
            "order_date_wycena": self._date_edit_to_text(self.ed_date_wycena),
            "order_date_produkcja": self._date_edit_to_text(self.ed_date_produkcja),
            "order_date_zakup_mat": self._date_edit_to_text(self.ed_date_zakup_mat),
            "order_date_montaz": self._date_edit_to_text(self.ed_date_montaz),
            "order_date_poprawki": self._date_edit_to_text(self.ed_date_poprawki),
            "order_date_projekt": self._date_edit_to_text(self.ed_date_projekt),
            "order_date_probki": self._date_edit_to_text(self.ed_date_probki),
            "worker_id": str(self.ed_worker_id.text().strip()),
            "worker_name": str(self._worker_name_from_fields()),
            "worker_first_name": str(self.ed_worker_first_name.text().strip()),
            "worker_last_name": str(self.ed_worker_last_name.text().strip()),
            "worker_role": str(self.ed_worker_role.text().strip()),
            "worker_phone": str(self.ed_worker_phone.text().strip()),
            "worker_email": str(self.ed_worker_email.text().strip()),
            "worker_notes": str(self.ed_worker_notes.toPlainText().strip()),
            "architect_attachments": [dict(item) for item in self._architect_attachments],
            "quote_items": [dict(item) for item in self._quote_items],
            "material_choices": [dict(item) for item in self._material_choices],
            "customer_payments": [dict(item) for item in self._customer_payments],
        }

    def _has_meaningful_draft(self, payload: dict[str, object]) -> bool:
        ignored_keys = {"order_id"}
        for key, value in payload.items():
            if key in ignored_keys:
                continue
            if isinstance(value, str) and value.strip():
                return True
            if isinstance(value, list) and value:
                return True
        return False

    def _save_draft(self, show_status: bool) -> bool:
        if self._is_restoring_draft:
            return False
        payload = self._draft_payload()
        self._draft_store.save(payload)
        if show_status:
            self._set_status("Zapisano karte robocza zamowienia.", ok=True)
        return True

    def _load_draft(self, show_status: bool) -> bool:
        payload = self._draft_store.load()
        if not self._has_meaningful_draft(payload):
            return False

        self._is_restoring_draft = True
        try:
            self._reload_client_choices()
            self._reload_worker_choices()
            draft_client_name = str(payload.get("client_name", "") or "")
            self.cb_client_name.setCurrentText(draft_client_name)
            self.ed_client_id.setText(str(payload.get("client_id", "") or ""))
            self.ed_client_first_name.setText(str(payload.get("client_first_name", "") or ""))
            self.ed_client_last_name.setText(str(payload.get("client_last_name", "") or ""))
            if not self.ed_client_id.text().strip() and not self.ed_client_first_name.text().strip() and not self.ed_client_last_name.text().strip():
                parsed_client_id, parsed_full_name = self._split_client_key(draft_client_name)
                parsed_first_name, parsed_last_name = self._split_full_name(parsed_full_name)
                self.ed_client_id.setText(parsed_client_id)
                self.ed_client_first_name.setText(parsed_first_name)
                self.ed_client_last_name.setText(parsed_last_name)
            self.ed_client_phone.setText(str(payload.get("client_phone", "") or ""))
            self.ed_client_email.setText(str(payload.get("client_email", "") or ""))
            self.ed_client_street.setText(str(payload.get("client_street", "") or ""))
            self.ed_client_house_number.setText(str(payload.get("client_house_number", "") or ""))
            self.ed_client_apartment_number.setText(str(payload.get("client_apartment_number", "") or ""))
            self.ed_client_postal_code.setText(str(payload.get("client_postal_code", "") or ""))
            self.ed_client_city.setText(str(payload.get("client_city", "") or ""))
            self.ed_client_notes.setPlainText(str(payload.get("client_notes", "") or ""))

            self.ed_order_id.setText(str(payload.get("order_id", "") or self._generate_next_order_id()))
            self.ed_order_code.setText(str(payload.get("order_code", "") or ""))
            self.ed_order_name.setText(str(payload.get("order_name", "") or ""))
            order_status = str(payload.get("order_status", "") or "")
            idx = self.cb_order_status.findText(order_status)
            self.cb_order_status.setCurrentIndex(idx if idx >= 0 else 0)
            order_progress_percent = int(float(payload.get("order_progress_percent", 0.0) or 0.0))
            self.sp_order_progress.setValue(max(0, min(100, order_progress_percent)))
            self._current_order_calendar_stage = str(payload.get("order_calendar_stage", "") or "")
            self._current_order_calendar_date = str(payload.get("order_calendar_date", "") or "")
            self._current_order_calendar_note = str(payload.get("order_calendar_note", "") or "")
            draft_order_address = str(payload.get("order_address", "") or "")
            self.ed_order_address.setText(draft_order_address)
            self.ed_order_site_street.setText(str(payload.get("order_site_street", "") or ""))
            self.ed_order_site_house_number.setText(str(payload.get("order_site_house_number", "") or ""))
            self.ed_order_site_apartment_number.setText(str(payload.get("order_site_apartment_number", "") or ""))
            self.ed_order_site_postal_code.setText(str(payload.get("order_site_postal_code", "") or ""))
            self.ed_order_site_city.setText(str(payload.get("order_site_city", "") or ""))
            if not any(
                (
                    self.ed_order_site_street.text().strip(),
                    self.ed_order_site_house_number.text().strip(),
                    self.ed_order_site_apartment_number.text().strip(),
                    self.ed_order_site_postal_code.text().strip(),
                    self.ed_order_site_city.text().strip(),
                )
            ):
                self._set_order_address_parts_from_text(draft_order_address)
            self.ed_order_notes.setPlainText(str(payload.get("order_notes", "") or ""))
            self._set_date_edit_from_text(self.ed_date_wycena, str(payload.get("order_date_wycena", "") or ""))
            self._set_date_edit_from_text(self.ed_date_produkcja, str(payload.get("order_date_produkcja", "") or ""))
            self._set_date_edit_from_text(self.ed_date_zakup_mat, str(payload.get("order_date_zakup_mat", "") or ""))
            self._set_date_edit_from_text(self.ed_date_montaz, str(payload.get("order_date_montaz", "") or ""))
            self._set_date_edit_from_text(self.ed_date_poprawki, str(payload.get("order_date_poprawki", "") or ""))
            self._set_date_edit_from_text(self.ed_date_projekt, str(payload.get("order_date_projekt", "") or ""))
            self._set_date_edit_from_text(self.ed_date_probki, str(payload.get("order_date_probki", "") or ""))

            worker_name = str(payload.get("worker_name", "") or "")
            worker_first_name = str(payload.get("worker_first_name", "") or "")
            worker_last_name = str(payload.get("worker_last_name", "") or "")
            if not worker_first_name and not worker_last_name:
                worker_first_name, worker_last_name = self._split_full_name(worker_name)
            self.ed_worker_id.setText(str(payload.get("worker_id", "") or ""))
            self.cb_worker_name.setCurrentText(worker_name)
            self.ed_worker_first_name.setText(worker_first_name)
            self.ed_worker_last_name.setText(worker_last_name)
            self.ed_worker_name_input.setText(worker_name)
            self.ed_worker_role.setText(str(payload.get("worker_role", "") or ""))
            self.ed_worker_phone.setText(str(payload.get("worker_phone", "") or ""))
            self.ed_worker_email.setText(str(payload.get("worker_email", "") or ""))
            self.ed_worker_notes.setPlainText(str(payload.get("worker_notes", "") or ""))
            self._set_architect_attachments(list(payload.get("architect_attachments", []) or []))
            self._set_quote_items(list(payload.get("quote_items", []) or []))
            self._set_material_choices(list(payload.get("material_choices", []) or []))
            self._set_customer_payments(list(payload.get("customer_payments", []) or []))
        finally:
            self._is_restoring_draft = False

        self._refresh_summary()
        if show_status:
            self._set_status("Przywrocono zapis roboczy zamowienia.", ok=True)
        return True

    def _autosave_draft(self) -> None:
        if self._is_restoring_draft:
            return
        self._draft_store.save(self._draft_payload())

    def _reload_client_choices(self) -> None:
        current = self.cb_client_name.currentText().strip()
        self.cb_client_name.blockSignals(True)
        try:
            self.cb_client_name.clear()
            self.cb_client_name.addItem("")
            for name in self._client_store.list_names():
                self.cb_client_name.addItem(name)
            self.cb_client_name.setCurrentText(current)
        finally:
            self.cb_client_name.blockSignals(False)

    def _reload_worker_choices(self) -> None:
        current = self._worker_name_from_fields()
        self.cb_worker_name.blockSignals(True)
        try:
            self.cb_worker_name.clear()
            self.cb_worker_name.addItem("")
            for name in self._worker_store.list_names():
                self.cb_worker_name.addItem(name)
            self.cb_worker_name.setCurrentText(current)
        finally:
            self.cb_worker_name.blockSignals(False)

    @staticmethod
    def _split_client_key(value: str) -> tuple[str, str]:
        text = str(value or "").strip()
        if "|" not in text:
            return "", text
        client_id, full_name = text.split("|", 1)
        return client_id.strip(), full_name.strip()

    @staticmethod
    def _split_full_name(full_name: str) -> tuple[str, str]:
        parts = str(full_name or "").strip().split()
        if not parts:
            return "", ""
        if len(parts) == 1:
            return parts[0], ""
        return parts[0], " ".join(parts[1:])

    def _new_calendar_date_edit(self, parent: QWidget) -> QDateEdit:
        editor = QDateEdit(parent)
        editor.setCalendarPopup(True)
        editor.setDisplayFormat("yyyy-MM-dd")
        editor.setMinimumDate(QDate(2026, 1, 1))
        editor.setSpecialValueText("")
        editor.setDate(QDate.currentDate())
        editor.setMaximumWidth(140)
        editor.dateChanged.connect(lambda _date: self._refresh_summary())
        return editor

    @staticmethod
    def _date_edit_to_text(editor: QDateEdit) -> str:
        date_value = editor.date()
        if not date_value.isValid():
            return ""
        return str(date_value.toString("yyyy-MM-dd"))

    @staticmethod
    def _set_date_edit_from_text(editor: QDateEdit, value: str) -> None:
        text = str(value or "").strip()
        parsed = QDate.fromString(text, "yyyy-MM-dd")
        if parsed.isValid():
            editor.setDate(parsed)
            return
        editor.setDate(QDate.currentDate())

    @staticmethod
    def _build_client_key(client_id: str, first_name: str, last_name: str, fallback_name: str = "") -> str:
        cid = str(client_id or "").strip()
        first = str(first_name or "").strip()
        last = str(last_name or "").strip()
        full_name = " ".join(part for part in (first, last) if part).strip()
        if cid and full_name:
            return f"{cid} | {full_name}"
        if full_name:
            return full_name
        return str(fallback_name or "").strip()

    def _worker_name_from_fields(self) -> str:
        first = str(self.ed_worker_first_name.text().strip())
        last = str(self.ed_worker_last_name.text().strip())
        full_name = " ".join(part for part in (first, last) if part).strip()
        if full_name:
            return full_name
        return str(self.ed_worker_name_input.text().strip() or self.cb_worker_name.currentText().strip())

    def _set_worker_fields_from_full_name(self, full_name: str) -> None:
        worker_name = str(full_name or "").strip()
        first_name, last_name = self._split_full_name(worker_name)
        self._is_syncing_worker_name = True
        try:
            self.ed_worker_first_name.blockSignals(True)
            self.ed_worker_last_name.blockSignals(True)
            self.ed_worker_name_input.blockSignals(True)
            try:
                self.ed_worker_first_name.setText(first_name)
                self.ed_worker_last_name.setText(last_name)
                self.ed_worker_name_input.setText(worker_name)
            finally:
                self.ed_worker_name_input.blockSignals(False)
                self.ed_worker_last_name.blockSignals(False)
                self.ed_worker_first_name.blockSignals(False)
        finally:
            self._is_syncing_worker_name = False

    def _clear_worker_base_fields(self) -> None:
        self.ed_worker_id.clear()
        self.ed_worker_role.clear()
        self.ed_worker_phone.clear()
        self.ed_worker_email.clear()
        self.ed_worker_notes.clear()

    def _generate_next_client_id(self) -> str:
        max_id = 0
        for client in self._client_store.list_clients():
            raw_id = str(getattr(client, "client_id", "") or "").strip()
            if not raw_id:
                raw_id, _ = self._split_client_key(str(getattr(client, "name", "") or ""))
            match = re.search(r"(\d+)$", raw_id)
            if match is None:
                continue
            max_id = max(max_id, int(match.group(1)))
        return f"K{max_id + 1:04d}"

    def _generate_next_order_id(self) -> str:
        used_ids = {str(item or "").strip() for item in self._generated_order_ids if str(item or "").strip()}
        current_id = str(getattr(self, "ed_order_id", None).text().strip()) if hasattr(self, "ed_order_id") else ""
        if current_id:
            used_ids.add(current_id)

        for order in self._order_store.list_orders():
            raw_id = str(getattr(order, "order_id", "") or "").strip()
            if raw_id:
                used_ids.add(raw_id)

        draft_id = str(self._draft_store.load().get("order_id", "") or "").strip()
        if draft_id:
            used_ids.add(draft_id)

        base_candidate = f"ORD-{datetime.now().strftime('%y%m%d')}"
        candidate = base_candidate
        suffix = 1
        while candidate in used_ids:
            candidate = f"{base_candidate}-{suffix:02d}"
            suffix += 1
        self._generated_order_ids.add(candidate)
        return candidate

    def _generate_next_worker_id(self) -> str:
        max_id = 0
        for worker in self._worker_store.list_workers():
            raw_id = str(getattr(worker, "worker_id", "") or "").strip()
            match = re.search(r"(\d+)$", raw_id)
            if match is None:
                continue
            max_id = max(max_id, int(match.group(1)))
        return f"P{max_id + 1:04d}"

    def _on_client_name_changed(self, text: str) -> None:
        selected_name = str(text or "").strip()
        client = self._client_store.get(selected_name)
        if client is None:
            parsed_client_id, parsed_full_name = self._split_client_key(selected_name)
            if parsed_client_id:
                parsed_first_name, parsed_last_name = self._split_full_name(parsed_full_name)
                self.ed_client_id.setText(parsed_client_id)
                self.ed_client_first_name.setText(parsed_first_name)
                self.ed_client_last_name.setText(parsed_last_name)
            self._refresh_summary()
            return
        parsed_client_id, parsed_full_name = self._split_client_key(client.name)
        parsed_first_name, parsed_last_name = self._split_full_name(parsed_full_name)
        self.ed_client_id.setText(str(getattr(client, "client_id", "") or parsed_client_id))
        self.ed_client_first_name.setText(str(getattr(client, "first_name", "") or parsed_first_name))
        self.ed_client_last_name.setText(str(getattr(client, "last_name", "") or parsed_last_name))
        self.ed_client_phone.setText(client.phone)
        self.ed_client_email.setText(client.email)
        self.ed_client_street.setText(str(getattr(client, "street", "") or ""))
        self.ed_client_house_number.setText(str(getattr(client, "house_number", "") or ""))
        self.ed_client_apartment_number.setText(str(getattr(client, "apartment_number", "") or ""))
        self.ed_client_postal_code.setText(str(getattr(client, "postal_code", "") or ""))
        self.ed_client_city.setText(client.city)
        self.ed_client_notes.setPlainText(client.notes)
        self._refresh_summary()

    def _on_worker_name_changed(self, text: str) -> None:
        worker_name = str(text or "").strip()
        self._set_worker_fields_from_full_name(worker_name)
        worker = self._worker_store.get(worker_name)
        if worker is None:
            if not self._is_restoring_draft:
                self._clear_worker_base_fields()
            self._refresh_summary()
            return
        self._set_worker_fields_from_full_name(
            " ".join(
                part
                for part in (
                    str(getattr(worker, "first_name", "") or worker.get_first_name()).strip(),
                    str(getattr(worker, "last_name", "") or worker.get_last_name()).strip(),
                )
                if part
            ).strip()
            or worker_name
        )
        self.ed_worker_id.setText(str(getattr(worker, "worker_id", "") or ""))
        self.ed_worker_role.setText(worker.role)
        self.ed_worker_phone.setText(worker.phone)
        self.ed_worker_email.setText(worker.email)
        self.ed_worker_notes.setPlainText(worker.notes)
        self._refresh_summary()

    def _on_worker_name_input_changed(self, text: str) -> None:
        worker_name = str(text or "").strip()
        if self.cb_worker_name.currentText().strip() != worker_name:
            self.cb_worker_name.blockSignals(True)
            try:
                self.cb_worker_name.setCurrentText(worker_name)
            finally:
                self.cb_worker_name.blockSignals(False)
        self._on_worker_name_changed(worker_name)

    def _on_worker_name_parts_changed(self, _text: str) -> None:
        if self._is_syncing_worker_name:
            return
        worker_name = self._worker_name_from_fields()
        self._is_syncing_worker_name = True
        try:
            self.ed_worker_name_input.blockSignals(True)
            self.cb_worker_name.blockSignals(True)
            try:
                self.ed_worker_name_input.setText(worker_name)
                self.cb_worker_name.setCurrentText(worker_name)
            finally:
                self.cb_worker_name.blockSignals(False)
                self.ed_worker_name_input.blockSignals(False)
        finally:
            self._is_syncing_worker_name = False
        self._on_worker_name_changed(worker_name)

    def _client_from_form(self) -> ClientDef:
        client_id = str(self.ed_client_id.text().strip())
        first_name = str(self.ed_client_first_name.text().strip())
        last_name = str(self.ed_client_last_name.text().strip())
        typed_name = str(self.cb_client_name.currentText().strip())
        client_name = self._build_client_key(
            client_id=client_id,
            first_name=first_name,
            last_name=last_name,
            fallback_name=typed_name,
        )
        return ClientDef(
            name=client_name,
            phone=str(self.ed_client_phone.text().strip()),
            email=str(self.ed_client_email.text().strip()),
            street=str(self.ed_client_street.text().strip()),
            house_number=str(self.ed_client_house_number.text().strip()),
            apartment_number=str(self.ed_client_apartment_number.text().strip()),
            postal_code=str(self.ed_client_postal_code.text().strip()),
            city=str(self.ed_client_city.text().strip()),
            notes=str(self.ed_client_notes.toPlainText().strip()),
            client_id=client_id,
            first_name=first_name,
            last_name=last_name,
        )

    def _worker_from_form(self) -> WorkerDef:
        worker_name = str(self._worker_name_from_fields())
        worker_first_name = str(self.ed_worker_first_name.text().strip())
        worker_last_name = str(self.ed_worker_last_name.text().strip())
        if not worker_first_name and not worker_last_name:
            worker_first_name, worker_last_name = self._split_full_name(worker_name)
        return WorkerDef(
            name=worker_name,
            first_name=worker_first_name,
            last_name=worker_last_name,
            worker_id=str(self.ed_worker_id.text().strip()),
            role=str(self.ed_worker_role.text().strip()),
            phone=str(self.ed_worker_phone.text().strip()),
            email=str(self.ed_worker_email.text().strip()),
            notes=str(self.ed_worker_notes.toPlainText().strip()),
        )

    def _order_from_form(self) -> OrderDef:
        client_name = self._build_client_key(
            client_id=self.ed_client_id.text().strip(),
            first_name=self.ed_client_first_name.text().strip(),
            last_name=self.ed_client_last_name.text().strip(),
            fallback_name=self.cb_client_name.currentText().strip(),
        )
        site_address = self._build_order_address_from_parts() or str(self.ed_order_address.text().strip())
        return OrderDef(
            code=str(self.ed_order_code.text().strip()),
            order_name=str(self.ed_order_name.text().strip()),
            order_id=str(self.ed_order_id.text().strip()),
            client_name=client_name,
            worker_name=str(self._worker_name_from_fields()),
            status=str(self.cb_order_status.currentText().strip() or "Nowe"),
            progress_percent=float(self.sp_order_progress.value()),
            calendar_stage=str(self._current_order_calendar_stage or ""),
            calendar_date=str(self._current_order_calendar_date or ""),
            calendar_note=str(self._current_order_calendar_note or ""),
            site_address=site_address,
            site_street=str(self.ed_order_site_street.text().strip()),
            site_house_number=str(self.ed_order_site_house_number.text().strip()),
            site_apartment_number=str(self.ed_order_site_apartment_number.text().strip()),
            site_postal_code=str(self.ed_order_site_postal_code.text().strip()),
            site_city=str(self.ed_order_site_city.text().strip()),
            notes=str(self.ed_order_notes.toPlainText().strip()),
            date_wycena=self._date_edit_to_text(self.ed_date_wycena),
            date_produkcja=self._date_edit_to_text(self.ed_date_produkcja),
            date_zakup_mat=self._date_edit_to_text(self.ed_date_zakup_mat),
            date_montaz=self._date_edit_to_text(self.ed_date_montaz),
            date_poprawki=self._date_edit_to_text(self.ed_date_poprawki),
            date_projekt=self._date_edit_to_text(self.ed_date_projekt),
            date_probki=self._date_edit_to_text(self.ed_date_probki),
            attachments=[dict(item) for item in self._architect_attachments],
            quote_items=[dict(item) for item in self._quote_items],
            material_choices=[dict(item) for item in self._material_choices],
            customer_payments=[dict(item) for item in self._customer_payments],
        )

    def current_order_context(self) -> dict[str, object]:
        order = self._order_from_form()
        return {
            "client_name": str(order.client_name or "").strip(),
            "order_id": str(order.order_id or "").strip(),
            "order_name": str(order.code or "").strip(),
            "worker_name": str(order.worker_name or "").strip(),
            "order_status": str(order.status or "").strip(),
            "order_progress_percent": float(order.progress_percent or 0.0),
            "order_calendar_stage": str(order.calendar_stage or "").strip(),
            "order_calendar_date": str(order.calendar_date or "").strip(),
            "order_calendar_note": str(order.calendar_note or "").strip(),
            "order_notes": str(order.notes or "").strip(),
            "site_address": str(order.site_address or "").strip(),
            "site_street": str(order.site_street or "").strip(),
            "site_house_number": str(order.site_house_number or "").strip(),
            "site_apartment_number": str(order.site_apartment_number or "").strip(),
            "site_postal_code": str(order.site_postal_code or "").strip(),
            "site_city": str(order.site_city or "").strip(),
        }

    def _set_status(self, message: str, ok: bool) -> None:
        color = "#2d6a4f" if ok else "#b42318"
        self.lab_status.setStyleSheet(f"color:{color};")
        self.lab_status.setText(str(message or ""))
        self._refresh_summary()

    def _save_client(self, overwrite: bool) -> tuple[bool, str]:
        if not str(self.ed_client_id.text().strip()):
            self.ed_client_id.setText(self._generate_next_client_id())
        client = self._client_from_form()
        if not client.name:
            return False, "Podaj dane klienta (ID, imie, nazwisko)."
        if overwrite:
            result = self._client_store.overwrite(client)
        else:
            existing = self._client_store.get(client.name)
            result = self._client_store.overwrite(client) if existing is not None else self._client_store.save_new(client)
        self._reload_client_choices()
        self.cb_client_name.setCurrentText(client.name)
        return result.ok, result.message_pl

    def _save_worker(self, overwrite: bool) -> tuple[bool, str]:
        if not str(self.ed_worker_id.text().strip()):
            self.ed_worker_id.setText(self._generate_next_worker_id())
        worker = self._worker_from_form()
        if not worker.name:
            return False, "Podaj imie i nazwisko pracownika."
        if overwrite:
            result = self._worker_store.overwrite(worker)
        else:
            existing = self._worker_store.get(worker.name)
            result = self._worker_store.overwrite(worker) if existing is not None else self._worker_store.save_new(worker)
        self._reload_worker_choices()
        self.cb_worker_name.setCurrentText(worker.name)
        self.ed_worker_name_input.setText(worker.name)
        return result.ok, result.message_pl

    def _save_order(self, overwrite: bool) -> tuple[bool, str]:
        if not str(self.ed_order_id.text().strip()):
            self.ed_order_id.setText(self._generate_next_order_id())
        order = self._order_from_form()
        if not order.code:
            return False, "Podaj kod zamowienia."
        if not order.client_name:
            return False, "Wybierz klienta albo wpisz nowego klienta."

        existing_order = self._order_store.get(order.code)
        order = self._with_status_history(order, existing_order)

        if overwrite:
            result = self._order_store.overwrite(order)
        else:
            result = self._order_store.overwrite(order) if existing_order is not None else self._order_store.save_new(order)
        if not result.ok:
            return result.ok, result.message_pl

        calendar_msg = self._sync_calendar_events_for_order(order)
        message = str(result.message_pl or "")
        if calendar_msg:
            message = (message + "\n" + calendar_msg).strip()
        
        # Auto-deduct materials when order enters production phase
        inventory_msg = self._deduct_materials_on_status_change(order, existing_order)
        if inventory_msg:
            message = (message + "\n" + inventory_msg).strip()
        
        # Run alarm checks for this order
        try:
            alarm_service = AlarmService.instance()
            new_alarms = alarm_service.run_all_checks({"order_code": order.code})
            if new_alarms:
                alarm_msgs = [f"⚠ Wygenerowano {len(new_alarms)} alarm(ów)"]
                for alarm in new_alarms[:3]:  # Show first 3
                    alarm_msgs.append(f"  - {alarm.title}")
                if len(new_alarms) > 3:
                    alarm_msgs.append(f"  ... i {len(new_alarms) - 3} więcej")
                message = (message + "\n" + "\n".join(alarm_msgs)).strip()
        except Exception as e:
            print(f"Alarm check failed: {e}")
        
        # Sync to calendar (generate calendar events from order)
        try:
            sync_single_order(order.code)
        except Exception as e:
            print(f"Calendar sync failed: {e}")
        
        return True, message
    
    def _deduct_materials_on_status_change(self, order: OrderDef, existing_order: OrderDef | None) -> str:
        """
        Automatically deduct materials from inventory when order status changes
        to a production phase (Zakup materialow, W produkcji).
        
        Returns:
            Message about inventory changes, or empty string if no changes.
        """
        import json
        from src.storage.data_paths import data_dir
        
        # Statuses that trigger material deduction
        PRODUCTION_STATUSES = {"Zakup materialow", "W produkcji", "Lakiernia", "Montaz"}
        
        new_status = str(getattr(order, "status", "") or "").strip()
        
        # Only deduct if entering production for the first time
        if new_status not in PRODUCTION_STATUSES:
            return ""
        
        # Check if order was already in production (don't deduct twice)
        if existing_order:
            old_status = str(getattr(existing_order, "status", "") or "").strip()
            if old_status in PRODUCTION_STATUSES:
                return ""  # Already in production, don't deduct again
        
        # Get material choices that are "wybrane finalnie"
        raw_choices = getattr(order, "material_choices", [])
        choices = [x for x in raw_choices if isinstance(x, dict)]
        final_choices = [x for x in choices if str(x.get("status", "") or "").strip().lower() == "wybrane finalnie"]
        
        if not final_choices:
            return f"ℹ Zamówienie {order.code}: brak wybranych materiałów do odjęcia"
        
        # Load material database
        material_path = data_dir() / "baza_materialu.json"
        try:
            raw = json.loads(material_path.read_text(encoding="utf-8")) if material_path.exists() else {}
            material_data = raw if isinstance(raw, dict) else {}
            rows = material_data.get("rows", [])
        except Exception as e:
            return f"⚠ Nie można odjąć materiałów: błąd odczytu bazy ({e})"
        
        # Build index for quick lookup
        by_id: dict[str, int] = {}
        by_name: dict[str, int] = {}
        for i, row in enumerate(rows):
            mat_id = str(row.get("id", "") or "").strip()
            name = str(row.get("nazwa", "") or "").strip()
            if mat_id:
                by_id[mat_id] = i
            if name:
                by_name[name.lower()] = i
        
        def _safe_float(value) -> float:
            raw = str(value or "").strip().replace(" ", "").replace(",", ".")
            try:
                return float(raw) if raw else 0.0
            except ValueError:
                return 0.0
        
        deducted_items = []
        missing_items = []
        
        for choice in final_choices:
            mat_name = str(choice.get("material_name", "") or "").strip()
            mat_id = str(choice.get("material_id", "") or "").strip()
            qty_needed = _safe_float(choice.get("qty", 0.0))
            
            if qty_needed <= 0:
                continue
            
            # Find material in database
            key = mat_id if mat_id else mat_name.lower()
            row_idx = by_id.get(key) if key in by_id else by_name.get(key.lower())
            
            if row_idx is None:
                missing_items.append(mat_name or mat_id)
                continue
            
            row = rows[row_idx]
            current_stock = _safe_float(row.get("ilosc_magazyn", row.get("ilosc", 0.0)))
            new_stock = max(0.0, current_stock - qty_needed)
            
            # Update stock in database
            rows[row_idx]["ilosc_magazyn"] = new_stock
            deducted_items.append(f"{mat_name}: -{qty_needed:.1f} (zostało: {new_stock:.1f})")
        
        # Save updated material database
        try:
            material_data["rows"] = rows
            material_path.write_text(json.dumps(material_data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            return f"⚠ Nie można zapisać bazy materiałów: {e}"
        
        # Build result message
        messages = []
        if deducted_items:
            messages.append(f"📦 Odjęto materiały dla {order.code}:")
            for item in deducted_items[:5]:
                messages.append(f"  • {item}")
            if len(deducted_items) > 5:
                messages.append(f"  ... i {len(deducted_items) - 5} więcej")
        
        if missing_items:
            messages.append(f"⚠ Brak w bazie: {', '.join(missing_items[:3])}")
        
        return "\n".join(messages) if messages else ""

    def _sync_calendar_events_for_order(self, order: OrderDef) -> str:
        order_code = str(getattr(order, "code", "") or "").strip()
        if not order_code:
            return ""

        marker_prefix = "AUTO_ORDER_STAGE:"
        stage_labels = {
            "wycena": "Wycena",
            "projekt": "Projekt",
            "probki": "Probki materialow",
            "zakup_mat": "Zakup materialow",
            "produkcja": "Produkcja",
            "montaz": "Montaz",
            "poprawki": "Poprawki",
        }

        all_events = list(self._calendar_store.list_events() or [])
        managed_events: dict[str, CalendarEvent] = {}
        for event in all_events:
            if str(getattr(event, "order_code", "") or "").strip() != order_code:
                continue
            notes = str(getattr(event, "notes", "") or "")
            if not notes.startswith(marker_prefix):
                continue
            marker_line = notes.splitlines()[0].strip()
            stage_key = marker_line.removeprefix(marker_prefix).strip().lower()
            if stage_key:
                managed_events[stage_key] = event

        active_stage_keys: set[str] = set()
        for stage_key, field_name, event_type, station in self._ORDER_STAGE_CALENDAR_MAP:
            date_value = str(getattr(order, field_name, "") or "").strip()
            if not date_value:
                continue
            active_stage_keys.add(stage_key)

            title = f"{order_code} - {stage_labels.get(stage_key, stage_key.title())}"
            notes = f"{marker_prefix}{stage_key}"
            worker_name = str(getattr(order, "worker_name", "") or "").strip()

            existing = managed_events.get(stage_key)
            if existing is not None:
                self._calendar_store.save(
                    CalendarEvent(
                        id=str(existing.id or ""),
                        event_type=event_type,
                        station=station,
                        title=title,
                        date=date_value,
                        worker_name=worker_name,
                        order_code=order_code,
                        notes=notes,
                    )
                )
            else:
                self._calendar_store.save(
                    CalendarEvent.new(
                        event_type=event_type,
                        station=station,
                        title=title,
                        date=date_value,
                        worker_name=worker_name,
                        order_code=order_code,
                        notes=notes,
                    )
                )

        for stage_key, event in managed_events.items():
            if stage_key not in active_stage_keys:
                self._calendar_store.delete(str(getattr(event, "id", "") or ""))

        return "Kalendarz: zaktualizowano terminy zamowienia."

    def _with_status_history(self, order: OrderDef, previous: OrderDef | None) -> OrderDef:
        base_history = list(getattr(previous, "status_history", []) or []) if previous is not None else []

        if previous is None:
            return OrderDef.from_dict({**order.to_dict(), "status_history": base_history})

        prev_status = str(getattr(previous, "status", "") or "").strip()
        new_status = str(getattr(order, "status", "") or "").strip()
        prev_progress = int(round(float(getattr(previous, "progress_percent", 0.0) or 0.0)))
        new_progress = int(round(float(getattr(order, "progress_percent", 0.0) or 0.0)))
        prev_stage = str(getattr(previous, "calendar_stage", "") or "").strip()
        new_stage = str(getattr(order, "calendar_stage", "") or "").strip()

        changed = (
            prev_status != new_status
            or prev_progress != new_progress
            or prev_stage != new_stage
        )
        if not changed:
            return OrderDef.from_dict({**order.to_dict(), "status_history": base_history})

        note_parts: list[str] = []
        if prev_progress != new_progress:
            note_parts.append(f"postep {prev_progress}% -> {new_progress}%")
        if prev_stage != new_stage:
            note_parts.append(f"etap {prev_stage or '-'} -> {new_stage or '-'}")

        calendar_note = str(getattr(order, "calendar_note", "") or "").strip()
        if calendar_note:
            note_parts.append(calendar_note)

        base_history.append(
            {
                "changed_at": datetime.now().isoformat(timespec="seconds"),
                "from_status": prev_status,
                "to_status": new_status,
                "changed_by": str(getattr(order, "worker_name", "") or self._worker_name_from_fields() or "").strip(),
                "note": " | ".join(note_parts),
            }
        )

        if len(base_history) > 200:
            base_history = base_history[-200:]

        return OrderDef.from_dict({**order.to_dict(), "status_history": base_history})

    def _on_save_client_to_base(self) -> None:
        ok, message = self._save_client(overwrite=False)
        self._set_status(message, ok=ok)

    def _on_save_worker_to_base(self) -> None:
        ok, message = self._save_worker(overwrite=False)
        self._set_status(message, ok=ok)

    def _on_save_order_to_base(self) -> None:
        client_ok, client_message = self._save_client(overwrite=False)
        if not client_ok:
            self._set_status(client_message, ok=False)
            return
        worker_name = str(self._worker_name_from_fields())
        messages = [client_message]
        if worker_name:
            worker_ok, worker_message = self._save_worker(overwrite=False)
            if not worker_ok:
                self._set_status(worker_message, ok=False)
                return
            messages.append(worker_message)
        order_ok, order_message = self._save_order(overwrite=False)
        messages.append(order_message)
        self._set_status("\n".join(messages), ok=order_ok)

    def _on_pick_client_from_base(self) -> None:
        names = self._client_store.list_names()
        if not names:
            self._set_status("Baza klientow jest pusta.", ok=False)
            return
        picked, ok = QInputDialog.getItem(
            self,
            "Wybierz klienta",
            "Klient z bazy:",
            names,
            0,
            False,
        )
        if not ok:
            return
        self.cb_client_name.setCurrentText(str(picked or ""))

    def _on_pick_worker_from_base(self) -> None:
        names = self._worker_store.list_names()
        if not names:
            self._set_status("Baza pracownikow jest pusta.", ok=False)
            return
        picked, ok = QInputDialog.getItem(
            self,
            "Wybierz pracownika",
            "Pracownik z bazy:",
            names,
            0,
            False,
        )
        if not ok:
            return
        self.cb_worker_name.setCurrentText(str(picked or ""))
        self.ed_worker_name_input.setText(str(picked or ""))

    def _on_pick_order_from_base(self) -> None:
        self._set_entry_editor_visible(True)
        codes = self._order_store.list_codes()
        if not codes:
            self._set_status("Baza zamowien jest pusta.", ok=False)
            return
        picked, ok = QInputDialog.getItem(
            self,
            "Wczytaj zamowienie",
            "Kod zamowienia:",
            codes,
            0,
            False,
        )
        if not ok:
            return
        order = self._order_store.get(str(picked or ""))
        if order is None:
            self._set_status("Nie udalo sie wczytac zamowienia.", ok=False)
            return
        self.ed_order_id.setText(str(getattr(order, "order_id", "") or self._generate_next_order_id()))
        self.ed_order_code.setText(order.code)
        self.ed_order_name.setText(str(getattr(order, "order_name", "") or ""))
        self.cb_client_name.setCurrentText(order.client_name)
        self.cb_worker_name.setCurrentText(order.worker_name)
        self.ed_worker_name_input.setText(order.worker_name)
        idx = self.cb_order_status.findText(order.status)
        self.cb_order_status.setCurrentIndex(idx if idx >= 0 else 0)
        self.sp_order_progress.setValue(max(0, min(100, int(round(float(getattr(order, "progress_percent", 0.0) or 0.0))))))
        self._current_order_calendar_stage = str(getattr(order, "calendar_stage", "") or "")
        self._current_order_calendar_date = str(getattr(order, "calendar_date", "") or "")
        self._current_order_calendar_note = str(getattr(order, "calendar_note", "") or "")
        self.ed_order_address.setText(order.site_address)
        self.ed_order_site_street.setText(str(getattr(order, "site_street", "") or ""))
        self.ed_order_site_house_number.setText(str(getattr(order, "site_house_number", "") or ""))
        self.ed_order_site_apartment_number.setText(str(getattr(order, "site_apartment_number", "") or ""))
        self.ed_order_site_postal_code.setText(str(getattr(order, "site_postal_code", "") or ""))
        self.ed_order_site_city.setText(str(getattr(order, "site_city", "") or ""))
        if not any(
            (
                self.ed_order_site_street.text().strip(),
                self.ed_order_site_house_number.text().strip(),
                self.ed_order_site_apartment_number.text().strip(),
                self.ed_order_site_postal_code.text().strip(),
                self.ed_order_site_city.text().strip(),
            )
        ):
            self._set_order_address_parts_from_text(order.site_address)
        self.ed_order_notes.setPlainText(order.notes)
        self._set_date_edit_from_text(self.ed_date_wycena, str(getattr(order, "date_wycena", "") or ""))
        self._set_date_edit_from_text(self.ed_date_produkcja, str(getattr(order, "date_produkcja", "") or ""))
        self._set_date_edit_from_text(self.ed_date_zakup_mat, str(getattr(order, "date_zakup_mat", "") or ""))
        self._set_date_edit_from_text(self.ed_date_montaz, str(getattr(order, "date_montaz", "") or ""))
        self._set_date_edit_from_text(self.ed_date_poprawki, str(getattr(order, "date_poprawki", "") or ""))
        self._set_date_edit_from_text(self.ed_date_projekt, str(getattr(order, "date_projekt", "") or ""))
        self._set_date_edit_from_text(self.ed_date_probki, str(getattr(order, "date_probki", "") or ""))
        self._set_architect_attachments(list(getattr(order, "attachments", []) or []))
        self._set_quote_items(list(getattr(order, "quote_items", []) or []))
        self._set_material_choices(list(getattr(order, "material_choices", []) or []))
        self._set_customer_payments(list(getattr(order, "customer_payments", []) or []))
        self._set_status(f'Wczytano zamowienie "{order.code}".', ok=True)

    def _ensure_context_saved_for_next_step(self) -> tuple[bool, str]:
        client_name = self._client_from_form().name
        worker_name = str(self._worker_name_from_fields())
        order_code = self.ed_order_code.text().strip()

        messages: list[str] = []

        if client_name:
            ok, message = self._save_client(overwrite=False)
            if not ok:
                return False, message
            messages.append(message)

        if worker_name:
            ok, message = self._save_worker(overwrite=False)
            if not ok:
                return False, message
            messages.append(message)

        if order_code and client_name:
            ok, message = self._save_order(overwrite=False)
            if not ok:
                return False, message
            messages.append(message)

        return True, "\n".join([msg for msg in messages if msg])

    def _on_go_to_sciana(self) -> None:
        ok, message = self._ensure_context_saved_for_next_step()
        if not ok:
            self._set_status(message, ok=False)
            return
        self._save_draft(show_status=False)
        if message:
            self._set_status(message, ok=True)
        self.sig_open_sciana_requested.emit(self.current_order_context())

    def _on_open_selected_wall(self) -> None:
        wall_name = self._selected_wall_name()
        if not wall_name:
            self._set_status("Wybierz sciane z listy tego zamowienia.", ok=False)
            return
        self.sig_open_existing_sciana_requested.emit(wall_name)

    def _validate_required(self) -> tuple[bool, str]:
        order = self._order_from_form()
        if not order.code:
            return False, "Podaj kod zamowienia."
        if not order.client_name:
            return False, "Podaj klienta (ID, imie i nazwisko)."
        return True, ""

    def _on_save_new(self) -> None:
        is_valid, message = self._validate_required()
        if not is_valid:
            self._set_status(message, ok=False)
            return

        client = self._client_from_form()
        worker = self._worker_from_form()
        order = self._order_from_form()
        order = self._with_status_history(order, self._order_store.get(order.code))

        if self._order_store.get(order.code) is not None:
            self._set_status(f'Zamowienie "{order.code}" juz istnieje. Uzyj "Nadpisz wszystko".', ok=False)
            return

        messages: list[str] = []

        if client.name:
            if self._client_store.get(client.name) is None:
                result = self._client_store.save_new(client)
                if not result.ok:
                    self._set_status(result.message_pl, ok=False)
                    return
                messages.append(result.message_pl)
            else:
                messages.append(f'Klient "{client.name}" zostal powiazany z wpisem z bazy.')

        if worker.name:
            if self._worker_store.get(worker.name) is None:
                result = self._worker_store.save_new(worker)
                if not result.ok:
                    self._set_status(result.message_pl, ok=False)
                    return
                messages.append(result.message_pl)
            else:
                messages.append(f'Pracownik "{worker.name}" zostal powiazany z wpisem z bazy.')

        result = self._order_store.save_new(order)
        if not result.ok:
            self._set_status(result.message_pl, ok=False)
            return
        messages.append(result.message_pl)
        messages.append(self._sync_calendar_events_for_order(order))

        self._reload_client_choices()
        self._reload_worker_choices()
        self._save_draft(show_status=False)
        
        # Run alarm checks for the new order
        try:
            alarm_service = AlarmService.instance()
            new_alarms = alarm_service.run_all_checks({"order_code": order.code})
            if new_alarms:
                messages.append(f"⚠ Wygenerowano {len(new_alarms)} alarm(ów)")
                for alarm in new_alarms[:3]:
                    messages.append(f"  - {alarm.title}")
        except Exception as e:
            print(f"Alarm check failed: {e}")
        
        self._set_status("\n".join(messages), ok=True)

    def _on_overwrite_all(self) -> None:
        is_valid, message = self._validate_required()
        if not is_valid:
            self._set_status(message, ok=False)
            return

        client = self._client_from_form()
        worker = self._worker_from_form()
        order = self._order_from_form()
        order = self._with_status_history(order, self._order_store.get(order.code))

        messages: list[str] = []

        if client.name:
            result = self._client_store.overwrite(client)
            if not result.ok:
                self._set_status(result.message_pl, ok=False)
                return
            messages.append(result.message_pl)

        if worker.name:
            result = self._worker_store.overwrite(worker)
            if not result.ok:
                self._set_status(result.message_pl, ok=False)
                return
            messages.append(result.message_pl)

        result = self._order_store.overwrite(order)
        if not result.ok:
            self._set_status(result.message_pl, ok=False)
            return
        messages.append(result.message_pl)
        messages.append(self._sync_calendar_events_for_order(order))

        self._reload_client_choices()
        self._reload_worker_choices()
        self._save_draft(show_status=False)
        
        # Run alarm checks for the order
        try:
            alarm_service = AlarmService.instance()
            new_alarms = alarm_service.run_all_checks({"order_code": order.code})
            if new_alarms:
                messages.append(f"⚠ Wygenerowano {len(new_alarms)} alarm(ów)")
                for alarm in new_alarms[:3]:
                    messages.append(f"  - {alarm.title}")
        except Exception as e:
            print(f"Alarm check failed: {e}")
        
        self._set_status("\n".join(messages), ok=True)
