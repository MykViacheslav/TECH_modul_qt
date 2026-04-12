from __future__ import annotations

import re
from datetime import datetime

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QFormLayout,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.app.app_settings import load_table_column_widths, save_table_column_widths
from src.app.app_settings import load_ui_theme_settings
from src.domain.client_models import ClientDef
from src.domain.assembly_models import FurnitureAssemblyDef
from src.domain.order_models import OrderDef
from src.domain.worker_models import WorkerDef
from src.storage.assembly_store_json import AssemblyStoreJson
from src.storage.catalog_store_json import CatalogStoreJson
from src.storage.client_store_json import ClientStoreJson
from src.storage.module_store_json import ModuleStoreJson
from src.storage.order_store_json import OrderStoreJson
from src.storage.wall_store_json import WallStoreJson
from src.storage.worker_store_json import WorkerStoreJson
from src.domain.module_base_group import module_base_group_label_pl
from src.tabs.modul.dialog_catalog_editor import CatalogEditorDialog


ORDER_STATUS_ITEMS: tuple[str, ...] = (
    "Nowe",
    "Wycena",
    "Wycena szybka",
    "Wycena gotowa",
    "Oczekiwanie na klienta",
    "Wstrzymane",
    "Zaakceptowane",
    "Zakup materialow",
    "W produkcji",
    "Lakiernia",
    "Montaz",
    "Poprawki",
    "Gotowe",
    "Zamkniete",
    "Zakonczone",
    "Anulowane",
)

ORDER_STATUS_FILTER_ALL = "Wszystkie"
ORDER_WORKER_FILTER_ALL = "Wszyscy"

_ORDER_CLOSED_STATUSES = {"Zakonczone", "Anulowane"}


