from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFormLayout,
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
    "W produkcji",
    "Gotowe",
    "Zakonczone",
)


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
        title.setStyleSheet("font-weight:700;")
        root.addWidget(title)

        self.tabs = QTabWidget(self)
        root.addWidget(self.tabs, 1)

        self.tabs.addTab(self._build_modules_tab(), "Moduly")
        self.tabs.addTab(self._build_walls_tab(), "Sciany")
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
                self.ed_client_name.setFocus()
        return opened

    def open_orders_tab(self, clear_form: bool = False) -> bool:
        opened = self._open_subtab_by_title("Zamowienia")
        if opened:
            self._reload_orders_tab()
            if clear_form:
                self._clear_order_form()
                self.ed_order_code.setFocus()
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

    def _configure_content_width_table(self, table: QTableWidget) -> None:
        header = table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        if table.columnCount() > 0:
            header.setSectionResizeMode(table.columnCount() - 1, QHeaderView.ResizeMode.Stretch)

    def _resize_table_to_contents(self, table: QTableWidget) -> None:
        try:
            table.resizeColumnsToContents()
            table.resizeRowsToContents()
        except Exception:
            pass

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
        self.lab_modules_status.setStyleSheet("color:#666666;")
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
        self.btn_new_wall = QPushButton("Nowa w Sciana")
        self.btn_reload_walls = QPushButton("Odswiez")
        row.addWidget(self.btn_new_wall, 0)
        row.addStretch(1)
        row.addWidget(self.btn_reload_walls, 0)
        layout.addLayout(row)

        self.tbl_walls = QTableWidget(0, 6, panel)
        self.tbl_walls.setHorizontalHeaderLabels(["Nazwa", "Klient", "Zamowienie", "Typ", "Przeszkody", "Zdjecia"])
        self.tbl_walls.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_walls.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_walls.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_walls.verticalHeader().setVisible(False)
        self._configure_content_width_table(self.tbl_walls)
        layout.addWidget(self.tbl_walls, 1)

        btns = QHBoxLayout()
        self.btn_duplicate_wall = QPushButton("Duplikuj")
        self.btn_rename_wall = QPushButton("Zmien nazwe")
        self.btn_open_wall = QPushButton("Otworz w Sciana")
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
        self.lab_walls_status.setStyleSheet("color:#666666;")
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
            ["Nazwa", "Klient", "Zamowienie", "Pracownik", "Sciana", "Moduly"]
        )
        self.tbl_assemblies.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_assemblies.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_assemblies.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_assemblies.verticalHeader().setVisible(False)
        self._configure_content_width_table(self.tbl_assemblies)
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
        self.lab_assemblies_info.setStyleSheet("color:#666666;")
        layout.addWidget(self.lab_assemblies_info)

        self.lab_assemblies_status = QLabel("")
        self.lab_assemblies_status.setWordWrap(True)
        self.lab_assemblies_status.setStyleSheet("color:#666666;")
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

        form = QFormLayout()
        self.ed_client_name = QLineEdit()
        self.ed_client_phone = QLineEdit()
        self.ed_client_email = QLineEdit()
        self.ed_client_city = QLineEdit()
        self.ed_client_notes = QTextEdit()
        self.ed_client_notes.setMaximumHeight(90)

        form.addRow("Nazwa", self.ed_client_name)
        form.addRow("Telefon", self.ed_client_phone)
        form.addRow("E-mail", self.ed_client_email)
        form.addRow("Miasto", self.ed_client_city)
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

        self.tbl_clients = QTableWidget(0, 4, panel)
        self.tbl_clients.setHorizontalHeaderLabels(["Nazwa", "Telefon", "E-mail", "Miasto"])
        self.tbl_clients.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_clients.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_clients.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_clients.verticalHeader().setVisible(False)
        self._configure_content_width_table(self.tbl_clients)
        layout.addWidget(self.tbl_clients, 1)

        self.lab_clients_status = QLabel("")
        self.lab_clients_status.setWordWrap(True)
        self.lab_clients_status.setStyleSheet("color:#666666;")
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
        self.tbl_orders.setHorizontalHeaderLabels(["Kod", "Klient", "Pracownik", "Status", "Adres"])
        self.tbl_orders.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_orders.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_orders.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_orders.verticalHeader().setVisible(False)
        self._configure_content_width_table(self.tbl_orders)
        layout.addWidget(self.tbl_orders, 1)

        self.lab_orders_status = QLabel("")
        self.lab_orders_status.setWordWrap(True)
        self.lab_orders_status.setStyleSheet("color:#666666;")
        layout.addWidget(self.lab_orders_status)

        self.btn_order_add.clicked.connect(self._on_order_add)
        self.btn_order_overwrite.clicked.connect(self._on_order_overwrite)
        self.btn_order_delete.clicked.connect(self._on_order_delete)
        self.btn_order_clear.clicked.connect(self._clear_order_form)
        self.tbl_orders.itemSelectionChanged.connect(self._sync_order_form_from_selection)

        return panel

    def _build_materials_tab(self) -> QWidget:
        panel = QWidget(self)
        layout = QVBoxLayout(panel)

        self.lab_materials_info = QLabel("-")
        self.lab_materials_info.setWordWrap(True)
        layout.addWidget(self.lab_materials_info)

        self.btn_open_catalog = QPushButton("Otworz edytor bazy cen")
        self._make_compact_button(self.btn_open_catalog, min_width=180, max_width=220)
        layout.addWidget(self.btn_open_catalog, 0)
        layout.addStretch(1)

        self.btn_open_catalog.clicked.connect(self._open_catalog_editor)
        return panel

    def _build_workers_tab(self) -> QWidget:
        panel = QWidget(self)
        layout = QVBoxLayout(panel)

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
        layout.addLayout(form)

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

        self.tbl_workers = QTableWidget(0, 4, panel)
        self.tbl_workers.setHorizontalHeaderLabels(["Nazwa", "Rola", "Telefon", "E-mail"])
        self.tbl_workers.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_workers.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_workers.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_workers.verticalHeader().setVisible(False)
        self._configure_content_width_table(self.tbl_workers)
        layout.addWidget(self.tbl_workers, 1)

        self.lab_workers_status = QLabel("")
        self.lab_workers_status.setWordWrap(True)
        self.lab_workers_status.setStyleSheet("color:#666666;")
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
            return
        module = self._module_store.get(name) if hasattr(self._module_store, "get") else None
        current_group = str(getattr(module, "base_group", "") or "")
        self._reload_module_group_choices(current_group=current_group)

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

    def _client_from_form(self) -> ClientDef:
        return ClientDef(
            name=str(self.ed_client_name.text().strip()),
            phone=str(self.ed_client_phone.text().strip()),
            email=str(self.ed_client_email.text().strip()),
            city=str(self.ed_client_city.text().strip()),
            notes=str(self.ed_client_notes.toPlainText().strip()),
        )

    def _selected_client_name(self) -> str:
        rows = self.tbl_clients.selectionModel().selectedRows() if self.tbl_clients.selectionModel() is not None else []
        if not rows:
            return ""
        item = self.tbl_clients.item(int(rows[0].row()), 0)
        return item.text().strip() if item is not None else ""

    def _clear_client_form(self) -> None:
        self._is_syncing_client_ui = True
        try:
            self.tbl_clients.clearSelection()
            self.ed_client_name.clear()
            self.ed_client_phone.clear()
            self.ed_client_email.clear()
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
            self.ed_client_phone.setText(client.phone)
            self.ed_client_email.setText(client.email)
            self.ed_client_city.setText(client.city)
            self.ed_client_notes.setPlainText(client.notes)
        finally:
            self._is_syncing_client_ui = False

    def _reload_clients_tab(self) -> None:
        clients = self._client_store.list_clients()
        self.tbl_clients.setRowCount(len(clients))
        for row, client in enumerate(clients):
            values = [client.name, client.phone, client.email, client.city]
            for col, value in enumerate(values):
                self.tbl_clients.setItem(row, col, QTableWidgetItem(value))
        self._reload_order_client_choices()
        self._resize_table_to_contents(self.tbl_clients)

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

    def _on_client_add(self) -> None:
        client = self._client_from_form()
        if not client.name:
            self._set_status(self.lab_clients_status, "Podaj nazwe klienta.", ok=False)
            return
        result = self._client_store.save_new(client)
        self._set_status(self.lab_clients_status, result.message_pl, ok=result.ok)
        self._reload_clients_tab()

    def _on_client_overwrite(self) -> None:
        client = self._client_from_form()
        if not client.name:
            self._set_status(self.lab_clients_status, "Podaj nazwe klienta.", ok=False)
            return
        result = self._client_store.overwrite(client)
        self._set_status(self.lab_clients_status, result.message_pl, ok=result.ok)
        self._reload_clients_tab()

    def _on_client_delete(self) -> None:
        name = self._selected_client_name() or str(self.ed_client_name.text().strip())
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

    def _selected_order_code(self) -> str:
        rows = self.tbl_orders.selectionModel().selectedRows() if self.tbl_orders.selectionModel() is not None else []
        if not rows:
            return ""
        item = self.tbl_orders.item(int(rows[0].row()), 0)
        return item.text().strip() if item is not None else ""

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
        orders = self._order_store.list_orders()
        self.tbl_orders.setRowCount(len(orders))
        for row, order in enumerate(orders):
            values = [order.code, order.client_name, getattr(order, "worker_name", ""), order.status, order.site_address]
            for col, value in enumerate(values):
                self.tbl_orders.setItem(row, col, QTableWidgetItem(value))
        self._reload_order_worker_choices()
        self._resize_table_to_contents(self.tbl_orders)

    def _on_order_add(self) -> None:
        order = self._order_from_form()
        if not order.code:
            self._set_status(self.lab_orders_status, "Podaj kod zamowienia.", ok=False)
            return
        result = self._order_store.save_new(order)
        self._set_status(self.lab_orders_status, result.message_pl, ok=result.ok)
        self._reload_orders_tab()

    def _on_order_overwrite(self) -> None:
        order = self._order_from_form()
        if not order.code:
            self._set_status(self.lab_orders_status, "Podaj kod zamowienia.", ok=False)
            return
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
        materials = len(self._catalog.list_materials())
        edgebands = len(self._catalog.list_edgebands())
        hardware = len(self._catalog.list_hardware())
        profiles = len(self._catalog.list_material_profiles())
        self.lab_materials_info.setText(
            "Baza materialow korzysta z tego samego katalogu, co Modul.\n\n"
            f"Materialy: {materials}\n"
            f"Okleiny: {edgebands}\n"
            f"Okucia: {hardware}\n"
            f"Profile: {profiles}"
        )

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
        finally:
            self._is_syncing_worker_ui = False

    def _reload_workers_tab(self) -> None:
        workers = self._worker_store.list_workers()
        self.tbl_workers.setRowCount(len(workers))
        for row, worker in enumerate(workers):
            values = [worker.name, worker.role, worker.phone, worker.email]
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
