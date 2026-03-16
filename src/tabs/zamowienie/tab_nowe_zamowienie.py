from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFrame,
    QFormLayout,
    QHeaderView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.app.app_settings import load_drawing_settings
from src.domain.assembly_resolution_service import resolve_assembly_items
from src.domain.client_models import ClientDef
from src.domain.order_models import OrderDef
from src.domain.worker_models import WorkerDef
from src.storage.assembly_store_json import AssemblyStoreJson
from src.storage.catalog_store_json import CatalogStoreJson
from src.storage.client_store_json import ClientStoreJson
from src.storage.order_draft_store_json import OrderDraftStoreJson
from src.storage.order_store_json import OrderStoreJson
from src.storage.wall_store_json import WallStoreJson
from src.storage.worker_store_json import WorkerStoreJson
from src.ui.collapsible_block import CollapsibleBlock


ORDER_STATUS_ITEMS: tuple[str, ...] = (
    "Nowe",
    "Wycena",
    "W produkcji",
    "Gotowe",
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


class TabNoweZamowienie(QWidget):
    sig_open_clients_base_requested = pyqtSignal()
    sig_open_orders_base_requested = pyqtSignal()
    sig_open_workers_base_requested = pyqtSignal()
    sig_open_sciana_requested = pyqtSignal(dict)
    sig_open_komplet_requested = pyqtSignal(dict)
    sig_open_existing_sciana_requested = pyqtSignal(str)

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
    ) -> None:
        super().__init__(parent)

        self._client_store = client_store if client_store is not None else ClientStoreJson()
        self._order_store = order_store if order_store is not None else OrderStoreJson()
        self._worker_store = worker_store if worker_store is not None else WorkerStoreJson()
        self._wall_store = wall_store if wall_store is not None else WallStoreJson()
        self._assembly_store = assembly_store if assembly_store is not None else AssemblyStoreJson()
        self._catalog = catalog if catalog is not None else CatalogStoreJson()
        self._draft_store = draft_store if draft_store is not None else OrderDraftStoreJson()
        self._is_restoring_draft = False
        self._architect_preview_pages: list[dict[str, object]] = []
        self._architect_preview_header = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        title = QLabel("NOWE ZAMOWIENIE")
        title.setStyleSheet("font-size: 22px; font-weight: 800; letter-spacing: 0.5px;")
        root.addWidget(title, 0, Qt.AlignmentFlag.AlignLeft)

        subtitle = QLabel(
            "Karta robocza dla calego projektu: klient, zamowienie, pracownik, sciany i koszty kompletow w jednym miejscu."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color:#555555;")
        root.addWidget(subtitle, 0, Qt.AlignmentFlag.AlignLeft)

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
        self.grp_walls = CollapsibleBlock("Sciany zamowienia", self)
        self.grp_summary = CollapsibleBlock("Podsumowanie zamowienia", self)

        body.addWidget(self.grp_client)
        body.addWidget(self.grp_order)
        body.addWidget(self.grp_worker)
        body.addWidget(self.grp_actions)
        body.addWidget(self.grp_architect)
        body.addWidget(self.grp_quote_items)
        body.addWidget(self.grp_material_choices)
        body.addWidget(self.grp_walls)
        body.addWidget(self.grp_summary)
        body.addStretch(1)

        for block in (
            self.grp_client,
            self.grp_order,
            self.grp_worker,
            self.grp_actions,
            self.grp_architect,
            self.grp_quote_items,
            self.grp_material_choices,
            self.grp_walls,
            self.grp_summary,
        ):
            block.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        self._build_client_group()
        self._build_order_group()
        self._build_worker_group()
        self._build_actions_group()
        self._build_architect_group()
        self._build_quote_items_group()
        self._build_material_choices_group()
        self._build_walls_group()
        self._build_summary_group()

        self.grp_worker.set_expanded(False)

        self.lab_status = QLabel("")
        self.lab_status.setWordWrap(True)
        self.lab_status.setStyleSheet("color:#666666;")
        page_root.addWidget(self.lab_status)

        page_root.addStretch(1)

        self.cb_client_name.currentTextChanged.connect(self._on_client_name_changed)
        self.cb_worker_name.currentTextChanged.connect(self._on_worker_name_changed)
        self.ed_order_code.textChanged.connect(self._refresh_summary)
        self.cb_order_status.currentTextChanged.connect(self._refresh_summary)
        self.ed_order_address.textChanged.connect(self._refresh_summary)
        self.ed_client_phone.textChanged.connect(self._refresh_summary)
        self.ed_client_email.textChanged.connect(self._refresh_summary)
        self.ed_client_city.textChanged.connect(self._refresh_summary)
        self.ed_worker_role.textChanged.connect(self._refresh_summary)
        self.ed_worker_phone.textChanged.connect(self._refresh_summary)
        self.ed_worker_email.textChanged.connect(self._refresh_summary)

        self.btn_pick_client.clicked.connect(self._on_pick_client_from_base)
        self.btn_save_client.clicked.connect(self._on_save_client_to_base)
        self.btn_pick_order.clicked.connect(self._on_pick_order_from_base)
        self.btn_save_order.clicked.connect(self._on_save_order_to_base)
        self.btn_pick_worker.clicked.connect(self._on_pick_worker_from_base)
        self.btn_save_worker.clicked.connect(self._on_save_worker_to_base)
        self.btn_open_clients_base.clicked.connect(self.sig_open_clients_base_requested.emit)
        self.btn_open_orders_base.clicked.connect(self.sig_open_orders_base_requested.emit)
        self.btn_open_workers_base.clicked.connect(self.sig_open_workers_base_requested.emit)
        self.btn_go_to_sciana.clicked.connect(self._on_go_to_sciana)
        self.btn_save_new.clicked.connect(self._on_save_new)
        self.btn_overwrite_all.clicked.connect(self._on_overwrite_all)
        self.btn_save_draft.clicked.connect(lambda: self._save_draft(show_status=True))
        self.btn_clear.clicked.connect(lambda: self.start_new_order(force_blank=True))
        self.btn_pick_architect_file.clicked.connect(self._on_pick_architect_file)
        self.btn_add_architect_attachment.clicked.connect(self._on_add_architect_attachment)
        self.btn_remove_architect_attachment.clicked.connect(self._on_remove_architect_attachment)
        self.tbl_architect_attachments.itemSelectionChanged.connect(
            self._on_architect_attachment_selection_changed
        )
        self.btn_add_quote_item.clicked.connect(self._on_add_quote_item)
        self.btn_remove_quote_item.clicked.connect(self._on_remove_quote_item)
        self.btn_quote_to_sciana.clicked.connect(self._on_open_quote_item_as_sciana)
        self.btn_quote_to_komplet.clicked.connect(self._on_open_quote_item_as_komplet)
        self.tbl_quote_items.itemSelectionChanged.connect(self._on_quote_item_selection_changed)
        self.btn_add_material_choice.clicked.connect(self._on_add_material_choice)
        self.btn_remove_material_choice.clicked.connect(self._on_remove_material_choice)
        self.tbl_material_choices.itemSelectionChanged.connect(self._on_material_choice_selection_changed)
        self.btn_new_wall.clicked.connect(self._on_go_to_sciana)
        self.btn_open_wall.clicked.connect(self._on_open_selected_wall)
        self.btn_refresh_walls.clicked.connect(self._refresh_order_walls_table)
        self.tbl_walls.itemSelectionChanged.connect(self._on_walls_selection_changed)
        self.tbl_walls.itemDoubleClicked.connect(lambda _item: self._on_open_selected_wall())

        self.start_new_order()

    def _build_client_group(self) -> None:
        layout = self.grp_client.content_layout()

        top = QHBoxLayout()
        self.cb_client_name = QComboBox(self.grp_client)
        self.cb_client_name.setEditable(True)
        self.btn_pick_client = QPushButton("Wybierz z bazy", self.grp_client)
        self.btn_save_client = QPushButton("Zapisz klienta", self.grp_client)
        self.btn_open_clients_base = QPushButton("Bazy", self.grp_client)
        self._make_compact_button(self.btn_pick_client, min_width=120, max_width=150)
        self._make_compact_button(self.btn_save_client, min_width=120, max_width=150)
        self._make_compact_button(self.btn_open_clients_base, min_width=70, max_width=90)
        top.addWidget(self.cb_client_name, 1)
        top.addWidget(self.btn_pick_client, 0)
        top.addWidget(self.btn_save_client, 0)
        top.addWidget(self.btn_open_clients_base, 0)
        layout.addLayout(top)

        form = QFormLayout()
        self.ed_client_phone = QLineEdit(self.grp_client)
        self.ed_client_email = QLineEdit(self.grp_client)
        self.ed_client_city = QLineEdit(self.grp_client)
        self.ed_client_notes = QTextEdit(self.grp_client)
        self.ed_client_notes.setMaximumHeight(90)
        form.addRow("Telefon", self.ed_client_phone)
        form.addRow("E-mail", self.ed_client_email)
        form.addRow("Miasto", self.ed_client_city)
        form.addRow("Notatki", self.ed_client_notes)
        layout.addLayout(form)

        note = QLabel(
            "Wybierz klienta z bazy albo wpisz nowego i zapisz go od razu tutaj."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#666666;")
        layout.addWidget(note)

    def _build_order_group(self) -> None:
        layout = self.grp_order.content_layout()

        top = QHBoxLayout()
        self.btn_pick_order = QPushButton("Wczytaj z bazy", self.grp_order)
        self.btn_save_order = QPushButton("Zapisz zamowienie", self.grp_order)
        self.btn_open_orders_base = QPushButton("Bazy", self.grp_order)
        self._make_compact_button(self.btn_pick_order, min_width=120, max_width=150)
        self._make_compact_button(self.btn_save_order, min_width=130, max_width=160)
        self._make_compact_button(self.btn_open_orders_base, min_width=70, max_width=90)
        top.addStretch(1)
        top.addWidget(self.btn_pick_order, 0)
        top.addWidget(self.btn_save_order, 0)
        top.addWidget(self.btn_open_orders_base, 0)
        layout.addLayout(top)

        form = QFormLayout()
        self.ed_order_code = QLineEdit(self.grp_order)
        self.cb_order_status = QComboBox(self.grp_order)
        for item in ORDER_STATUS_ITEMS:
            self.cb_order_status.addItem(item)
        self.ed_order_address = QLineEdit(self.grp_order)
        self.ed_order_notes = QTextEdit(self.grp_order)
        self.ed_order_notes.setMaximumHeight(110)
        form.addRow("Kod", self.ed_order_code)
        form.addRow("Status", self.cb_order_status)
        form.addRow("Adres realizacji", self.ed_order_address)
        form.addRow("Notatki", self.ed_order_notes)
        layout.addLayout(form)

    def _build_worker_group(self) -> None:
        layout = self.grp_worker.content_layout()

        top = QHBoxLayout()
        self.cb_worker_name = QComboBox(self.grp_worker)
        self.cb_worker_name.setEditable(True)
        self.btn_pick_worker = QPushButton("Wybierz z bazy", self.grp_worker)
        self.btn_save_worker = QPushButton("Zapisz pracownika", self.grp_worker)
        self.btn_open_workers_base = QPushButton("Bazy", self.grp_worker)
        self._make_compact_button(self.btn_pick_worker, min_width=120, max_width=150)
        self._make_compact_button(self.btn_save_worker, min_width=130, max_width=160)
        self._make_compact_button(self.btn_open_workers_base, min_width=70, max_width=90)
        top.addWidget(self.cb_worker_name, 1)
        top.addWidget(self.btn_pick_worker, 0)
        top.addWidget(self.btn_save_worker, 0)
        top.addWidget(self.btn_open_workers_base, 0)
        layout.addLayout(top)

        form = QFormLayout()
        self.ed_worker_role = QLineEdit(self.grp_worker)
        self.ed_worker_phone = QLineEdit(self.grp_worker)
        self.ed_worker_email = QLineEdit(self.grp_worker)
        self.ed_worker_notes = QTextEdit(self.grp_worker)
        self.ed_worker_notes.setMaximumHeight(90)
        form.addRow("Rola", self.ed_worker_role)
        form.addRow("Telefon", self.ed_worker_phone)
        form.addRow("E-mail", self.ed_worker_email)
        form.addRow("Notatki", self.ed_worker_notes)
        layout.addLayout(form)

        note = QLabel(
            "Wybierz pracownika z bazy albo dopisz go tutaj i zapisz od razu."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#666666;")
        layout.addWidget(note)

    def _build_actions_group(self) -> None:
        layout = self.grp_actions.content_layout()

        info = QLabel(
            "Zapisz nowe tworzy brakujace wpisy. Nadpisz wszystko aktualizuje dane wedlug biezacej karty."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color:#444444;")
        layout.addWidget(info)

        btns = QHBoxLayout()
        self.btn_save_draft = QPushButton("Zapisz roboczo", self.grp_actions)
        self.btn_save_new = QPushButton("Zapisz nowe", self.grp_actions)
        self.btn_overwrite_all = QPushButton("Nadpisz wszystko", self.grp_actions)
        self.btn_clear = QPushButton("Wyczysc karte", self.grp_actions)
        self.btn_go_to_sciana = QPushButton("Dalej: Sciana", self.grp_actions)
        for button in (
            self.btn_save_draft,
            self.btn_save_new,
            self.btn_overwrite_all,
            self.btn_clear,
            self.btn_go_to_sciana,
        ):
            self._make_compact_button(button, min_width=130, max_width=160)
            btns.addWidget(button, 0)
        btns.addStretch(1)
        layout.addLayout(btns)

    def _build_walls_group(self) -> None:
        layout = self.grp_walls.content_layout()

        note = QLabel(
            "Jedno zamowienie moze miec wiele scian. Tutaj widzisz wszystkie sciany powiazane z biezacym kodem."
        )
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

        note = QLabel(
            "Tutaj przypinasz PDF-y, zrzuty i referencje od architekta, z ktorych robimy szybka wycene i pozniejsza oferte."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#555555;")
        layout.addWidget(note)

        path_row = QHBoxLayout()
        self.ed_architect_file = QLineEdit(self.grp_architect)
        self.ed_architect_file.setPlaceholderText("Sciezka do PDF albo obrazu od architekta...")
        self.btn_pick_architect_file = QPushButton("Wybierz plik", self.grp_architect)
        self._make_compact_button(self.btn_pick_architect_file, min_width=110, max_width=130)
        path_row.addWidget(self.ed_architect_file, 1)
        path_row.addWidget(self.btn_pick_architect_file, 0)
        layout.addLayout(path_row)

        meta_row = QHBoxLayout()
        self.cb_architect_kind = QComboBox(self.grp_architect)
        self.cb_architect_kind.addItems(["PDF", "Obraz", "Referencja"])
        self.cb_architect_kind.setMaximumWidth(140)
        self.ed_architect_description = QLineEdit(self.grp_architect)
        self.ed_architect_description.setPlaceholderText("Opis, np. Lazienka master / widok front / wizualizacja...")
        meta_row.addWidget(self.cb_architect_kind, 0)
        meta_row.addWidget(self.ed_architect_description, 1)
        layout.addLayout(meta_row)

        btns = QHBoxLayout()
        self.btn_add_architect_attachment = QPushButton("Dodaj zalacznik", self.grp_architect)
        self.btn_remove_architect_attachment = QPushButton("Usun zaznaczony", self.grp_architect)
        self._make_compact_button(self.btn_add_architect_attachment, min_width=130, max_width=160)
        self._make_compact_button(self.btn_remove_architect_attachment, min_width=130, max_width=160)
        btns.addWidget(self.btn_add_architect_attachment, 0)
        btns.addWidget(self.btn_remove_architect_attachment, 0)
        btns.addStretch(1)
        layout.addLayout(btns)

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
        layout.addWidget(self.tbl_architect_attachments)

        preview_note = QLabel(
            "Po zaznaczeniu zalacznika PDF zobaczysz miniatury stron. To bedzie baza pod pozniejsze wycinanie fragmentow do Sciana, Komplet i oferty."
        )
        preview_note.setWordWrap(True)
        preview_note.setStyleSheet("color:#555555;")
        layout.addWidget(preview_note)

        self.lab_architect_preview_info = QLabel("Wybierz zalacznik, aby zobaczyc podglad.")
        self.lab_architect_preview_info.setWordWrap(True)
        self.lab_architect_preview_info.setStyleSheet("color:#444444; font-weight:600;")
        layout.addWidget(self.lab_architect_preview_info)

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

        self.lab_architect_page_preview = QLabel("Brak podgladu strony.")
        self.lab_architect_page_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lab_architect_page_preview.setMinimumSize(420, 280)
        self.lab_architect_page_preview.setStyleSheet(
            "border:1px solid #d7dbe2; background:#fafbfc; color:#666666; padding:8px;"
        )
        preview_row.addWidget(self.lab_architect_page_preview, 2)

        layout.addLayout(preview_row)
        self.lst_architect_pages.currentRowChanged.connect(self._on_architect_preview_page_changed)
        self._set_architect_attachments([])

    def _build_quote_items_group(self) -> None:
        layout = self.grp_quote_items.content_layout()

        note = QLabel(
            "Tutaj rozbijasz zamowienie na szybkie pozycje handlowe, np. kuchnia, szafa, RTV albo lazienka."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#555555;")
        layout.addWidget(note)

        row = QHBoxLayout()
        self.ed_quote_item_name = QLineEdit(self.grp_quote_items)
        self.ed_quote_item_name.setPlaceholderText("Nazwa pozycji, np. Kuchnia salon")
        self.cb_quote_item_kind = QComboBox(self.grp_quote_items)
        self.cb_quote_item_kind.addItems(list(QUOTE_ITEM_TYPES))
        self.cb_quote_item_kind.setMaximumWidth(150)
        row.addWidget(self.ed_quote_item_name, 1)
        row.addWidget(self.cb_quote_item_kind, 0)
        layout.addLayout(row)

        self.ed_quote_item_description = QLineEdit(self.grp_quote_items)
        self.ed_quote_item_description.setPlaceholderText(
            "Krotki opis, np. zabudowa wyspy + slupki albo szafa wnekowa przy wejsciu"
        )
        layout.addWidget(self.ed_quote_item_description)

        btns = QHBoxLayout()
        self.btn_add_quote_item = QPushButton("Dodaj pozycje", self.grp_quote_items)
        self.btn_remove_quote_item = QPushButton("Usun zaznaczona", self.grp_quote_items)
        self.btn_quote_to_sciana = QPushButton("Otworz jako Sciana", self.grp_quote_items)
        self.btn_quote_to_komplet = QPushButton("Otworz jako Komplet", self.grp_quote_items)
        self._make_compact_button(self.btn_add_quote_item, min_width=130, max_width=160)
        self._make_compact_button(self.btn_remove_quote_item, min_width=130, max_width=160)
        self._make_compact_button(self.btn_quote_to_sciana, min_width=150, max_width=180)
        self._make_compact_button(self.btn_quote_to_komplet, min_width=150, max_width=180)
        btns.addWidget(self.btn_add_quote_item, 0)
        btns.addWidget(self.btn_remove_quote_item, 0)
        btns.addWidget(self.btn_quote_to_sciana, 0)
        btns.addWidget(self.btn_quote_to_komplet, 0)
        btns.addStretch(1)
        layout.addLayout(btns)

        self.tbl_quote_items = QTableWidget(0, 3, self.grp_quote_items)
        self.tbl_quote_items.setHorizontalHeaderLabels(["Pozycja", "Typ", "Opis"])
        self.tbl_quote_items.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_quote_items.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_quote_items.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_quote_items.verticalHeader().setVisible(False)
        self.tbl_quote_items.horizontalHeader().setStretchLastSection(True)
        self.tbl_quote_items.setAlternatingRowColors(True)
        self.tbl_quote_items.setMinimumHeight(160)
        self.tbl_quote_items.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_quote_items.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.tbl_quote_items)
        self._set_quote_items([])

    def _build_material_choices_group(self) -> None:
        layout = self.grp_material_choices.content_layout()

        note = QLabel(
            "Tutaj zapisujesz pokazane probki i finalne wybory klienta: korpus, front, blat, farba, uchwyt albo inny material z kolorem i kodem."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#555555;")
        layout.addWidget(note)

        row_meta = QHBoxLayout()
        self.cb_material_scope = QComboBox(self.grp_material_choices)
        self.cb_material_scope.addItems(list(MATERIAL_SCOPE_ITEMS))
        self.cb_material_scope.setMaximumWidth(170)
        self.cb_material_choice_status = QComboBox(self.grp_material_choices)
        self.cb_material_choice_status.addItems(list(MATERIAL_CHOICE_STATUS_ITEMS))
        self.cb_material_choice_status.setMaximumWidth(180)
        row_meta.addWidget(self.cb_material_scope, 0)
        row_meta.addWidget(self.cb_material_choice_status, 0)
        row_meta.addStretch(1)
        layout.addLayout(row_meta)

        row_material = QHBoxLayout()
        self.ed_material_choice_material = QLineEdit(self.grp_material_choices)
        self.ed_material_choice_material.setPlaceholderText("Material / producent, np. Egger U702 albo lakier poliuretan")
        self.ed_material_choice_color = QLineEdit(self.grp_material_choices)
        self.ed_material_choice_color.setPlaceholderText("Kolor / dekor, np. Cashmere, dab naturalny")
        row_material.addWidget(self.ed_material_choice_material, 1)
        row_material.addWidget(self.ed_material_choice_color, 1)
        layout.addLayout(row_material)

        row_code = QHBoxLayout()
        self.ed_material_choice_code = QLineEdit(self.grp_material_choices)
        self.ed_material_choice_code.setPlaceholderText("Kod, np. U702 ST9 / RAL 9016")
        self.ed_material_choice_notes = QLineEdit(self.grp_material_choices)
        self.ed_material_choice_notes.setPlaceholderText("Uwagi, np. klient wybral probke nr 2")
        row_code.addWidget(self.ed_material_choice_code, 1)
        row_code.addWidget(self.ed_material_choice_notes, 1)
        layout.addLayout(row_code)

        btns = QHBoxLayout()
        self.btn_add_material_choice = QPushButton("Dodaj wpis", self.grp_material_choices)
        self.btn_remove_material_choice = QPushButton("Usun zaznaczony", self.grp_material_choices)
        self._make_compact_button(self.btn_add_material_choice, min_width=120, max_width=150)
        self._make_compact_button(self.btn_remove_material_choice, min_width=140, max_width=170)
        btns.addWidget(self.btn_add_material_choice, 0)
        btns.addWidget(self.btn_remove_material_choice, 0)
        btns.addStretch(1)
        layout.addLayout(btns)

        self.tbl_material_choices = QTableWidget(0, 6, self.grp_material_choices)
        self.tbl_material_choices.setHorizontalHeaderLabels(["Zakres", "Material", "Kolor", "Kod", "Status", "Uwagi"])
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
        layout.addWidget(self.tbl_material_choices)
        self._set_material_choices([])

    def _normalize_attachment(self, item: dict | None) -> dict[str, str] | None:
        if not isinstance(item, dict):
            return None
        path = str(item.get("path", "") or "").strip()
        kind = str(item.get("kind", "") or "").strip() or "PDF"
        description = str(item.get("description", "") or "").strip()
        if not path:
            return None
        return {
            "path": path,
            "kind": kind,
            "description": description,
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
            items = (
                QTableWidgetItem(file_name),
                QTableWidgetItem(str(attachment.get("kind", "") or "PDF")),
                QTableWidgetItem(str(attachment.get("description", "") or "")),
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
        if hasattr(self, "lab_architect_page_preview"):
            self.lab_architect_page_preview.clear()
            self.lab_architect_page_preview.setText(message)

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
            if hasattr(self, "lab_architect_page_preview") and not self._architect_preview_pages:
                self.lab_architect_page_preview.setText("Brak podgladu strony.")
            return

        page = self._architect_preview_pages[current_row]
        pixmap = page.get("full")
        label = str(page.get("label", "") or "")
        if isinstance(pixmap, QPixmap) and not pixmap.isNull():
            self.lab_architect_page_preview.setPixmap(pixmap)
            self.lab_architect_page_preview.setText("")
        else:
            self.lab_architect_page_preview.clear()
            self.lab_architect_page_preview.setText("Brak podgladu strony.")
        if self._architect_preview_header:
            self.lab_architect_preview_info.setText(f"{self._architect_preview_header} | {label}")

    def _normalize_quote_item(self, item: dict | None) -> dict[str, str] | None:
        if not isinstance(item, dict):
            return None
        name = str(item.get("name", "") or "").strip()
        kind = str(item.get("kind", "") or "").strip() or "Inne"
        description = str(item.get("description", "") or "").strip()
        if not name:
            return None
        return {
            "name": name,
            "kind": kind,
            "description": description,
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

    def _on_add_quote_item(self) -> None:
        entry = self._normalize_quote_item(
            {
                "name": self.ed_quote_item_name.text().strip(),
                "kind": self.cb_quote_item_kind.currentText().strip() or "Inne",
                "description": self.ed_quote_item_description.text().strip(),
            }
        )
        if entry is None:
            self._set_status("Podaj nazwe pozycji do wyceny.", ok=False)
            return
        self._quote_items.append(entry)
        self.ed_quote_item_name.clear()
        self.ed_quote_item_description.clear()
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

    def _normalize_material_choice(self, item: dict | None) -> dict[str, str] | None:
        if not isinstance(item, dict):
            return None
        scope = str(item.get("scope", "") or "").strip() or "Inne"
        material = str(item.get("material", "") or "").strip()
        color = str(item.get("color", "") or "").strip()
        code = str(item.get("code", "") or "").strip()
        status = str(item.get("status", "") or "").strip() or "Probka pokazana"
        notes = str(item.get("notes", "") or "").strip()
        if not any((scope, material, color, code, status, notes)):
            return None
        return {
            "scope": scope,
            "material": material,
            "color": color,
            "code": code,
            "status": status,
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

    def start_new_order(self, force_blank: bool = False) -> None:
        if not force_blank and self._load_draft(show_status=False):
            self.lab_status.clear()
            self.ed_order_code.setFocus()
            return

        if force_blank:
            self._draft_store.clear()

        self._reload_client_choices()
        self._reload_worker_choices()

        self.cb_client_name.setCurrentText("")
        self.ed_client_phone.clear()
        self.ed_client_email.clear()
        self.ed_client_city.clear()
        self.ed_client_notes.clear()

        self.ed_order_code.clear()
        self.cb_order_status.setCurrentIndex(0)
        self.ed_order_address.clear()
        self.ed_order_notes.clear()

        self.cb_worker_name.setCurrentText("")
        self.ed_worker_role.clear()
        self.ed_worker_phone.clear()
        self.ed_worker_email.clear()
        self.ed_worker_notes.clear()

        self.ed_architect_file.clear()
        self.cb_architect_kind.setCurrentIndex(0)
        self.ed_architect_description.clear()
        self._set_architect_attachments([])
        self.ed_quote_item_name.clear()
        self.cb_quote_item_kind.setCurrentIndex(0)
        self.ed_quote_item_description.clear()
        self._set_quote_items([])
        self.cb_material_scope.setCurrentIndex(0)
        self.cb_material_choice_status.setCurrentIndex(0)
        self.ed_material_choice_material.clear()
        self.ed_material_choice_color.clear()
        self.ed_material_choice_code.clear()
        self.ed_material_choice_notes.clear()
        self._set_material_choices([])

        self.lab_status.clear()
        self._refresh_summary()
        self.ed_order_code.setFocus()
        self._refresh_order_walls_table()

        if force_blank:
            self._set_status("Wyczyszczono karte i zapis roboczy.", ok=True)

    def start_new_order_from_context(self, context: dict | None = None) -> None:
        payload = context if isinstance(context, dict) else {}

        client_name = str(payload.get("client_name", "") or "").strip()
        order_name = str(payload.get("order_name", "") or "").strip()
        worker_name = str(payload.get("worker_name", "") or "").strip()
        order_status = str(payload.get("order_status", "") or "").strip()
        site_address = str(payload.get("site_address", "") or "").strip()

        self._reload_client_choices()
        self._reload_worker_choices()

        client = self._client_store.get(client_name) if client_name else None
        worker = self._worker_store.get(worker_name) if worker_name else None
        order = self._order_store.get(order_name) if order_name else None

        self._is_restoring_draft = True
        try:
            self.cb_client_name.setCurrentText(client_name)
            self.ed_client_phone.setText(str(getattr(client, "phone", "") or ""))
            self.ed_client_email.setText(str(getattr(client, "email", "") or ""))
            self.ed_client_city.setText(str(getattr(client, "city", "") or ""))
            self.ed_client_notes.setPlainText(str(getattr(client, "notes", "") or ""))

            self.ed_order_code.setText(order_name)
            effective_status = str(getattr(order, "status", "") or order_status or ORDER_STATUS_ITEMS[0])
            idx = self.cb_order_status.findText(effective_status)
            self.cb_order_status.setCurrentIndex(idx if idx >= 0 else 0)
            self.ed_order_address.setText(str(getattr(order, "site_address", "") or site_address))
            self.ed_order_notes.setPlainText(str(getattr(order, "notes", "") or ""))

            self.cb_worker_name.setCurrentText(worker_name)
            self.ed_worker_role.setText(str(getattr(worker, "role", "") or ""))
            self.ed_worker_phone.setText(str(getattr(worker, "phone", "") or ""))
            self.ed_worker_email.setText(str(getattr(worker, "email", "") or ""))
            self.ed_worker_notes.setPlainText(str(getattr(worker, "notes", "") or ""))
            self._set_architect_attachments(list(getattr(order, "attachments", []) or []))
            self._set_quote_items(list(getattr(order, "quote_items", []) or []))
            self._set_material_choices(list(getattr(order, "material_choices", []) or []))
        finally:
            self._is_restoring_draft = False

        self._refresh_summary()
        self._save_draft(show_status=False)
        self.ed_order_code.setFocus()
        self._set_status("Przywrocono dane zamowienia z kompletu.", ok=True)

    def _refresh_summary(self) -> None:
        client_name = self.cb_client_name.currentText().strip() or "-"
        order_code = self.ed_order_code.text().strip() or "-"
        worker_name = self.cb_worker_name.currentText().strip() or "-"
        status_name = self.cb_order_status.currentText().strip() or "-"
        wall_count = len(self._current_order_wall_names())
        assembly_count = len(self._current_order_assemblies())
        attachment_count = len(self._architect_attachments)
        quote_item_count = len(self._quote_items)
        material_choice_count = len(self._material_choices)
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
        self.lab_summary.setText(
            f"Klient: {client_name}\n"
            f"Zamowienie: {order_code}\n"
            f"Status: {status_name}\n"
            f"Pracownik: {worker_name}\n"
            f"Zalaczniki od architekta: {attachment_count}\n"
            f"Pozycje do wyceny: {quote_item_count}\n"
            f"Probki / materialy: {material_choice_count}\n"
            f"Finalne wybory: {len(final_material_choices)}"
        )
        if final_material_parts:
            self.lab_summary.setText(self.lab_summary.text() + "\nWybrane: " + "; ".join(final_material_parts))
        self._refresh_order_walls_table()
        self._refresh_order_cost_summary()
        self._autosave_draft()

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

            assembly_rows.append(
                {
                    "name": str(getattr(assembly, "name", "") or "-"),
                    "wall_name": str(getattr(assembly, "wall_name", "") or "-"),
                    "modules": int(assembly_modules),
                    "material_total": float(assembly_material_total),
                    "edgeband_total": float(assembly_edgeband_total),
                    "hardware_total": float(assembly_hardware_total),
                    "grand_total": float(
                        assembly_material_total + assembly_edgeband_total + assembly_hardware_total
                    ),
                }
            )

        grand_total = material_total + edgeband_total + hardware_total
        if hasattr(self, "lab_metric_total"):
            self.lab_metric_total.setText(f"{grand_total:.2f} zl")

        if assemblies:
            assembly_names = ", ".join(str(getattr(item, "name", "") or "-") for item in assemblies[:4])
            if len(assemblies) > 4:
                assembly_names += ", ..."
            self.lab_cost_summary.setText(
                f"Sciany: {wall_count}\n"
                f"Komplety: {len(assemblies)}\n"
                f"Moduly w kompletach: {modules_total}\n"
                f"Materialy: {material_total:.2f} zl\n"
                f"Okleina: {edgeband_total:.2f} zl\n"
                f"Okucia: {hardware_total:.2f} zl\n"
                f"RAZEM: {grand_total:.2f} zl\n"
                f"Komplety w zamowieniu: {assembly_names}"
            )
        else:
            self.lab_cost_summary.setText(
                f"Sciany: {wall_count}\n"
                "Komplety: 0\n"
                "Materialy: 0.00 zl\n"
                "Okleina: 0.00 zl\n"
                "Okucia: 0.00 zl\n"
                "RAZEM: 0.00 zl\n"
                "Brak zapisanych kompletow dla tego zamowienia."
            )

        assembly_rows = sorted(
            assembly_rows,
            key=lambda item: (
                -float(item["grand_total"]),
                str(item["name"]).lower(),
            ),
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
            key=lambda item: (
                -float(item["cost"]),
                str(item["label"]).lower(),
            ),
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
            "client_phone": str(self.ed_client_phone.text().strip()),
            "client_email": str(self.ed_client_email.text().strip()),
            "client_city": str(self.ed_client_city.text().strip()),
            "client_notes": str(self.ed_client_notes.toPlainText().strip()),
            "order_code": str(self.ed_order_code.text().strip()),
            "order_status": str(self.cb_order_status.currentText().strip()),
            "order_address": str(self.ed_order_address.text().strip()),
            "order_notes": str(self.ed_order_notes.toPlainText().strip()),
            "worker_name": str(self.cb_worker_name.currentText().strip()),
            "worker_role": str(self.ed_worker_role.text().strip()),
            "worker_phone": str(self.ed_worker_phone.text().strip()),
            "worker_email": str(self.ed_worker_email.text().strip()),
            "worker_notes": str(self.ed_worker_notes.toPlainText().strip()),
            "architect_attachments": [dict(item) for item in self._architect_attachments],
            "quote_items": [dict(item) for item in self._quote_items],
            "material_choices": [dict(item) for item in self._material_choices],
        }

    def _has_meaningful_draft(self, payload: dict[str, object]) -> bool:
        for value in payload.values():
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
            self.cb_client_name.setCurrentText(str(payload.get("client_name", "") or ""))
            self.ed_client_phone.setText(str(payload.get("client_phone", "") or ""))
            self.ed_client_email.setText(str(payload.get("client_email", "") or ""))
            self.ed_client_city.setText(str(payload.get("client_city", "") or ""))
            self.ed_client_notes.setPlainText(str(payload.get("client_notes", "") or ""))

            self.ed_order_code.setText(str(payload.get("order_code", "") or ""))
            order_status = str(payload.get("order_status", "") or "")
            idx = self.cb_order_status.findText(order_status)
            self.cb_order_status.setCurrentIndex(idx if idx >= 0 else 0)
            self.ed_order_address.setText(str(payload.get("order_address", "") or ""))
            self.ed_order_notes.setPlainText(str(payload.get("order_notes", "") or ""))

            self.cb_worker_name.setCurrentText(str(payload.get("worker_name", "") or ""))
            self.ed_worker_role.setText(str(payload.get("worker_role", "") or ""))
            self.ed_worker_phone.setText(str(payload.get("worker_phone", "") or ""))
            self.ed_worker_email.setText(str(payload.get("worker_email", "") or ""))
            self.ed_worker_notes.setPlainText(str(payload.get("worker_notes", "") or ""))
            self._set_architect_attachments(list(payload.get("architect_attachments", []) or []))
            self._set_quote_items(list(payload.get("quote_items", []) or []))
            self._set_material_choices(list(payload.get("material_choices", []) or []))
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
        current = self.cb_worker_name.currentText().strip()
        self.cb_worker_name.blockSignals(True)
        try:
            self.cb_worker_name.clear()
            self.cb_worker_name.addItem("")
            for name in self._worker_store.list_names():
                self.cb_worker_name.addItem(name)
            self.cb_worker_name.setCurrentText(current)
        finally:
            self.cb_worker_name.blockSignals(False)

    def _on_client_name_changed(self, text: str) -> None:
        client = self._client_store.get(str(text or "").strip())
        if client is None:
            self._refresh_summary()
            return
        self.ed_client_phone.setText(client.phone)
        self.ed_client_email.setText(client.email)
        self.ed_client_city.setText(client.city)
        self.ed_client_notes.setPlainText(client.notes)
        self._refresh_summary()

    def _on_worker_name_changed(self, text: str) -> None:
        worker = self._worker_store.get(str(text or "").strip())
        if worker is None:
            self._refresh_summary()
            return
        self.ed_worker_role.setText(worker.role)
        self.ed_worker_phone.setText(worker.phone)
        self.ed_worker_email.setText(worker.email)
        self.ed_worker_notes.setPlainText(worker.notes)
        self._refresh_summary()

    def _client_from_form(self) -> ClientDef:
        return ClientDef(
            name=str(self.cb_client_name.currentText().strip()),
            phone=str(self.ed_client_phone.text().strip()),
            email=str(self.ed_client_email.text().strip()),
            city=str(self.ed_client_city.text().strip()),
            notes=str(self.ed_client_notes.toPlainText().strip()),
        )

    def _worker_from_form(self) -> WorkerDef:
        return WorkerDef(
            name=str(self.cb_worker_name.currentText().strip()),
            role=str(self.ed_worker_role.text().strip()),
            phone=str(self.ed_worker_phone.text().strip()),
            email=str(self.ed_worker_email.text().strip()),
            notes=str(self.ed_worker_notes.toPlainText().strip()),
        )

    def _order_from_form(self) -> OrderDef:
        return OrderDef(
            code=str(self.ed_order_code.text().strip()),
            client_name=str(self.cb_client_name.currentText().strip()),
            worker_name=str(self.cb_worker_name.currentText().strip()),
            status=str(self.cb_order_status.currentText().strip() or "Nowe"),
            site_address=str(self.ed_order_address.text().strip()),
            notes=str(self.ed_order_notes.toPlainText().strip()),
            attachments=[dict(item) for item in self._architect_attachments],
            quote_items=[dict(item) for item in self._quote_items],
            material_choices=[dict(item) for item in self._material_choices],
        )

    def current_order_context(self) -> dict[str, str]:
        order = self._order_from_form()
        return {
            "client_name": str(order.client_name or "").strip(),
            "order_name": str(order.code or "").strip(),
            "worker_name": str(order.worker_name or "").strip(),
            "order_status": str(order.status or "").strip(),
            "site_address": str(order.site_address or "").strip(),
        }

    def _set_status(self, message: str, ok: bool) -> None:
        color = "#2d6a4f" if ok else "#b42318"
        self.lab_status.setStyleSheet(f"color:{color};")
        self.lab_status.setText(str(message or ""))
        self._refresh_summary()

    def _save_client(self, overwrite: bool) -> tuple[bool, str]:
        client = self._client_from_form()
        if not client.name:
            return False, "Podaj nazwe klienta."
        if overwrite:
            result = self._client_store.overwrite(client)
        else:
            existing = self._client_store.get(client.name)
            result = self._client_store.overwrite(client) if existing is not None else self._client_store.save_new(client)
        self._reload_client_choices()
        self.cb_client_name.setCurrentText(client.name)
        return result.ok, result.message_pl

    def _save_worker(self, overwrite: bool) -> tuple[bool, str]:
        worker = self._worker_from_form()
        if not worker.name:
            return False, "Podaj nazwe pracownika."
        if overwrite:
            result = self._worker_store.overwrite(worker)
        else:
            existing = self._worker_store.get(worker.name)
            result = self._worker_store.overwrite(worker) if existing is not None else self._worker_store.save_new(worker)
        self._reload_worker_choices()
        self.cb_worker_name.setCurrentText(worker.name)
        return result.ok, result.message_pl

    def _save_order(self, overwrite: bool) -> tuple[bool, str]:
        order = self._order_from_form()
        if not order.code:
            return False, "Podaj kod zamowienia."
        if not order.client_name:
            return False, "Wybierz klienta albo wpisz nowego klienta."
        if overwrite:
            result = self._order_store.overwrite(order)
        else:
            existing = self._order_store.get(order.code)
            result = self._order_store.overwrite(order) if existing is not None else self._order_store.save_new(order)
        return result.ok, result.message_pl

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
        worker_name = self.cb_worker_name.currentText().strip()
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

    def _on_pick_order_from_base(self) -> None:
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
        self.ed_order_code.setText(order.code)
        self.cb_client_name.setCurrentText(order.client_name)
        self.cb_worker_name.setCurrentText(order.worker_name)
        idx = self.cb_order_status.findText(order.status)
        self.cb_order_status.setCurrentIndex(idx if idx >= 0 else 0)
        self.ed_order_address.setText(order.site_address)
        self.ed_order_notes.setPlainText(order.notes)
        self._set_architect_attachments(list(getattr(order, "attachments", []) or []))
        self._set_quote_items(list(getattr(order, "quote_items", []) or []))
        self._set_material_choices(list(getattr(order, "material_choices", []) or []))
        self._set_status(f'Wczytano zamowienie "{order.code}".', ok=True)

    def _ensure_context_saved_for_next_step(self) -> tuple[bool, str]:
        client_name = self.cb_client_name.currentText().strip()
        worker_name = self.cb_worker_name.currentText().strip()
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
            return False, "Wybierz klienta albo wpisz nowego klienta."
        return True, ""

    def _on_save_new(self) -> None:
        is_valid, message = self._validate_required()
        if not is_valid:
            self._set_status(message, ok=False)
            return

        client = self._client_from_form()
        worker = self._worker_from_form()
        order = self._order_from_form()

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

        self._reload_client_choices()
        self._reload_worker_choices()
        self._save_draft(show_status=False)
        self._set_status("\n".join(messages), ok=True)

    def _on_overwrite_all(self) -> None:
        is_valid, message = self._validate_required()
        if not is_valid:
            self._set_status(message, ok=False)
            return

        client = self._client_from_form()
        worker = self._worker_from_form()
        order = self._order_from_form()

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

        self._reload_client_choices()
        self._reload_worker_choices()
        self._save_draft(show_status=False)
        self._set_status("\n".join(messages), ok=True)