class TabBazy(QWidget):
    sig_open_module_requested = pyqtSignal(str)
    sig_open_wall_requested = pyqtSignal(str)
    sig_open_assembly_requested = pyqtSignal(str)
    sig_new_module_requested = pyqtSignal()
    sig_new_wall_requested = pyqtSignal()
    sig_new_assembly_requested = pyqtSignal()

    def __init__(
        self,
        parent: QWidget | None = None,
        module_store: ModuleStoreJson | None = None,
        wall_store: WallStoreJson | None = None,
        assembly_store: AssemblyStoreJson | None = None,
        client_store: ClientStoreJson | None = None,
        order_store: OrderStoreJson | None = None,
        worker_store: WorkerStoreJson | None = None,
        catalog: CatalogStoreJson | None = None,
    ) -> None:
        super().__init__(parent)
        theme = load_ui_theme_settings()
        self._is_tech = str(theme.motif or "").strip().lower() == "tech" and str(theme.mode or "").strip().lower() == "night"
        self._colors = {
            "title": "#e8efff" if self._is_tech else "#1f2937",
            "section_bg": "#111b30" if self._is_tech else "#fffdf8",
            "section_border": "#2a4368" if self._is_tech else "#e6d9c8",
            "section_head": "#dbe9ff" if self._is_tech else "#2f241b",
            "section_sub": "#9bb0cd" if self._is_tech else "#6b5b4b",
            "stat_bg": "#15253f" if self._is_tech else "#f7efe2",
            "stat_border": "#2e4b78" if self._is_tech else "#e2d2bc",
            "stat_title": "#9cb7dc" if self._is_tech else "#80684f",
            "stat_value": "#f2f7ff" if self._is_tech else "#2f241b",
            "muted": "#9bb0cd" if self._is_tech else "#666666",
        }
        self._status_style = f"color:{self._colors['muted']};"

        self._module_store = module_store if module_store is not None else ModuleStoreJson()
        self._wall_store = wall_store if wall_store is not None else WallStoreJson()
        self._assembly_store = assembly_store if assembly_store is not None else AssemblyStoreJson()
        self._client_store = client_store if client_store is not None else ClientStoreJson()
        self._order_store = order_store if order_store is not None else OrderStoreJson()
        self._worker_store = worker_store if worker_store is not None else WorkerStoreJson()
        self._catalog = catalog if catalog is not None else CatalogStoreJson()
        self._is_syncing_client_ui = False
        self._is_syncing_order_ui = False
        self._is_syncing_worker_ui = False

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        title = QLabel("BAZY")
        title.setStyleSheet(f"font-weight:700; color:{self._colors['title']};")
        root.addWidget(title)

        self.tabs = QTabWidget(self)
        root.addWidget(self.tabs, 1)

        self.tabs.addTab(self._build_modules_tab(), "Moduły")
        self.tabs.addTab(self._build_walls_tab(), "Ściany")
        self.tabs.addTab(self._build_assemblies_tab(), "Komplety")
        self.tabs.addTab(self._build_clients_tab(), "Klienci")
        self.tabs.addTab(self._build_orders_tab(), "Zamowienia")
        self.tabs.addTab(self._build_materials_tab(), "Materialy")
        self.tabs.addTab(self._build_workers_tab(), "Pracownicy")

        self._reload_all()

    def _open_subtab_by_title(self, title: str) -> bool:
        wanted = str(title or "").strip()
        if not wanted:
            return False
        for index in range(self.tabs.count()):
            if self.tabs.tabText(index) == wanted:
                self.tabs.setCurrentIndex(index)
                return True
        return False

    def open_clients_tab(self, clear_form: bool = False) -> bool:
        opened = self._open_subtab_by_title("Klienci")
        if opened:
            self._reload_clients_tab()
            if clear_form:
                self._clear_client_form()
                self.ed_client_id.setFocus()
        return opened

    def open_orders_tab(self, clear_form: bool = False, focus_code: str = "") -> bool:
        opened = self._open_subtab_by_title("Zamowienia")
        if opened:
            if focus_code:
                self._clear_order_filters(reload=False)
            self._reload_orders_tab()
            if clear_form:
                self._clear_order_form()
                self.ed_order_code.setFocus()
            elif focus_code:
                self._select_order_by_code(focus_code)
        return opened

    def open_workers_tab(self, clear_form: bool = False) -> bool:
        opened = self._open_subtab_by_title("Pracownicy")
        if opened:
            self._reload_workers_tab()
            if clear_form:
                self._clear_worker_form()
                self.ed_worker_name.setFocus()
        return opened

    def _make_compact_button(self, button: QPushButton, min_width: int = 110, max_width: int = 140) -> None:
        button.setMinimumWidth(min_width)
        button.setMaximumWidth(max_width)
        button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def _make_section_box(self, title: str, subtitle: str = "") -> tuple[QFrame, QVBoxLayout]:
        box = QFrame(self)
        box.setStyleSheet(
            "QFrame {"
            f" background:{self._colors['section_bg']};"
            f" border:1px solid {self._colors['section_border']};"
            " border-radius:12px;"
            "}"
        )
        layout = QVBoxLayout(box)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        head = QLabel(title, box)
        head.setStyleSheet(f"font-size:16px; font-weight:800; color:{self._colors['section_head']};")
        layout.addWidget(head)
        if subtitle:
            sub = QLabel(subtitle, box)
            sub.setWordWrap(True)
            sub.setStyleSheet(f"color:{self._colors['section_sub']};")
            layout.addWidget(sub)
        return box, layout

    def _make_stat_card(self, title: str) -> tuple[QFrame, QLabel]:
        box = QFrame(self)
        box.setStyleSheet(
            "QFrame {"
            f" background:{self._colors['stat_bg']};"
            f" border:1px solid {self._colors['stat_border']};"
            " border-radius:12px;"
            "}"
        )
        layout = QVBoxLayout(box)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)
        lab_title = QLabel(title, box)
        lab_title.setStyleSheet(f"font-size:11px; font-weight:700; color:{self._colors['stat_title']};")
        lab_value = QLabel("-", box)
        lab_value.setStyleSheet(f"font-size:20px; font-weight:900; color:{self._colors['stat_value']};")
        layout.addWidget(lab_title)
        layout.addWidget(lab_value)
        return box, lab_value

    def _configure_content_width_table(self, table: QTableWidget, table_key: str) -> None:
        header = table.horizontalHeader()
        header.setStretchLastSection(False)
        for col in range(table.columnCount()):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
        table.setProperty("column_widths_key", table_key)
        header.sectionResized.connect(
            lambda _idx, _old, _new, t=table: self._save_table_column_widths_for(t)
        )
        if not self._restore_table_column_widths_for(table):
            table.resizeColumnsToContents()
            self._save_table_column_widths_for(table)

    def _resize_table_to_contents(self, table: QTableWidget) -> None:
        try:
            if not self._restore_table_column_widths_for(table):
                table.resizeColumnsToContents()
            table.resizeRowsToContents()
        except Exception:
            pass

    def _restore_table_column_widths_for(self, table: QTableWidget) -> bool:
        key = str(table.property("column_widths_key") or "").strip()
        if not key:
            return False
        widths = load_table_column_widths(key)
        if len(widths) != table.columnCount():
            return False
        for idx, width in enumerate(widths):
            table.setColumnWidth(idx, max(40, int(width)))
        return True

    def _save_table_column_widths_for(self, table: QTableWidget) -> None:
        key = str(table.property("column_widths_key") or "").strip()
        if not key:
            return
        widths = [int(table.columnWidth(idx)) for idx in range(table.columnCount())]
        save_table_column_widths(key, widths)

    def _build_modules_tab(self) -> QWidget:
        panel = QWidget(self)
        layout = QVBoxLayout(panel)

        row = QHBoxLayout()
        self.btn_new_module = QPushButton("Nowy w Modul")
        self.btn_reload_modules = QPushButton("Odswiez")
        row.addWidget(self.btn_new_module, 0)
        row.addStretch(1)
        row.addWidget(self.btn_reload_modules, 0)
        layout.addLayout(row)

        self.tree_modules = QTreeWidget(panel)
        self.tree_modules.setHeaderHidden(True)
        layout.addWidget(self.tree_modules, 1)

        details_box, details_layout = self._make_section_box(
            "Wybrany modul",
            "Szybki opis zaznaczonego modulu: rozmiar, typ, front i wnetrze.",
        )
        details_grid = QGridLayout()
        details_grid.setHorizontalSpacing(12)
        details_grid.setVerticalSpacing(6)
        details_grid.addWidget(QLabel("Nazwa"), 0, 0)
        self.lab_module_detail_name = QLabel("-")
        details_grid.addWidget(self.lab_module_detail_name, 0, 1)
        details_grid.addWidget(QLabel("Grupa"), 1, 0)
        self.lab_module_detail_group = QLabel("-")
        details_grid.addWidget(self.lab_module_detail_group, 1, 1)
        details_grid.addWidget(QLabel("Wymiary"), 2, 0)
        self.lab_module_detail_dims = QLabel("-")
        details_grid.addWidget(self.lab_module_detail_dims, 2, 1)
        details_grid.addWidget(QLabel("Typ"), 3, 0)
        self.lab_module_detail_kind = QLabel("-")
        details_grid.addWidget(self.lab_module_detail_kind, 3, 1)
        details_grid.addWidget(QLabel("Front"), 4, 0)
        self.lab_module_detail_front = QLabel("-")
        details_grid.addWidget(self.lab_module_detail_front, 4, 1)
        details_grid.addWidget(QLabel("Srodek"), 5, 0)
        self.lab_module_detail_inside = QLabel("-")
        details_grid.addWidget(self.lab_module_detail_inside, 5, 1)
        details_grid.addWidget(QLabel("Profil"), 6, 0)
        self.lab_module_detail_profile = QLabel("-")
        details_grid.addWidget(self.lab_module_detail_profile, 6, 1)
        details_layout.addLayout(details_grid)
        layout.addWidget(details_box, 0)

        manage_row = QHBoxLayout()
        self.cb_module_target_group = QComboBox(panel)
        self.btn_move_module = QPushButton("Przenies do grupy")
        self.btn_add_module_group = QPushButton("Dodaj grupe")
        self.btn_duplicate_module = QPushButton("Duplikuj")
        self.btn_rename_module = QPushButton("Zmien nazwe")
        self.btn_open_module = QPushButton("Otworz w Modul")
        self.btn_delete_module = QPushButton("Usun z bazy")
        for button in (
            self.btn_new_module,
            self.btn_reload_modules,
            self.btn_move_module,
            self.btn_add_module_group,
            self.btn_duplicate_module,
            self.btn_rename_module,
            self.btn_open_module,
            self.btn_delete_module,
        ):
            self._make_compact_button(button)
        self.cb_module_target_group.setEnabled(False)
        self.btn_move_module.setEnabled(False)
        self.btn_add_module_group.setEnabled(False)
        self.btn_duplicate_module.setEnabled(False)
        self.btn_rename_module.setEnabled(False)
        self.btn_open_module.setEnabled(False)
        self.btn_delete_module.setEnabled(False)
        manage_row.addWidget(self.cb_module_target_group, 1)
        manage_row.addWidget(self.btn_move_module, 0)
        manage_row.addWidget(self.btn_add_module_group, 0)
        manage_row.addWidget(self.btn_duplicate_module, 0)
        manage_row.addWidget(self.btn_rename_module, 0)
        manage_row.addWidget(self.btn_open_module, 0)
        manage_row.addWidget(self.btn_delete_module, 0)
        layout.addLayout(manage_row)

        self.lab_modules_info = QLabel("-")
        self.lab_modules_info.setWordWrap(True)
        layout.addWidget(self.lab_modules_info)

        self.lab_modules_status = QLabel("")
        self.lab_modules_status.setWordWrap(True)
        self.lab_modules_status.setStyleSheet(self._status_style)
        layout.addWidget(self.lab_modules_status)

        self.btn_new_module.clicked.connect(self._on_new_module)
        self.btn_reload_modules.clicked.connect(self._reload_modules_tab)
        self.btn_move_module.clicked.connect(self._on_move_selected_module)
        self.btn_add_module_group.clicked.connect(self._on_add_custom_module_group)
        self.btn_duplicate_module.clicked.connect(self._on_duplicate_selected_module)
        self.btn_rename_module.clicked.connect(self._on_rename_selected_module)
        self.btn_open_module.clicked.connect(self._on_open_selected_module)
        self.btn_delete_module.clicked.connect(self._on_delete_selected_module)
        self.tree_modules.itemSelectionChanged.connect(self._on_module_selection_changed)
        return panel

    def _build_walls_tab(self) -> QWidget:
        panel = QWidget(self)
        layout = QVBoxLayout(panel)

        row = QHBoxLayout()
        self.btn_new_wall = QPushButton("Nowa w Ściana")
        self.btn_reload_walls = QPushButton("Odswiez")
        row.addWidget(self.btn_new_wall, 0)
        row.addStretch(1)
        row.addWidget(self.btn_reload_walls, 0)
        layout.addLayout(row)

        self.tbl_walls = QTableWidget(0, 6, panel)
        self.tbl_walls.setHorizontalHeaderLabels(["Nazwa", "Klient", "Zamówienie", "Typ", "Przeszkody", "Zdjęcia"])
        self.tbl_walls.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_walls.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_walls.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_walls.verticalHeader().setVisible(False)
        self._configure_content_width_table(self.tbl_walls, "bazy_walls")
        layout.addWidget(self.tbl_walls, 1)

        btns = QHBoxLayout()
        self.btn_duplicate_wall = QPushButton("Duplikuj")
        self.btn_rename_wall = QPushButton("Zmien nazwe")
        self.btn_open_wall = QPushButton("Otwórz w Ściana")
        self.btn_delete_wall = QPushButton("Usun z bazy")
        for button in (
            self.btn_new_wall,
            self.btn_reload_walls,
            self.btn_duplicate_wall,
            self.btn_rename_wall,
            self.btn_open_wall,
            self.btn_delete_wall,
        ):
            self._make_compact_button(button)
        self.btn_duplicate_wall.setEnabled(False)
        self.btn_rename_wall.setEnabled(False)
        self.btn_open_wall.setEnabled(False)
        self.btn_delete_wall.setEnabled(False)
        btns.addWidget(self.btn_duplicate_wall)
        btns.addWidget(self.btn_rename_wall)
        btns.addWidget(self.btn_open_wall)
        btns.addWidget(self.btn_delete_wall)
        btns.addStretch(1)
        layout.addLayout(btns)

        self.lab_walls_info = QLabel("-")
        self.lab_walls_info.setWordWrap(True)
        layout.addWidget(self.lab_walls_info)

        self.lab_walls_status = QLabel("")
        self.lab_walls_status.setWordWrap(True)
        self.lab_walls_status.setStyleSheet(self._status_style)
        layout.addWidget(self.lab_walls_status)

        self.btn_new_wall.clicked.connect(self._on_new_wall)
        self.btn_reload_walls.clicked.connect(self._reload_walls_tab)
        self.btn_duplicate_wall.clicked.connect(self._on_duplicate_selected_wall)
        self.btn_rename_wall.clicked.connect(self._on_rename_selected_wall)
        self.btn_open_wall.clicked.connect(self._on_open_selected_wall)
        self.btn_delete_wall.clicked.connect(self._on_delete_selected_wall)
        self.tbl_walls.itemSelectionChanged.connect(self._on_wall_selection_changed)
        return panel

    def _build_assemblies_tab(self) -> QWidget:
        panel = QWidget(self)
        layout = QVBoxLayout(panel)

        row = QHBoxLayout()
        self.btn_new_assembly = QPushButton("Nowy w Komplet")
        self.btn_reload_assemblies = QPushButton("Odswiez")
        row.addWidget(self.btn_new_assembly, 0)
        row.addStretch(1)
        row.addWidget(self.btn_reload_assemblies, 0)
        layout.addLayout(row)

        self.tbl_assemblies = QTableWidget(0, 6, panel)
        self.tbl_assemblies.setHorizontalHeaderLabels(
            ["Nazwa", "Klient", "Zamówienie", "Pracownik", "Ściana", "Moduły"]
        )
        self.tbl_assemblies.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_assemblies.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_assemblies.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_assemblies.verticalHeader().setVisible(False)
        self._configure_content_width_table(self.tbl_assemblies, "bazy_assemblies")
        layout.addWidget(self.tbl_assemblies, 1)

        btns = QHBoxLayout()
        self.btn_duplicate_assembly = QPushButton("Duplikuj")
        self.btn_rename_assembly = QPushButton("Zmien nazwe")
        self.btn_open_assembly = QPushButton("Otworz w Komplet")
        self.btn_delete_assembly = QPushButton("Usun z bazy")
        for button in (
            self.btn_new_assembly,
            self.btn_reload_assemblies,
            self.btn_duplicate_assembly,
            self.btn_rename_assembly,
            self.btn_open_assembly,
            self.btn_delete_assembly,
        ):
            self._make_compact_button(button)
        self.btn_duplicate_assembly.setEnabled(False)
        self.btn_rename_assembly.setEnabled(False)
        self.btn_open_assembly.setEnabled(False)
        self.btn_delete_assembly.setEnabled(False)
        btns.addWidget(self.btn_duplicate_assembly)
        btns.addWidget(self.btn_rename_assembly)
        btns.addWidget(self.btn_open_assembly)
        btns.addWidget(self.btn_delete_assembly)
        btns.addStretch(1)
        layout.addLayout(btns)

        self.lab_assemblies_info = QLabel("-")
        self.lab_assemblies_info.setWordWrap(True)
        self.lab_assemblies_info.setStyleSheet(self._status_style)
        layout.addWidget(self.lab_assemblies_info)

        self.lab_assemblies_status = QLabel("")
        self.lab_assemblies_status.setWordWrap(True)
        self.lab_assemblies_status.setStyleSheet(self._status_style)
        layout.addWidget(self.lab_assemblies_status)

        self.btn_new_assembly.clicked.connect(self._on_new_assembly)
        self.btn_reload_assemblies.clicked.connect(self._reload_assemblies_tab)
        self.btn_duplicate_assembly.clicked.connect(self._on_duplicate_selected_assembly)
        self.btn_rename_assembly.clicked.connect(self._on_rename_selected_assembly)
        self.btn_open_assembly.clicked.connect(self._on_open_selected_assembly)
        self.btn_delete_assembly.clicked.connect(self._on_delete_selected_assembly)
        self.tbl_assemblies.itemSelectionChanged.connect(self._on_assembly_selection_changed)

        return panel

    def _build_clients_tab(self) -> QWidget:
        panel = QWidget(self)
        layout = QVBoxLayout(panel)

        self.ed_client_name = QLineEdit()
        self.ed_client_name.setVisible(False)

        compact = QHBoxLayout()
        compact.setSpacing(8)
        self.ed_client_id = QLineEdit()
        self.ed_client_id.setPlaceholderText("ID")
        self.ed_client_id.setMaximumWidth(120)
        self.ed_client_first_name = QLineEdit()
        self.ed_client_first_name.setPlaceholderText("Imie")
        self.ed_client_first_name.setMaximumWidth(170)
        self.ed_client_last_name = QLineEdit()
        self.ed_client_last_name.setPlaceholderText("Nazwisko")
        self.ed_client_last_name.setMaximumWidth(220)
        self.ed_client_phone = QLineEdit()
        self.ed_client_phone.setPlaceholderText("Telefon")
        self.ed_client_phone.setMaximumWidth(170)
        self.ed_client_email = QLineEdit()
        self.ed_client_email.setPlaceholderText("E-mail")
        self.ed_client_email.setMaximumWidth(240)

        compact.addWidget(QLabel("ID"))
        compact.addWidget(self.ed_client_id)
        compact.addWidget(QLabel("Imie"))
        compact.addWidget(self.ed_client_first_name)
        compact.addWidget(QLabel("Nazwisko"))
        compact.addWidget(self.ed_client_last_name)
        compact.addWidget(QLabel("Telefon"))
        compact.addWidget(self.ed_client_phone)
        compact.addWidget(QLabel("E-mail"))
        compact.addWidget(self.ed_client_email)
        compact.addStretch(1)
        layout.addLayout(compact)

        address_row = QHBoxLayout()
        address_row.setSpacing(8)
        self.ed_client_street = QLineEdit()
        self.ed_client_street.setPlaceholderText("Ulica")
        self.ed_client_street.setMaximumWidth(240)
        self.ed_client_house_number = QLineEdit()
        self.ed_client_house_number.setPlaceholderText("Dom")
        self.ed_client_house_number.setMaximumWidth(100)
        self.ed_client_apartment_number = QLineEdit()
        self.ed_client_apartment_number.setPlaceholderText("Mieszkanie")
        self.ed_client_apartment_number.setMaximumWidth(120)
        self.ed_client_postal_code = QLineEdit()
        self.ed_client_postal_code.setPlaceholderText("Kod")
        self.ed_client_postal_code.setMaximumWidth(130)
        self.ed_client_city = QLineEdit()
        self.ed_client_city.setPlaceholderText("Miasto")
        self.ed_client_city.setMaximumWidth(180)
        address_row.addWidget(QLabel("Ulica"))
        address_row.addWidget(self.ed_client_street)
        address_row.addWidget(QLabel("Dom"))
        address_row.addWidget(self.ed_client_house_number)
        address_row.addWidget(QLabel("Mieszkanie"))
        address_row.addWidget(self.ed_client_apartment_number)
        address_row.addWidget(QLabel("Kod"))
        address_row.addWidget(self.ed_client_postal_code)
        address_row.addWidget(QLabel("Miasto"))
        address_row.addWidget(self.ed_client_city)
        address_row.addStretch(1)
        layout.addLayout(address_row)

        form = QFormLayout()
        self.ed_client_notes = QTextEdit()
        self.ed_client_notes.setMaximumHeight(56)

        form.addRow("Notatki", self.ed_client_notes)
        layout.addLayout(form)

        btns = QHBoxLayout()
        self.btn_client_add = QPushButton("Dodaj")
        self.btn_client_overwrite = QPushButton("Nadpisz")
        self.btn_client_delete = QPushButton("Usun")
        self.btn_client_clear = QPushButton("Wyczysc")
        for button in (
            self.btn_client_add,
            self.btn_client_overwrite,
            self.btn_client_delete,
            self.btn_client_clear,
        ):
            self._make_compact_button(button)
        btns.addWidget(self.btn_client_add)
        btns.addWidget(self.btn_client_overwrite)
        btns.addWidget(self.btn_client_delete)
        btns.addWidget(self.btn_client_clear)
        btns.addStretch(1)
        layout.addLayout(btns)

        self.tbl_clients = QTableWidget(0, 10, panel)
        self.tbl_clients.setHorizontalHeaderLabels(
            ["ID", "Imie", "Nazwisko", "Telefon", "E-mail", "Ulica", "Dom", "Mieszkanie", "Kod", "Miasto"]
        )
        self.tbl_clients.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_clients.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_clients.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_clients.verticalHeader().setVisible(False)
        self._configure_content_width_table(self.tbl_clients, "bazy_clients")
        layout.addWidget(self.tbl_clients, 1)

        self.lab_clients_status = QLabel("")
        self.lab_clients_status.setWordWrap(True)
        self.lab_clients_status.setStyleSheet(self._status_style)
        layout.addWidget(self.lab_clients_status)

        self.btn_client_add.clicked.connect(self._on_client_add)
        self.btn_client_overwrite.clicked.connect(self._on_client_overwrite)
        self.btn_client_delete.clicked.connect(self._on_client_delete)
        self.btn_client_clear.clicked.connect(self._clear_client_form)
        self.tbl_clients.itemSelectionChanged.connect(self._sync_client_form_from_selection)

        return panel

    def _build_orders_tab(self) -> QWidget:
        panel = QWidget(self)
        layout = QVBoxLayout(panel)

        filters_row = QHBoxLayout()
        filters_row.setSpacing(8)
        filters_row.addWidget(QLabel("Status"), 0)
        self.cb_order_status_filter = QComboBox(panel)
        self.cb_order_status_filter.setMinimumWidth(170)
        self.cb_order_status_filter.addItem(ORDER_STATUS_FILTER_ALL, ORDER_STATUS_FILTER_ALL)
        for status in ORDER_STATUS_ITEMS:
            self.cb_order_status_filter.addItem(status, status)
        filters_row.addWidget(self.cb_order_status_filter, 0)

        filters_row.addWidget(QLabel("Pracownik"), 0)
        self.cb_order_worker_filter = QComboBox(panel)
        self.cb_order_worker_filter.setMinimumWidth(190)
        self.cb_order_worker_filter.addItem(ORDER_WORKER_FILTER_ALL, ORDER_WORKER_FILTER_ALL)
        filters_row.addWidget(self.cb_order_worker_filter, 0)

        filters_row.addWidget(QLabel("Szukaj"), 0)
        self.ed_order_query_filter = QLineEdit(panel)
        self.ed_order_query_filter.setPlaceholderText("kod / ID / nazwa / klient / adres")
        filters_row.addWidget(self.ed_order_query_filter, 1)

        self.btn_order_clear_filters = QPushButton("Wyczysc filtry", panel)
        self._make_compact_button(self.btn_order_clear_filters, min_width=130, max_width=160)
        filters_row.addWidget(self.btn_order_clear_filters, 0)
        layout.addLayout(filters_row)

        self.lab_order_filter_info = QLabel("0 / 0", panel)
        self.lab_order_filter_info.setStyleSheet(self._status_style)
        layout.addWidget(self.lab_order_filter_info)
        self.lab_order_filter_active = QLabel("Filtry: brak", panel)
        self.lab_order_filter_active.setStyleSheet(self._status_style)
        layout.addWidget(self.lab_order_filter_active)

        form = QFormLayout()
        self.ed_order_code = QLineEdit()
        self.cb_order_client = QComboBox()
        self.cb_order_client.setEditable(True)
        self.cb_order_worker = QComboBox()
        self.cb_order_worker.setEditable(True)
        self.cb_order_status = QComboBox()
        for item in ORDER_STATUS_ITEMS:
            self.cb_order_status.addItem(item)
        self.ed_order_address = QLineEdit()
        self.ed_order_notes = QTextEdit()
        self.ed_order_notes.setMaximumHeight(90)

        form.addRow("Kod", self.ed_order_code)
        form.addRow("Klient", self.cb_order_client)
        form.addRow("Pracownik", self.cb_order_worker)
        form.addRow("Status", self.cb_order_status)
        form.addRow("Adres", self.ed_order_address)
        form.addRow("Notatki", self.ed_order_notes)
        layout.addLayout(form)

        btns = QHBoxLayout()
        self.btn_order_add = QPushButton("Dodaj")
        self.btn_order_overwrite = QPushButton("Nadpisz")
        self.btn_order_delete = QPushButton("Usun")
        self.btn_order_clear = QPushButton("Wyczysc")
        for button in (
            self.btn_order_add,
            self.btn_order_overwrite,
            self.btn_order_delete,
            self.btn_order_clear,
        ):
            self._make_compact_button(button)
        btns.addWidget(self.btn_order_add)
        btns.addWidget(self.btn_order_overwrite)
        btns.addWidget(self.btn_order_delete)
        btns.addWidget(self.btn_order_clear)
        btns.addStretch(1)
        layout.addLayout(btns)

        self.tbl_orders = QTableWidget(0, 5, panel)
        self.tbl_orders.setHorizontalHeaderLabels(["Kod", "Klient", "Status", "Pracownik", "Adres"])
        self.tbl_orders.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_orders.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_orders.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_orders.verticalHeader().setVisible(False)
        self._configure_content_width_table(self.tbl_orders, "bazy_orders")
        layout.addWidget(self.tbl_orders, 1)

        self.lab_orders_status = QLabel("")
        self.lab_orders_status.setWordWrap(True)
        self.lab_orders_status.setStyleSheet(self._status_style)
        layout.addWidget(self.lab_orders_status)

        self.btn_order_add.clicked.connect(self._on_order_add)
        self.btn_order_overwrite.clicked.connect(self._on_order_overwrite)
        self.btn_order_delete.clicked.connect(self._on_order_delete)
        self.btn_order_clear.clicked.connect(self._clear_order_form)
        self.tbl_orders.itemSelectionChanged.connect(self._sync_order_form_from_selection)
        self.cb_order_status_filter.currentIndexChanged.connect(self._reload_orders_tab)
        self.cb_order_worker_filter.currentIndexChanged.connect(self._reload_orders_tab)
        self.ed_order_query_filter.textChanged.connect(self._reload_orders_tab)
        self.btn_order_clear_filters.clicked.connect(self._clear_order_filters)

        return panel

    def _build_materials_tab(self) -> QWidget:
        panel = QWidget(self)
        layout = QVBoxLayout(panel)

        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(12)
        self.card_materials_total, self.lab_materials_total = self._make_stat_card("Materialy")
        self.card_edgebands_total, self.lab_edgebands_total = self._make_stat_card("Okleiny")
        self.card_hardware_total, self.lab_hardware_total = self._make_stat_card("Okucia")
        self.card_profiles_total, self.lab_profiles_total = self._make_stat_card("Profile")
        for card in (
            self.card_materials_total,
            self.card_edgebands_total,
            self.card_hardware_total,
            self.card_profiles_total,
        ):
            metrics_row.addWidget(card, 1)
        layout.addLayout(metrics_row)

        self.lab_materials_info = QLabel("-")
        self.lab_materials_info.setWordWrap(True)
        layout.addWidget(self.lab_materials_info)

        self.btn_open_catalog = QPushButton("Otworz edytor bazy cen")
        self._make_compact_button(self.btn_open_catalog, min_width=180, max_width=220)
        button_row = QHBoxLayout()
        button_row.addWidget(self.btn_open_catalog, 0)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        tables_row = QHBoxLayout()
        tables_row.setSpacing(12)

        materials_box, materials_layout = self._make_section_box("Materialy", "Podglad najwazniejszych materialow.")
        self.tbl_materials_preview = QTableWidget(0, 4, panel)
        self.tbl_materials_preview.setHorizontalHeaderLabels(["Material", "Grupa", "mm", "zl/m2"])
        self.tbl_materials_preview.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_materials_preview.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.tbl_materials_preview.setAlternatingRowColors(True)
        self.tbl_materials_preview.verticalHeader().setVisible(False)
        self._configure_content_width_table(self.tbl_materials_preview, "bazy_materials_preview")
        materials_layout.addWidget(self.tbl_materials_preview, 1)
        tables_row.addWidget(materials_box, 2)

        edgebands_box, edgebands_layout = self._make_section_box("Okleiny", "Podglad najwazniejszych oklein.")
        self.tbl_edgebands_preview = QTableWidget(0, 3, panel)
        self.tbl_edgebands_preview.setHorizontalHeaderLabels(["Okleina", "mm", "zl/mb"])
        self.tbl_edgebands_preview.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_edgebands_preview.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.tbl_edgebands_preview.setAlternatingRowColors(True)
        self.tbl_edgebands_preview.verticalHeader().setVisible(False)
        self._configure_content_width_table(self.tbl_edgebands_preview, "bazy_edgebands_preview")
        edgebands_layout.addWidget(self.tbl_edgebands_preview, 1)
        tables_row.addWidget(edgebands_box, 1)

        hardware_box, hardware_layout = self._make_section_box("Okucia", "Podglad najwazniejszych okuć i cen.")
        self.tbl_hardware_preview = QTableWidget(0, 4, panel)
        self.tbl_hardware_preview.setHorizontalHeaderLabels(["Okucie", "Producent", "Jedn.", "zl"])
        self.tbl_hardware_preview.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_hardware_preview.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.tbl_hardware_preview.setAlternatingRowColors(True)
        self.tbl_hardware_preview.verticalHeader().setVisible(False)
        self._configure_content_width_table(self.tbl_hardware_preview, "bazy_hardware_preview")
        hardware_layout.addWidget(self.tbl_hardware_preview, 1)
        tables_row.addWidget(hardware_box, 2)

        layout.addLayout(tables_row, 1)

        self.btn_open_catalog.clicked.connect(self._open_catalog_editor)
        return panel

    def _build_workers_tab(self) -> QWidget:
        panel = QWidget(self)
        layout = QVBoxLayout(panel)

        top_row = QHBoxLayout()

        contact_box, contact_layout = self._make_section_box(
            "Dane pracownika",
            "Podstawowe dane kontaktowe i rola w firmie.",
        )
        form = QFormLayout()
        self.ed_worker_name = QLineEdit()
        self.ed_worker_role = QLineEdit()
        self.ed_worker_phone = QLineEdit()
        self.ed_worker_email = QLineEdit()
        self.ed_worker_notes = QTextEdit()
        self.ed_worker_notes.setMaximumHeight(90)

        form.addRow("Nazwa", self.ed_worker_name)
        form.addRow("Rola", self.ed_worker_role)
        form.addRow("Telefon", self.ed_worker_phone)
        form.addRow("E-mail", self.ed_worker_email)
        form.addRow("Notatki", self.ed_worker_notes)
        contact_layout.addLayout(form)
        top_row.addWidget(contact_box, 2)

        payroll_box, payroll_layout = self._make_section_box(
            "Baza rozliczenia",
            "Te stawki sa podstawa pod Czas pracy, robocizne i przyszle wyplaty.",
        )
        payroll_form = QFormLayout()
        self.cb_worker_pay_mode = QComboBox()
        self.cb_worker_pay_mode.addItems(["Godzinowa", "Dniowka"])
        self.sp_worker_hourly_rate = QDoubleSpinBox()
        self.sp_worker_hourly_rate.setRange(0.0, 9999.99)
        self.sp_worker_hourly_rate.setDecimals(2)
        self.sp_worker_hourly_rate.setSuffix(" PLN/h")
        self.sp_worker_daily_rate = QDoubleSpinBox()
        self.sp_worker_daily_rate.setRange(0.0, 99999.99)
        self.sp_worker_daily_rate.setDecimals(2)
        self.sp_worker_daily_rate.setSuffix(" PLN/dzien")
        self.sp_worker_overtime_multiplier = QDoubleSpinBox()
        self.sp_worker_overtime_multiplier.setRange(1.0, 5.0)
        self.sp_worker_overtime_multiplier.setDecimals(2)
        self.sp_worker_overtime_multiplier.setSingleStep(0.1)
        self.sp_worker_delegation = QDoubleSpinBox()
        self.sp_worker_delegation.setRange(0.0, 9999.99)
        self.sp_worker_delegation.setDecimals(2)
        self.sp_worker_delegation.setSuffix(" PLN/dzien")
        self.sp_worker_montage = QDoubleSpinBox()
        self.sp_worker_montage.setRange(0.0, 9999.99)
        self.sp_worker_montage.setDecimals(2)
        self.sp_worker_montage.setSuffix(" PLN/h")
        self.sp_worker_onsite = QDoubleSpinBox()
        self.sp_worker_onsite.setRange(0.0, 9999.99)
        self.sp_worker_onsite.setDecimals(2)
        self.sp_worker_onsite.setSuffix(" PLN/h")
        self.sp_worker_lacquer = QDoubleSpinBox()
        self.sp_worker_lacquer.setRange(0.0, 9999.99)
        self.sp_worker_lacquer.setDecimals(2)
        self.sp_worker_lacquer.setSuffix(" PLN/h")
        payroll_form.addRow("Tryb", self.cb_worker_pay_mode)
        payroll_form.addRow("Godz.", self.sp_worker_hourly_rate)
        payroll_form.addRow("Dniowka", self.sp_worker_daily_rate)
        payroll_form.addRow("Nadgodz. x", self.sp_worker_overtime_multiplier)
        payroll_form.addRow("Delegacja", self.sp_worker_delegation)
        payroll_form.addRow("Montaz", self.sp_worker_montage)
        payroll_form.addRow("Na miejscu", self.sp_worker_onsite)
        payroll_form.addRow("Lakiernia", self.sp_worker_lacquer)
        payroll_layout.addLayout(payroll_form)
        top_row.addWidget(payroll_box, 1)
        layout.addLayout(top_row)

        btns = QHBoxLayout()
        self.btn_worker_add = QPushButton("Dodaj")
        self.btn_worker_overwrite = QPushButton("Nadpisz")
        self.btn_worker_delete = QPushButton("Usun")
        self.btn_worker_clear = QPushButton("Wyczysc")
        for button in (
            self.btn_worker_add,
            self.btn_worker_overwrite,
            self.btn_worker_delete,
            self.btn_worker_clear,
        ):
            self._make_compact_button(button)
        btns.addWidget(self.btn_worker_add)
        btns.addWidget(self.btn_worker_overwrite)
        btns.addWidget(self.btn_worker_delete)
        btns.addWidget(self.btn_worker_clear)
        btns.addStretch(1)
        layout.addLayout(btns)

        self.tbl_workers = QTableWidget(0, 7, panel)
        self.tbl_workers.setHorizontalHeaderLabels(["Nazwa", "Rola", "Tryb", "Godz.", "Dniowka", "Telefon", "E-mail"])
        self.tbl_workers.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_workers.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_workers.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_workers.verticalHeader().setVisible(False)
        self._configure_content_width_table(self.tbl_workers, "bazy_workers")
        layout.addWidget(self.tbl_workers, 1)

        self.lab_workers_status = QLabel("")
        self.lab_workers_status.setWordWrap(True)
        self.lab_workers_status.setStyleSheet(self._status_style)
        layout.addWidget(self.lab_workers_status)

        self.btn_worker_add.clicked.connect(self._on_worker_add)
        self.btn_worker_overwrite.clicked.connect(self._on_worker_overwrite)
        self.btn_worker_delete.clicked.connect(self._on_worker_delete)
        self.btn_worker_clear.clicked.connect(self._clear_worker_form)
        self.tbl_workers.itemSelectionChanged.connect(self._sync_worker_form_from_selection)

        return panel

    def _reload_all(self) -> None:
        self._reload_modules_tab()
        self._reload_walls_tab()
        self._reload_assemblies_tab()
        self._reload_clients_tab()
        self._reload_orders_tab()
        self._reload_materials_tab()
        self._reload_workers_tab()

    def _reload_modules_tab(self) -> None:
        current_name = self._selected_module_name()
        grouped = self._module_store.list_grouped_names() if hasattr(self._module_store, "list_grouped_names") else {}
        self.tree_modules.clear()
        total = 0
        selected_item: QTreeWidgetItem | None = None
        for group_name, names in grouped.items():
            group_item = QTreeWidgetItem([module_base_group_label_pl(str(group_name or ""))])
            group_item.setFlags(group_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.tree_modules.addTopLevelItem(group_item)
            for name in names:
                child = QTreeWidgetItem([name])
                child.setData(0, Qt.ItemDataRole.UserRole, name)
                group_item.addChild(child)
                if name == current_name:
                    selected_item = child
                total += 1
        self.tree_modules.expandAll()
        self._reload_module_group_choices()
        if selected_item is not None:
            self.tree_modules.setCurrentItem(selected_item)
        self.lab_modules_info.setText(f"Grupy: {len(grouped)} | Moduly: {total}")
        self._on_module_selection_changed()

    def _suggest_copy_name(self, source_name: str, existing_names: list[str]) -> str:
        base = str(source_name or "").strip() or "Kopia"
        existing = {str(name or "").strip().lower() for name in existing_names}
        candidate = f"{base} - kopia"
        if candidate.lower() not in existing:
            return candidate
        idx = 2
        while True:
            candidate = f"{base} - kopia {idx}"
            if candidate.lower() not in existing:
                return candidate
            idx += 1

    def _prompt_entry_name(self, title: str, label: str, default_value: str = "") -> str:
        value, ok = QInputDialog.getText(self, title, label, text=str(default_value or ""))
        if not ok:
            return ""
        return str(value or "").strip()

    def _reload_walls_tab(self) -> None:
        current_name = self._selected_wall_name()
        layouts = self._wall_store.list_layouts() if hasattr(self._wall_store, "list_layouts") else []
        self.tbl_walls.setRowCount(len(layouts))
        selected_row = -1
        for row, wall in enumerate(layouts):
            values = [
                str(getattr(wall, "name", "") or ""),
                str(getattr(wall, "client_name", "") or "-"),
                str(getattr(wall, "order_name", "") or "-"),
                str(getattr(wall, "layout_type", "") or "line"),
                str(len(getattr(wall, "obstacles", []) or [])),
                str(len(getattr(wall, "photos", []) or [])),
            ]
            for col, value in enumerate(values):
                self.tbl_walls.setItem(row, col, QTableWidgetItem(value))
            if values[0] == current_name:
                selected_row = row
        if selected_row >= 0:
            self.tbl_walls.selectRow(selected_row)
        self.lab_walls_info.setText(f"Sciany zapisane w bazie: {len(layouts)}")
        self._on_wall_selection_changed()
        self._resize_table_to_contents(self.tbl_walls)

    def _selected_module_name(self) -> str:
        item = self.tree_modules.currentItem()
        if item is None:
            return ""
        return str(item.data(0, Qt.ItemDataRole.UserRole) or "").strip()

    def _reload_module_group_choices(self, current_group: str = "") -> None:
        current_group = str(current_group or "").strip()
        groups = self._module_store.list_base_groups() if hasattr(self._module_store, "list_base_groups") else []
        self.cb_module_target_group.blockSignals(True)
        self.cb_module_target_group.clear()
        for group in groups:
            self.cb_module_target_group.addItem(module_base_group_label_pl(group), group)
        idx = self.cb_module_target_group.findData(current_group)
        if idx < 0 and self.cb_module_target_group.count() > 0:
            idx = 0
        if idx >= 0:
            self.cb_module_target_group.setCurrentIndex(idx)
        self.cb_module_target_group.blockSignals(False)

    def _on_module_selection_changed(self) -> None:
        name = self._selected_module_name()
        has_selection = bool(name)
        self.cb_module_target_group.setEnabled(has_selection)
        self.btn_move_module.setEnabled(has_selection)
        self.btn_add_module_group.setEnabled(has_selection)
        self.btn_duplicate_module.setEnabled(has_selection)
        self.btn_rename_module.setEnabled(has_selection)
        self.btn_open_module.setEnabled(has_selection)
        self.btn_delete_module.setEnabled(has_selection)
        if not has_selection:
            self.lab_module_detail_name.setText("-")
            self.lab_module_detail_group.setText("-")
            self.lab_module_detail_dims.setText("-")
            self.lab_module_detail_kind.setText("-")
            self.lab_module_detail_front.setText("-")
            self.lab_module_detail_inside.setText("-")
            self.lab_module_detail_profile.setText("-")
            return
        module = self._module_store.get(name) if hasattr(self._module_store, "get") else None
        current_group = str(getattr(module, "base_group", "") or "")
        self._reload_module_group_choices(current_group=current_group)
        if module is not None:
            self.lab_module_detail_name.setText(module.name or "-")
            self.lab_module_detail_group.setText(module_base_group_label_pl(current_group) or "-")
            self.lab_module_detail_dims.setText(
                f'{float(module.width_mm or 0.0):.0f} x {float(module.height_mm or 0.0):.0f} x {float(module.depth_mm or 0.0):.0f} mm'
            )
            self.lab_module_detail_kind.setText(
                f'{str(getattr(module, "cabinet_kind", "") or "-")} / {str(getattr(module, "module_family", "") or "-")}'
            )
            self.lab_module_detail_front.setText(
                f'{str(getattr(module, "facade_mode", "") or "-")} | szuflady: {int(getattr(module, "drawer_count", 0) or 0)}'
            )
            self.lab_module_detail_inside.setText(
                f'polki: {int(getattr(module, "shelf_count", 0) or 0)}, piony: {int(getattr(module, "divider_count", 0) or 0)}'
            )
            self.lab_module_detail_profile.setText(str(getattr(module, "material_profile_key", "") or "-"))

    def _on_new_module(self) -> None:
        self.sig_new_module_requested.emit()
        self._set_status(self.lab_modules_status, "Przejscie do nowego modulu.", ok=True)

    def _on_open_selected_module(self) -> None:
        name = self._selected_module_name()
        if not name:
            self._set_status(self.lab_modules_status, "Wybierz modul do otwarcia.", ok=False)
            return
        self.sig_open_module_requested.emit(name)
        self._set_status(self.lab_modules_status, f'Otwieranie modulu: "{name}".', ok=True)

    def _on_delete_selected_module(self) -> None:
        name = self._selected_module_name()
        if not name:
            self._set_status(self.lab_modules_status, "Wybierz modul do usuniecia.", ok=False)
            return
        result = self._module_store.delete(name)
        self._set_status(self.lab_modules_status, result.message_pl, ok=result.ok)
        self._reload_modules_tab()

    def _on_duplicate_selected_module(self) -> None:
        name = self._selected_module_name()
        if not name:
            self._set_status(self.lab_modules_status, "Wybierz modul do skopiowania.", ok=False)
            return
        module = self._module_store.get(name) if hasattr(self._module_store, "get") else None
        if module is None:
            self._set_status(self.lab_modules_status, f'Nie znaleziono modulu "{name}".', ok=False)
            return
        target_name = self._prompt_entry_name(
            "Duplikuj modul",
            "Nazwa kopii:",
            self._suggest_copy_name(name, self._module_store.list_names()),
        )
        if not target_name:
            return
        if target_name == name:
            self._set_status(self.lab_modules_status, "Podaj inna nazwe kopii niz oryginal.", ok=False)
            return
        module_copy = type(module).from_dict(module.to_dict())
        module_copy.name = target_name
        result = self._module_store.save_new(module_copy)
        self._set_status(self.lab_modules_status, result.message_pl, ok=result.ok)
        self._reload_modules_tab()

    def _on_rename_selected_module(self) -> None:
        name = self._selected_module_name()
        if not name:
            self._set_status(self.lab_modules_status, "Wybierz modul do zmiany nazwy.", ok=False)
            return
        module = self._module_store.get(name) if hasattr(self._module_store, "get") else None
        if module is None:
            self._set_status(self.lab_modules_status, f'Nie znaleziono modulu "{name}".', ok=False)
            return
        target_name = self._prompt_entry_name("Zmien nazwe modulu", "Nowa nazwa:", name)
        if not target_name:
            return
        if target_name == name:
            self._set_status(self.lab_modules_status, "Nazwa modulu bez zmian.", ok=True)
            return
        module_renamed = type(module).from_dict(module.to_dict())
        module_renamed.name = target_name
        save_result = self._module_store.save_new(module_renamed)
        if not save_result.ok:
            self._set_status(self.lab_modules_status, save_result.message_pl, ok=False)
            return
        delete_result = self._module_store.delete(name)
        if not delete_result.ok:
            self._set_status(self.lab_modules_status, delete_result.message_pl, ok=False)
            return
        self._set_status(
            self.lab_modules_status,
            f'Zmieniono nazwe modulu: "{name}" -> "{target_name}".',
            ok=True,
        )
        self._reload_modules_tab()
        self._select_module_name(target_name)

    def _on_move_selected_module(self) -> None:
        name = self._selected_module_name()
        if not name:
            self._set_status(self.lab_modules_status, "Wybierz modul do przeniesienia.", ok=False)
            return
        module = self._module_store.get(name) if hasattr(self._module_store, "get") else None
        if module is None:
            self._set_status(self.lab_modules_status, f'Nie znaleziono modulu "{name}".', ok=False)
            return
        target_group = str(self.cb_module_target_group.currentData() or "").strip()
        if not target_group:
            self._set_status(self.lab_modules_status, "Wybierz grupe docelowa.", ok=False)
            return
        module.base_group = target_group
        result = self._module_store.overwrite(module)
        self._set_status(self.lab_modules_status, result.message_pl, ok=result.ok)
        self._reload_modules_tab()

    def _on_add_custom_module_group(self) -> None:
        name = self._selected_module_name()
        if not name:
            self._set_status(self.lab_modules_status, "Najpierw wybierz modul.", ok=False)
            return
        group_name, ok = QInputDialog.getText(self, "Dodaj grupe", "Nazwa nowej grupy:")
        target_group = str(group_name or "").strip()
        if not ok or not target_group:
            return
        module = self._module_store.get(name) if hasattr(self._module_store, "get") else None
        if module is None:
            self._set_status(self.lab_modules_status, f'Nie znaleziono modulu "{name}".', ok=False)
            return
        module.base_group = target_group
        result = self._module_store.overwrite(module)
        self._set_status(self.lab_modules_status, result.message_pl, ok=result.ok)
        self._reload_modules_tab()

    def _select_module_name(self, name: str) -> None:
        target_name = str(name or "").strip()
        if not target_name:
            return
        for group_idx in range(self.tree_modules.topLevelItemCount()):
            group_item = self.tree_modules.topLevelItem(group_idx)
            if group_item is None:
                continue
            for child_idx in range(group_item.childCount()):
                child = group_item.child(child_idx)
                if child is None:
                    continue
                child_name = str(child.data(0, Qt.ItemDataRole.UserRole) or "").strip()
                if child_name == target_name:
                    self.tree_modules.setCurrentItem(child)
                    return

    def _selected_wall_name(self) -> str:
        rows = self.tbl_walls.selectionModel().selectedRows() if self.tbl_walls.selectionModel() is not None else []
        if not rows:
            return ""
        item = self.tbl_walls.item(int(rows[0].row()), 0)
        return item.text().strip() if item is not None else ""

    def _on_wall_selection_changed(self) -> None:
        has_selection = bool(self._selected_wall_name())
        self.btn_duplicate_wall.setEnabled(has_selection)
        self.btn_rename_wall.setEnabled(has_selection)
        self.btn_open_wall.setEnabled(has_selection)
        self.btn_delete_wall.setEnabled(has_selection)

    def _on_new_wall(self) -> None:
        self.sig_new_wall_requested.emit()
        self._set_status(self.lab_walls_status, "Przejscie do nowej sciany.", ok=True)

    def _on_open_selected_wall(self) -> None:
        name = self._selected_wall_name()
        if not name:
            self._set_status(self.lab_walls_status, "Wybierz sciane do otwarcia.", ok=False)
            return
        self.sig_open_wall_requested.emit(name)
        self._set_status(self.lab_walls_status, f'Otwieranie sciany: "{name}".', ok=True)

    def _on_delete_selected_wall(self) -> None:
        name = self._selected_wall_name()
        if not name:
            self._set_status(self.lab_walls_status, "Wybierz sciane do usuniecia.", ok=False)
            return
        result = self._wall_store.delete(name)
        self._set_status(self.lab_walls_status, result.message_pl, ok=result.ok)
        self._reload_walls_tab()

    def _on_duplicate_selected_wall(self) -> None:
        name = self._selected_wall_name()
        if not name:
            self._set_status(self.lab_walls_status, "Wybierz sciane do skopiowania.", ok=False)
            return
        wall = self._wall_store.get(name) if hasattr(self._wall_store, "get") else None
        if wall is None:
            self._set_status(self.lab_walls_status, f'Nie znaleziono sciany "{name}".', ok=False)
            return
        target_name = self._prompt_entry_name(
            "Duplikuj sciane",
            "Nazwa kopii:",
            self._suggest_copy_name(name, self._wall_store.list_names()),
        )
        if not target_name:
            return
        if target_name == name:
            self._set_status(self.lab_walls_status, "Podaj inna nazwe kopii niz oryginal.", ok=False)
            return
        wall_copy = type(wall).from_dict(wall.to_dict())
        wall_copy.name = target_name
        result = self._wall_store.save_new(wall_copy)
        self._set_status(self.lab_walls_status, result.message_pl, ok=result.ok)
        self._reload_walls_tab()
        if result.ok:
            self._select_wall_name(target_name)

    def _on_rename_selected_wall(self) -> None:
        name = self._selected_wall_name()
        if not name:
            self._set_status(self.lab_walls_status, "Wybierz sciane do zmiany nazwy.", ok=False)
            return
        wall = self._wall_store.get(name) if hasattr(self._wall_store, "get") else None
        if wall is None:
            self._set_status(self.lab_walls_status, f'Nie znaleziono sciany "{name}".', ok=False)
            return
        target_name = self._prompt_entry_name("Zmien nazwe sciany", "Nowa nazwa:", name)
        if not target_name:
            return
        if target_name == name:
            self._set_status(self.lab_walls_status, "Nazwa sciany bez zmian.", ok=True)
            return
        wall_renamed = type(wall).from_dict(wall.to_dict())
        wall_renamed.name = target_name
        save_result = self._wall_store.save_new(wall_renamed)
        if not save_result.ok:
            self._set_status(self.lab_walls_status, save_result.message_pl, ok=False)
            return
        delete_result = self._wall_store.delete(name)
        if not delete_result.ok:
            self._set_status(self.lab_walls_status, delete_result.message_pl, ok=False)
            return
        self._set_status(
            self.lab_walls_status,
            f'Zmieniono nazwe sciany: "{name}" -> "{target_name}".',
            ok=True,
        )
        self._reload_walls_tab()
        self._select_wall_name(target_name)

    def _select_wall_name(self, name: str) -> None:
        target_name = str(name or "").strip()
        if not target_name:
            return
        for row in range(self.tbl_walls.rowCount()):
            item = self.tbl_walls.item(row, 0)
            if item is not None and item.text().strip() == target_name:
                self.tbl_walls.selectRow(row)
                return

    def _selected_assembly_name(self) -> str:
        rows = self.tbl_assemblies.selectionModel().selectedRows() if self.tbl_assemblies.selectionModel() is not None else []
        if not rows:
            return ""
        item = self.tbl_assemblies.item(int(rows[0].row()), 0)
        return item.text().strip() if item is not None else ""

    def _reload_assemblies_tab(self) -> None:
        current_name = self._selected_assembly_name()
        assemblies = self._assembly_store.list_assemblies() if hasattr(self._assembly_store, "list_assemblies") else []
        self.tbl_assemblies.setRowCount(len(assemblies))
        selected_row = -1
        for row, assembly in enumerate(assemblies):
            values = [
                str(getattr(assembly, "name", "") or ""),
                str(getattr(assembly, "client_name", "") or "-"),
                str(getattr(assembly, "order_name", "") or "-"),
                str(getattr(assembly, "worker_name", "") or "-"),
                str(getattr(assembly, "wall_name", "") or "-"),
                str(len(getattr(assembly, "items", []) or [])),
            ]
            for col, value in enumerate(values):
                self.tbl_assemblies.setItem(row, col, QTableWidgetItem(value))
            if values[0] == current_name:
                selected_row = row

        count = len(assemblies)
        self.lab_assemblies_info.setText(f"Komplety zapisane w bazie: {count}")
        if selected_row >= 0:
            self.tbl_assemblies.selectRow(selected_row)
        elif count > 0:
            self.tbl_assemblies.selectRow(0)
        self._on_assembly_selection_changed()
        self._resize_table_to_contents(self.tbl_assemblies)

    def _on_assembly_selection_changed(self) -> None:
        has_selection = bool(self._selected_assembly_name())
        self.btn_duplicate_assembly.setEnabled(has_selection)
        self.btn_rename_assembly.setEnabled(has_selection)
        self.btn_open_assembly.setEnabled(has_selection)
        self.btn_delete_assembly.setEnabled(has_selection)

    def _on_new_assembly(self) -> None:
        self.sig_new_assembly_requested.emit()
        self._set_status(self.lab_assemblies_status, "Przejscie do nowego kompletu.", ok=True)

    def _on_open_selected_assembly(self) -> None:
        name = self._selected_assembly_name()
        if not name:
            self._set_status(self.lab_assemblies_status, "Wybierz komplet do otwarcia.", ok=False)
            return
        self.sig_open_assembly_requested.emit(name)
        self._set_status(self.lab_assemblies_status, f'Otwieranie kompletu: "{name}".', ok=True)

    def _on_delete_selected_assembly(self) -> None:
        name = self._selected_assembly_name()
        if not name:
            self._set_status(self.lab_assemblies_status, "Wybierz komplet do usuniecia.", ok=False)
            return
        result = self._assembly_store.delete(name)
        self._set_status(self.lab_assemblies_status, result.message_pl, ok=result.ok)
        self._reload_assemblies_tab()

    def _on_duplicate_selected_assembly(self) -> None:
        name = self._selected_assembly_name()
        if not name:
            self._set_status(self.lab_assemblies_status, "Wybierz komplet do skopiowania.", ok=False)
            return
        assembly = self._assembly_store.get(name) if hasattr(self._assembly_store, "get") else None
        if assembly is None:
            self._set_status(self.lab_assemblies_status, f'Nie znaleziono kompletu "{name}".', ok=False)
            return
        target_name = self._prompt_entry_name(
            "Duplikuj komplet",
            "Nazwa kopii:",
            self._suggest_copy_name(name, self._assembly_store.list_names()),
        )
        if not target_name:
            return
        if target_name == name:
            self._set_status(self.lab_assemblies_status, "Podaj inna nazwe kopii niz oryginal.", ok=False)
            return
        assembly_copy = type(assembly).from_dict(assembly.to_dict())
        assembly_copy.name = target_name
        result = self._assembly_store.save_new(assembly_copy)
        self._set_status(self.lab_assemblies_status, result.message_pl, ok=result.ok)
        self._reload_assemblies_tab()
        if result.ok:
            self._select_assembly_name(target_name)

    def _on_rename_selected_assembly(self) -> None:
        name = self._selected_assembly_name()
        if not name:
            self._set_status(self.lab_assemblies_status, "Wybierz komplet do zmiany nazwy.", ok=False)
            return
        assembly = self._assembly_store.get(name) if hasattr(self._assembly_store, "get") else None
        if assembly is None:
            self._set_status(self.lab_assemblies_status, f'Nie znaleziono kompletu "{name}".', ok=False)
            return
        target_name = self._prompt_entry_name("Zmien nazwe kompletu", "Nowa nazwa:", name)
        if not target_name:
            return
        if target_name == name:
            self._set_status(self.lab_assemblies_status, "Nazwa kompletu bez zmian.", ok=True)
            return
        assembly_renamed = type(assembly).from_dict(assembly.to_dict())
        assembly_renamed.name = target_name
        save_result = self._assembly_store.save_new(assembly_renamed)
        if not save_result.ok:
            self._set_status(self.lab_assemblies_status, save_result.message_pl, ok=False)
            return
        delete_result = self._assembly_store.delete(name)
        if not delete_result.ok:
            self._set_status(self.lab_assemblies_status, delete_result.message_pl, ok=False)
            return
        self._set_status(
            self.lab_assemblies_status,
            f'Zmieniono nazwe kompletu: "{name}" -> "{target_name}".',
            ok=True,
        )
        self._reload_assemblies_tab()
        self._select_assembly_name(target_name)

    def _select_assembly_name(self, name: str) -> None:
        target_name = str(name or "").strip()
        if not target_name:
            return
        for row in range(self.tbl_assemblies.rowCount()):
            item = self.tbl_assemblies.item(row, 0)
            if item is not None and item.text().strip() == target_name:
                self.tbl_assemblies.selectRow(row)
                return

    def _set_status(self, label: QLabel, message_pl: str, ok: bool) -> None:
        label.setText(str(message_pl or ""))
        label.setStyleSheet("color:#0f6a2f;" if ok else "color:#a61b1b;")

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

    def _client_identity_parts(self, client: ClientDef) -> tuple[str, str, str]:
        parsed_id, parsed_full_name = self._split_client_key(str(getattr(client, "name", "") or ""))
        parsed_first, parsed_last = self._split_full_name(parsed_full_name)
        client_id = str(getattr(client, "client_id", "") or parsed_id).strip()
        first_name = str(getattr(client, "first_name", "") or parsed_first).strip()
        last_name = str(getattr(client, "last_name", "") or parsed_last).strip()
        return client_id, first_name, last_name

    def _client_from_form(self) -> ClientDef:
        client_id = str(self.ed_client_id.text().strip())
        first_name = str(self.ed_client_first_name.text().strip())
        last_name = str(self.ed_client_last_name.text().strip())
        typed_name = str(self.ed_client_name.text().strip())
        client_name = self._build_client_key(
            client_id=client_id,
            first_name=first_name,
            last_name=last_name,
            fallback_name=typed_name,
        )
        return ClientDef(
            name=client_name,
            client_id=client_id,
            first_name=first_name,
            last_name=last_name,
            phone=str(self.ed_client_phone.text().strip()),
            email=str(self.ed_client_email.text().strip()),
            street=str(self.ed_client_street.text().strip()),
            house_number=str(self.ed_client_house_number.text().strip()),
            apartment_number=str(self.ed_client_apartment_number.text().strip()),
            postal_code=str(self.ed_client_postal_code.text().strip()),
            city=str(self.ed_client_city.text().strip()),
            notes=str(self.ed_client_notes.toPlainText().strip()),
        )

    def _selected_client_name(self) -> str:
        rows = self.tbl_clients.selectionModel().selectedRows() if self.tbl_clients.selectionModel() is not None else []
        if not rows:
            return ""
        item = self.tbl_clients.item(int(rows[0].row()), 0)
        if item is None:
            return ""
        return str(item.data(Qt.ItemDataRole.UserRole) or item.text() or "").strip()

    def _clear_client_form(self) -> None:
        self._is_syncing_client_ui = True
        try:
            self.tbl_clients.clearSelection()
            self.ed_client_name.clear()
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
        finally:
            self._is_syncing_client_ui = False

    def _sync_client_form_from_selection(self) -> None:
        if self._is_syncing_client_ui:
            return
        name = self._selected_client_name()
        client = self._client_store.get(name) if name else None
        if client is None:
            return
        self._is_syncing_client_ui = True
        try:
            self.ed_client_name.setText(client.name)
            client_id, first_name, last_name = self._client_identity_parts(client)
            self.ed_client_id.setText(client_id)
            self.ed_client_first_name.setText(first_name)
            self.ed_client_last_name.setText(last_name)
            self.ed_client_phone.setText(client.phone)
            self.ed_client_email.setText(client.email)
            self.ed_client_street.setText(str(getattr(client, "street", "") or ""))
            self.ed_client_house_number.setText(str(getattr(client, "house_number", "") or ""))
            self.ed_client_apartment_number.setText(str(getattr(client, "apartment_number", "") or ""))
            self.ed_client_postal_code.setText(str(getattr(client, "postal_code", "") or ""))
            self.ed_client_city.setText(client.city)
            self.ed_client_notes.setPlainText(client.notes)
        finally:
            self._is_syncing_client_ui = False

    def _reload_clients_tab(self) -> None:
        clients = self._client_store.list_clients()
        self.tbl_clients.setRowCount(len(clients))
        for row, client in enumerate(clients):
            client_id, first_name, last_name = self._client_identity_parts(client)
            values = [
                client_id,
                first_name,
                last_name,
                client.phone,
                client.email,
                str(getattr(client, "street", "") or ""),
                str(getattr(client, "house_number", "") or ""),
                str(getattr(client, "apartment_number", "") or ""),
                str(getattr(client, "postal_code", "") or ""),
                client.city,
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, client.name)
                self.tbl_clients.setItem(row, col, item)
        self._reload_order_client_choices()
        self._resize_table_to_contents(self.tbl_clients)

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

    def _reload_order_client_choices(self) -> None:
        current = self.cb_order_client.currentText().strip()
        client_names = [client.name for client in self._client_store.list_clients()]
        self.cb_order_client.blockSignals(True)
        self.cb_order_client.clear()
        self.cb_order_client.addItem("")
        for name in client_names:
            self.cb_order_client.addItem(name)
        self.cb_order_client.setCurrentText(current)
        self.cb_order_client.blockSignals(False)

    def _reload_order_worker_choices(self) -> None:
        current = self.cb_order_worker.currentText().strip()
        worker_names = [worker.name for worker in self._worker_store.list_workers()]
        self.cb_order_worker.blockSignals(True)
        self.cb_order_worker.clear()
        self.cb_order_worker.addItem("")
        for name in worker_names:
            self.cb_order_worker.addItem(name)
        self.cb_order_worker.setCurrentText(current)
        self.cb_order_worker.blockSignals(False)

    def _reload_order_filters(self, orders: list[OrderDef]) -> None:
        current_status = str(self.cb_order_status_filter.currentData() or ORDER_STATUS_FILTER_ALL)
        current_worker = str(self.cb_order_worker_filter.currentData() or ORDER_WORKER_FILTER_ALL)

        statuses: list[str] = []
        seen_status: set[str] = set()
        for status in ORDER_STATUS_ITEMS:
            if status not in seen_status:
                statuses.append(status)
                seen_status.add(status)
        for order in orders:
            status = str(getattr(order, "status", "") or "").strip()
            if status and status not in seen_status:
                statuses.append(status)
                seen_status.add(status)

        workers: list[str] = []
        seen_workers: set[str] = set()
        for worker in self._worker_store.list_workers():
            name = str(getattr(worker, "name", "") or "").strip()
            if name and name not in seen_workers:
                workers.append(name)
                seen_workers.add(name)
        for order in orders:
            worker_name = str(getattr(order, "worker_name", "") or "").strip()
            if worker_name and worker_name not in seen_workers:
                workers.append(worker_name)
                seen_workers.add(worker_name)

        self.cb_order_status_filter.blockSignals(True)
        self.cb_order_status_filter.clear()
        self.cb_order_status_filter.addItem(ORDER_STATUS_FILTER_ALL, ORDER_STATUS_FILTER_ALL)
        for status in statuses:
            self.cb_order_status_filter.addItem(status, status)
        idx_status = self.cb_order_status_filter.findData(current_status)
        self.cb_order_status_filter.setCurrentIndex(idx_status if idx_status >= 0 else 0)
        self.cb_order_status_filter.blockSignals(False)

        self.cb_order_worker_filter.blockSignals(True)
        self.cb_order_worker_filter.clear()
        self.cb_order_worker_filter.addItem(ORDER_WORKER_FILTER_ALL, ORDER_WORKER_FILTER_ALL)
        for worker_name in workers:
            self.cb_order_worker_filter.addItem(worker_name, worker_name)
        idx_worker = self.cb_order_worker_filter.findData(current_worker)
        self.cb_order_worker_filter.setCurrentIndex(idx_worker if idx_worker >= 0 else 0)
        self.cb_order_worker_filter.blockSignals(False)

    def _on_client_add(self) -> None:
        if not str(self.ed_client_id.text().strip()):
            self.ed_client_id.setText(self._generate_next_client_id())
        client = self._client_from_form()
        if not client.name:
            self._set_status(self.lab_clients_status, "Podaj ID, imie i nazwisko klienta.", ok=False)
            return
        result = self._client_store.save_new(client)
        self._set_status(self.lab_clients_status, result.message_pl, ok=result.ok)
        self._reload_clients_tab()

    def _on_client_overwrite(self) -> None:
        if not str(self.ed_client_id.text().strip()):
            self.ed_client_id.setText(self._generate_next_client_id())
        client = self._client_from_form()
        if not client.name:
            self._set_status(self.lab_clients_status, "Podaj ID, imie i nazwisko klienta.", ok=False)
            return
        result = self._client_store.overwrite(client)
        self._set_status(self.lab_clients_status, result.message_pl, ok=result.ok)
        self._reload_clients_tab()

    def _on_client_delete(self) -> None:
        name = self._selected_client_name() or self._build_client_key(
            self.ed_client_id.text().strip(),
            self.ed_client_first_name.text().strip(),
            self.ed_client_last_name.text().strip(),
            self.ed_client_name.text().strip(),
        )
        if not name:
            self._set_status(self.lab_clients_status, "Wybierz klienta do usuniecia.", ok=False)
            return
        result = self._client_store.delete(name)
        self._set_status(self.lab_clients_status, result.message_pl, ok=result.ok)
        self._reload_clients_tab()
        self._clear_client_form()

    def _order_from_form(self) -> OrderDef:
        return OrderDef(
            code=str(self.ed_order_code.text().strip()),
            client_name=str(self.cb_order_client.currentText().strip()),
            worker_name=str(self.cb_order_worker.currentText().strip()),
            status=str(self.cb_order_status.currentText().strip() or "Nowe"),
            site_address=str(self.ed_order_address.text().strip()),
            notes=str(self.ed_order_notes.toPlainText().strip()),
        )

    @staticmethod
    def _today_iso() -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def _with_order_stage_dates(self, order: OrderDef, previous: OrderDef | None) -> OrderDef:
        payload = order.to_dict()
        prev_payload = previous.to_dict() if previous is not None else {}
        for key in (
            "date_wycena_end",
            "date_produkcja_end",
            "date_zakup_mat_end",
            "date_montaz_end",
            "date_poprawki_end",
            "date_projekt_end",
            "date_probki_end",
        ):
            payload[key] = str(payload.get(key, "") or prev_payload.get(key, "") or "")

        today = self._today_iso()
        status = str(payload.get("status", "") or "").strip()

        if status == "Wycena gotowa":
            if not str(payload.get("date_wycena", "") or "").strip():
                payload["date_wycena"] = today
            payload["date_wycena_end"] = today
        elif status == "W produkcji":
            if not str(payload.get("date_produkcja", "") or "").strip():
                payload["date_produkcja"] = today
        elif status == "Anulowane":
            if str(payload.get("date_wycena", "") or "").strip():
                payload["date_wycena_end"] = today
            if str(payload.get("date_produkcja", "") or "").strip():
                payload["date_produkcja_end"] = today
            if str(payload.get("date_zakup_mat", "") or "").strip():
                payload["date_zakup_mat_end"] = today
            if str(payload.get("date_montaz", "") or "").strip():
                payload["date_montaz_end"] = today
            if str(payload.get("date_poprawki", "") or "").strip():
                payload["date_poprawki_end"] = today
            if str(payload.get("date_projekt", "") or "").strip():
                payload["date_projekt_end"] = today
            if str(payload.get("date_probki", "") or "").strip():
                payload["date_probki_end"] = today

        return OrderDef.from_dict(payload)

    def _with_order_status_history(self, order: OrderDef, previous: OrderDef | None) -> OrderDef:
        payload = order.to_dict()
        history = list(getattr(previous, "status_history", []) or []) if previous is not None else []
        to_status = str(getattr(order, "status", "") or "").strip()
        from_status = str(getattr(previous, "status", "") or "").strip() if previous is not None else ""
        should_append = previous is None or from_status != to_status
        if should_append:
            history.append(
                {
                    "changed_at": datetime.now().isoformat(timespec="seconds"),
                    "from_status": from_status,
                    "to_status": to_status,
                    "changed_by": str(getattr(order, "worker_name", "") or "").strip(),
                    "note": "",
                }
            )
        payload["status_history"] = history
        return OrderDef.from_dict(payload)

    def _merge_order_with_existing(self, form_order: OrderDef, existing: OrderDef | None) -> OrderDef:
        if existing is None:
            return form_order
        payload = existing.to_dict()
        payload.update(
            {
                "code": form_order.code or existing.code,
                "client_name": form_order.client_name,
                "worker_name": form_order.worker_name,
                "status": form_order.status,
                "site_address": form_order.site_address,
                "notes": form_order.notes,
            }
        )
        return OrderDef.from_dict(payload)

    def _selected_order_code(self) -> str:
        rows = self.tbl_orders.selectionModel().selectedRows() if self.tbl_orders.selectionModel() is not None else []
        if not rows:
            return ""
        item = self.tbl_orders.item(int(rows[0].row()), 0)
        return item.text().strip() if item is not None else ""

    def _select_order_by_code(self, code: str) -> bool:
        wanted = str(code or "").strip()
        if not wanted:
            return False
        for row in range(self.tbl_orders.rowCount()):
            item = self.tbl_orders.item(row, 0)
            if item is None:
                continue
            if str(item.text() or "").strip() == wanted:
                self.tbl_orders.selectRow(row)
                self._sync_order_form_from_selection()
                return True
        return False

    def _clear_order_filters(self, reload: bool = True) -> None:
        idx_status = self.cb_order_status_filter.findData(ORDER_STATUS_FILTER_ALL)
        idx_worker = self.cb_order_worker_filter.findData(ORDER_WORKER_FILTER_ALL)
        self.cb_order_status_filter.setCurrentIndex(idx_status if idx_status >= 0 else 0)
        self.cb_order_worker_filter.setCurrentIndex(idx_worker if idx_worker >= 0 else 0)
        self.ed_order_query_filter.clear()
        if reload:
            self._reload_orders_tab()

    def _clear_order_form(self) -> None:
        self._is_syncing_order_ui = True
        try:
            self.tbl_orders.clearSelection()
            self.ed_order_code.clear()
            self.cb_order_client.setCurrentText("")
            self.cb_order_worker.setCurrentText("")
            self.cb_order_status.setCurrentIndex(0)
            self.ed_order_address.clear()
            self.ed_order_notes.clear()
        finally:
            self._is_syncing_order_ui = False

    def _sync_order_form_from_selection(self) -> None:
        if self._is_syncing_order_ui:
            return
        code = self._selected_order_code()
        order = self._order_store.get(code) if code else None
        if order is None:
            return
        self._is_syncing_order_ui = True
        try:
            self.ed_order_code.setText(order.code)
            self.cb_order_client.setCurrentText(order.client_name)
            self.cb_order_worker.setCurrentText(getattr(order, "worker_name", ""))
            idx = self.cb_order_status.findText(order.status)
            if idx < 0:
                idx = 0
            self.cb_order_status.setCurrentIndex(idx)
            self.ed_order_address.setText(order.site_address)
            self.ed_order_notes.setPlainText(order.notes)
        finally:
            self._is_syncing_order_ui = False

    def _reload_orders_tab(self) -> None:
        orders = list(self._order_store.list_orders())
        self._reload_order_filters(orders)
        status_filter = str(self.cb_order_status_filter.currentData() or ORDER_STATUS_FILTER_ALL).strip()
        worker_filter = str(self.cb_order_worker_filter.currentData() or ORDER_WORKER_FILTER_ALL).strip()
        query_filter = str(self.ed_order_query_filter.text() or "").strip().lower()

        def _is_match(order: OrderDef) -> bool:
            if status_filter != ORDER_STATUS_FILTER_ALL and str(getattr(order, "status", "") or "").strip() != status_filter:
                return False
            if worker_filter != ORDER_WORKER_FILTER_ALL and str(getattr(order, "worker_name", "") or "").strip() != worker_filter:
                return False
            if not query_filter:
                return True
            haystack = " | ".join(
                [
                    str(getattr(order, "code", "") or ""),
                    str(getattr(order, "order_id", "") or ""),
                    str(getattr(order, "order_name", "") or ""),
                    str(getattr(order, "client_name", "") or ""),
                    str(getattr(order, "worker_name", "") or ""),
                    str(getattr(order, "site_address", "") or ""),
                ]
            ).lower()
            return query_filter in haystack

        filtered = [order for order in orders if _is_match(order)]
        filtered.sort(
            key=lambda order: (
                1 if str(getattr(order, "status", "") or "").strip() in _ORDER_CLOSED_STATUSES else 0,
                str(getattr(order, "code", "") or "").strip().lower(),
            )
        )

        self.tbl_orders.setRowCount(len(filtered))
        for row, order in enumerate(filtered):
            values = [
                str(getattr(order, "code", "") or ""),
                str(getattr(order, "client_name", "") or ""),
                str(getattr(order, "status", "") or ""),
                str(getattr(order, "worker_name", "") or ""),
                str(getattr(order, "site_address", "") or ""),
            ]
            for col, value in enumerate(values):
                self.tbl_orders.setItem(row, col, QTableWidgetItem(value))

        active_filters: list[str] = []
        if status_filter != ORDER_STATUS_FILTER_ALL:
            active_filters.append(f"status: {status_filter}")
        if worker_filter != ORDER_WORKER_FILTER_ALL:
            active_filters.append(f"pracownik: {worker_filter}")
        if query_filter:
            active_filters.append(f"szukaj: {query_filter}")
        self.lab_order_filter_active.setText("Filtry: brak" if not active_filters else "Filtry: " + " | ".join(active_filters))
        self.lab_order_filter_info.setText(f"Wynik: {len(filtered)} / {len(orders)}")
        self._reload_order_worker_choices()
        self._resize_table_to_contents(self.tbl_orders)

    def _on_order_add(self) -> None:
        form_order = self._order_from_form()
        if not form_order.code:
            self._set_status(self.lab_orders_status, "Podaj kod zamowienia.", ok=False)
            return
        order = self._with_order_stage_dates(form_order, previous=None)
        order = self._with_order_status_history(order, previous=None)
        result = self._order_store.save_new(order)
        self._set_status(self.lab_orders_status, result.message_pl, ok=result.ok)
        self._reload_orders_tab()

    def _on_order_overwrite(self) -> None:
        form_order = self._order_from_form()
        if not form_order.code:
            self._set_status(self.lab_orders_status, "Podaj kod zamowienia.", ok=False)
            return
        previous = self._order_store.get(form_order.code)
        order = self._merge_order_with_existing(form_order, previous)
        order = self._with_order_stage_dates(order, previous)
        order = self._with_order_status_history(order, previous)
        result = self._order_store.overwrite(order)
        self._set_status(self.lab_orders_status, result.message_pl, ok=result.ok)
        self._reload_orders_tab()

    def _on_order_delete(self) -> None:
        code = self._selected_order_code() or str(self.ed_order_code.text().strip())
        if not code:
            self._set_status(self.lab_orders_status, "Wybierz zamowienie do usuniecia.", ok=False)
            return
        result = self._order_store.delete(code)
        self._set_status(self.lab_orders_status, result.message_pl, ok=result.ok)
        self._reload_orders_tab()
        self._clear_order_form()

    def _reload_materials_tab(self) -> None:
        materials_list = self._catalog.list_materials()
        edgebands_list = self._catalog.list_edgebands()
        hardware_list = self._catalog.list_hardware()
        profiles_list = self._catalog.list_material_profiles()
        materials = len(materials_list)
        edgebands = len(edgebands_list)
        hardware = len(hardware_list)
        profiles = len(profiles_list)
        self.lab_materials_total.setText(str(materials))
        self.lab_edgebands_total.setText(str(edgebands))
        self.lab_hardware_total.setText(str(hardware))
        self.lab_profiles_total.setText(str(profiles))
        self.lab_materials_info.setText(
            "Baza materialow korzysta z tego samego katalogu, co Modul i bedzie baza pod wycene, zakupy i magazyn.\n\n"
            "To tutaj pozniej trafia ceny z dokumentow dostawy, WZ i faktur od dostawcow."
        )
        self.tbl_materials_preview.setRowCount(0)
        for row, material in enumerate(materials_list[:8]):
            self.tbl_materials_preview.insertRow(row)
            values = [
                material.name_pl,
                material.material_group or "-",
                f"{material.thickness_mm:.1f}",
                f"{material.price_pln_per_m2:.2f}",
            ]
            for col, value in enumerate(values):
                self.tbl_materials_preview.setItem(row, col, QTableWidgetItem(value))

        self.tbl_edgebands_preview.setRowCount(0)
        for row, band in enumerate(edgebands_list[:8]):
            self.tbl_edgebands_preview.insertRow(row)
            values = [band.name_pl, f"{band.thickness_mm:.1f}", f"{band.price_pln_per_m:.2f}"]
            for col, value in enumerate(values):
                self.tbl_edgebands_preview.setItem(row, col, QTableWidgetItem(value))

        self.tbl_hardware_preview.setRowCount(0)
        for row, hardware_item in enumerate(hardware_list[:8]):
            self.tbl_hardware_preview.insertRow(row)
            values = [
                hardware_item.name_pl,
                hardware_item.manufacturer or "-",
                hardware_item.unit or "szt",
                f"{hardware_item.price_pln:.2f}",
            ]
            for col, value in enumerate(values):
                self.tbl_hardware_preview.setItem(row, col, QTableWidgetItem(value))
        self._resize_table_to_contents(self.tbl_materials_preview)
        self._resize_table_to_contents(self.tbl_edgebands_preview)
        self._resize_table_to_contents(self.tbl_hardware_preview)

    def _open_catalog_editor(self) -> None:
        dlg = CatalogEditorDialog(self, self._catalog)
        dlg.exec()
        self._reload_materials_tab()

    def _worker_from_form(self) -> WorkerDef:
        return WorkerDef(
            name=str(self.ed_worker_name.text().strip()),
            role=str(self.ed_worker_role.text().strip()),
            phone=str(self.ed_worker_phone.text().strip()),
            email=str(self.ed_worker_email.text().strip()),
            notes=str(self.ed_worker_notes.toPlainText().strip()),
            pay_mode=str(self.cb_worker_pay_mode.currentText().strip() or "Godzinowa"),
            hourly_rate=float(self.sp_worker_hourly_rate.value()),
            daily_rate=float(self.sp_worker_daily_rate.value()),
            overtime_multiplier=float(self.sp_worker_overtime_multiplier.value()),
            delegation_day_addon_pln=float(self.sp_worker_delegation.value()),
            montage_hour_addon_pln=float(self.sp_worker_montage.value()),
            onsite_hour_addon_pln=float(self.sp_worker_onsite.value()),
            lacquer_hour_addon_pln=float(self.sp_worker_lacquer.value()),
        )

    def _selected_worker_name(self) -> str:
        rows = self.tbl_workers.selectionModel().selectedRows() if self.tbl_workers.selectionModel() is not None else []
        if not rows:
            return ""
        item = self.tbl_workers.item(int(rows[0].row()), 0)
        return item.text().strip() if item is not None else ""

    def _clear_worker_form(self) -> None:
        self._is_syncing_worker_ui = True
        try:
            self.tbl_workers.clearSelection()
            self.ed_worker_name.clear()
            self.ed_worker_role.clear()
            self.ed_worker_phone.clear()
            self.ed_worker_email.clear()
            self.ed_worker_notes.clear()
            self.cb_worker_pay_mode.setCurrentText("Godzinowa")
            self.sp_worker_hourly_rate.setValue(0.0)
            self.sp_worker_daily_rate.setValue(0.0)
            self.sp_worker_overtime_multiplier.setValue(1.0)
            self.sp_worker_delegation.setValue(0.0)
            self.sp_worker_montage.setValue(0.0)
            self.sp_worker_onsite.setValue(0.0)
            self.sp_worker_lacquer.setValue(0.0)
        finally:
            self._is_syncing_worker_ui = False

    def _sync_worker_form_from_selection(self) -> None:
        if self._is_syncing_worker_ui:
            return
        name = self._selected_worker_name()
        worker = self._worker_store.get(name) if name else None
        if worker is None:
            return
        self._is_syncing_worker_ui = True
        try:
            self.ed_worker_name.setText(worker.name)
            self.ed_worker_role.setText(worker.role)
            self.ed_worker_phone.setText(worker.phone)
            self.ed_worker_email.setText(worker.email)
            self.ed_worker_notes.setPlainText(worker.notes)
            self.cb_worker_pay_mode.setCurrentText(worker.pay_mode or "Godzinowa")
            self.sp_worker_hourly_rate.setValue(float(worker.hourly_rate or 0.0))
            self.sp_worker_daily_rate.setValue(float(worker.daily_rate or 0.0))
            self.sp_worker_overtime_multiplier.setValue(float(worker.overtime_multiplier or 1.0))
            self.sp_worker_delegation.setValue(float(worker.delegation_day_addon_pln or 0.0))
            self.sp_worker_montage.setValue(float(worker.montage_hour_addon_pln or 0.0))
            self.sp_worker_onsite.setValue(float(worker.onsite_hour_addon_pln or 0.0))
            self.sp_worker_lacquer.setValue(float(worker.lacquer_hour_addon_pln or 0.0))
        finally:
            self._is_syncing_worker_ui = False

    def _reload_workers_tab(self) -> None:
        workers = self._worker_store.list_workers()
        self.tbl_workers.setRowCount(len(workers))
        for row, worker in enumerate(workers):
            values = [
                worker.name,
                worker.role,
                worker.pay_mode,
                f"{float(worker.hourly_rate or 0.0):.2f}",
                f"{float(worker.daily_rate or 0.0):.2f}",
                worker.phone,
                worker.email,
            ]
            for col, value in enumerate(values):
                self.tbl_workers.setItem(row, col, QTableWidgetItem(value))
        self._resize_table_to_contents(self.tbl_workers)
        self._reload_order_worker_choices()

    def _on_worker_add(self) -> None:
        worker = self._worker_from_form()
        if not worker.name:
            self._set_status(self.lab_workers_status, "Podaj nazwe pracownika.", ok=False)
            return
        result = self._worker_store.save_new(worker)
        self._set_status(self.lab_workers_status, result.message_pl, ok=result.ok)
        self._reload_workers_tab()

    def _on_worker_overwrite(self) -> None:
        worker = self._worker_from_form()
        if not worker.name:
            self._set_status(self.lab_workers_status, "Podaj nazwe pracownika.", ok=False)
            return
        result = self._worker_store.overwrite(worker)
        self._set_status(self.lab_workers_status, result.message_pl, ok=result.ok)
        self._reload_workers_tab()

    def _on_worker_delete(self) -> None:
        name = self._selected_worker_name() or str(self.ed_worker_name.text().strip())
        if not name:
            self._set_status(self.lab_workers_status, "Wybierz pracownika do usuniecia.", ok=False)
            return
        result = self._worker_store.delete(name)
        self._set_status(self.lab_workers_status, result.message_pl, ok=result.ok)
        self._reload_workers_tab()
        self._clear_worker_form()
