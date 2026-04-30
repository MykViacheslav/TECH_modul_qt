from __future__ import annotations

from datetime import date
from typing import Any, Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.operations_models import ISSUE_TYPE_VALUES, ROUTE_STATUS_VALUES, STATUS_VALUES, IssueRecord
from src.core.operations_store import OperationsStore


def _bool_pl(value: bool) -> str:
    return "TAK" if bool(value) else "NIE"


def _fmt_money(value: float) -> str:
    return f"{float(value or 0.0):.2f}"


class PrioritiesRoutesPanel(QWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        store: OperationsStore | None = None,
        on_data_changed: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._store = store or OperationsStore()
        self._on_data_changed_cb = on_data_changed
        self._role = "biuro"
        self._worker_name = ""
        self._priority_rows: list[dict[str, Any]] = []
        self._route_rows = []
        self._priority_fin_cols = [8, 9]

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        self._build_priority_filters(root)
        self._build_route_filters(root)
        self._build_tables(root)
        self._apply_role_visibility()
        self.refresh_data()

    def set_current_user(self, worker_name: str, role: str) -> None:
        self._worker_name = str(worker_name or "").strip()
        self._role = str(role or "").strip().lower()
        self._apply_role_visibility()
        self.refresh_data()

    def _apply_role_visibility(self) -> None:
        hide_fin = self._role in {"produkcja", "magazyn", "montaz"}
        if hasattr(self, "tbl_priority"):
            for col in self._priority_fin_cols:
                self.tbl_priority.setColumnHidden(col, hide_fin)

    def _notify_change(self) -> None:
        if callable(self._on_data_changed_cb):
            self._on_data_changed_cb()

    def _build_priority_filters(self, root: QVBoxLayout) -> None:
        box = QFrame(self); box.setProperty("uiCard", True)
        lay = QHBoxLayout(box)
        lay.setContentsMargins(8, 8, 8, 8)
        self.p_text = QLineEdit(self)
        self.p_text.setPlaceholderText("Filtr priorytetow...")
        self.p_status = QComboBox(self)
        self.p_status.addItem("Status: wszystkie", "all")
        for key, label in STATUS_VALUES.items():
            self.p_status.addItem(f"Status: {label}", key)
        self.p_area = QComboBox(self)
        self.p_area.addItem("Obszar: wszystkie", "all")
        for key, label in ISSUE_TYPE_VALUES.items():
            self.p_area.addItem(label, key)
        self.p_date = QDateEdit(self)
        self.p_date.setCalendarPopup(True)
        self.p_date.setDate(date.today())
        self.p_date.setDisplayFormat("yyyy-MM-dd")
        self.p_crew = QLineEdit(self)
        self.p_crew.setPlaceholderText("Ekipa (do utworzenia trasy)")
        self.p_group = QLineEdit(self)
        self.p_group.setPlaceholderText("Grupa trasy")
        self.btn_create_route = QPushButton("Utworz trase z wybranego problemu", self)
        lay.addWidget(QLabel("Priorytety dnia:", self))
        lay.addWidget(self.p_text, 1)
        lay.addWidget(self.p_status)
        lay.addWidget(self.p_area)
        lay.addWidget(self.p_date)
        lay.addWidget(self.p_crew)
        lay.addWidget(self.p_group)
        lay.addWidget(self.btn_create_route)
        root.addWidget(box)

        self.p_text.textChanged.connect(self.refresh_data)
        self.p_status.currentIndexChanged.connect(self.refresh_data)
        self.p_area.currentIndexChanged.connect(self.refresh_data)
        self.btn_create_route.clicked.connect(self._on_create_route_from_selected_issue)

    def _build_route_filters(self, root: QVBoxLayout) -> None:
        box = QFrame(self); box.setProperty("uiCard", True)
        lay = QHBoxLayout(box)
        lay.setContentsMargins(8, 8, 8, 8)
        self.r_text = QLineEdit(self)
        self.r_text.setPlaceholderText("Filtr tras...")
        self.r_date = QDateEdit(self)
        self.r_date.setCalendarPopup(True)
        self.r_date.setDate(date.today())
        self.r_date.setDisplayFormat("yyyy-MM-dd")
        self.r_city = QLineEdit(self)
        self.r_city.setPlaceholderText("Miasto")
        self.r_crew = QLineEdit(self)
        self.r_crew.setPlaceholderText("Ekipa")
        self.r_group = QLineEdit(self)
        self.r_group.setPlaceholderText("Grupa")
        self.r_status = QComboBox(self)
        self.r_status.addItem("Status: wszystkie", "all")
        for key, label in ROUTE_STATUS_VALUES.items():
            self.r_status.addItem(f"Status: {label}", key)
        self.btn_assign_group = QPushButton("Przypisz grupe trasy", self)
        self.btn_done = QPushButton("Oznacz trase jako wykonana", self)
        lay.addWidget(QLabel("Trasy i wyjazdy:", self))
        lay.addWidget(self.r_text, 1)
        lay.addWidget(self.r_date)
        lay.addWidget(self.r_city)
        lay.addWidget(self.r_crew)
        lay.addWidget(self.r_group)
        lay.addWidget(self.r_status)
        lay.addWidget(self.btn_assign_group)
        lay.addWidget(self.btn_done)
        root.addWidget(box)

        self.r_text.textChanged.connect(self.refresh_data)
        self.r_date.dateChanged.connect(self.refresh_data)
        self.r_city.textChanged.connect(self.refresh_data)
        self.r_crew.textChanged.connect(self.refresh_data)
        self.r_group.textChanged.connect(self.refresh_data)
        self.r_status.currentIndexChanged.connect(self.refresh_data)
        self.btn_assign_group.clicked.connect(self._on_assign_route_group)
        self.btn_done.clicked.connect(self._on_mark_route_done)

    def _build_tables(self, root: QVBoxLayout) -> None:
        splitter = QSplitter(Qt.Orientation.Vertical, self)

        self.tbl_priority = QTableWidget(0, 15, self)
        self.tbl_priority.setHorizontalHeaderLabels(
            [
                "Wynik",
                "Projekt",
                "Klient",
                "Temat",
                "Typ zadania",
                "Status",
                "Ile pracy zostalo",
                "Szacowany czas",
                "Mozliwy odzysk przychodu",
                "Koszt domkniecia",
                "Blokuje fakture",
                "Po terminie",
                "Szybkie domkniecie",
                "Odpowiedzialny",
                "Termin",
            ]
        )
        self.tbl_priority.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_priority.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_priority.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_priority.verticalHeader().setVisible(False)
        h1 = self.tbl_priority.horizontalHeader()
        for col in range(15):
            mode = QHeaderView.ResizeMode.ResizeToContents
            if col == 3:
                mode = QHeaderView.ResizeMode.Stretch
            h1.setSectionResizeMode(col, mode)
        splitter.addWidget(self.tbl_priority)

        self.tbl_routes = QTableWidget(0, 14, self)
        self.tbl_routes.setHorizontalHeaderLabels(
            [
                "Data",
                "Ekipa",
                "Grupa trasy",
                "Projekt",
                "Klient",
                "Miasto",
                "Adres",
                "Typ zadania",
                "Opis",
                "Szacowany czas",
                "Priorytet",
                "Status",
                "Po drodze",
                "Uwagi",
            ]
        )
        self.tbl_routes.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_routes.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_routes.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_routes.verticalHeader().setVisible(False)
        h2 = self.tbl_routes.horizontalHeader()
        for col in range(14):
            mode = QHeaderView.ResizeMode.ResizeToContents
            if col in {8, 13}:
                mode = QHeaderView.ResizeMode.Stretch
            h2.setSectionResizeMode(col, mode)
        splitter.addWidget(self.tbl_routes)

        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 4)
        root.addWidget(splitter, 1)

    def refresh_data(self) -> None:
        self._refresh_priorities()
        self._refresh_routes()

    def navigate_to_route_or_issue(
        self,
        route_id: str | None = None,
        issue_id: str | None = None,
        project_name: str = "",
        client_name: str = "",
    ) -> bool:
        wanted_route = str(route_id or "").strip()
        wanted_issue = str(issue_id or "").strip()
        wanted_project = str(project_name or "").strip().lower()
        wanted_client = str(client_name or "").strip().lower()
        self.refresh_data()

        if wanted_issue:
            for i, row_item in enumerate(self._priority_rows):
                issue = row_item["issue"]
                if str(issue.id or "").strip() == wanted_issue:
                    self.tbl_priority.selectRow(i)
                    item = self.tbl_priority.item(i, 0)
                    if item is not None:
                        self.tbl_priority.scrollToItem(item, QAbstractItemView.ScrollHint.PositionAtCenter)
                    return True

        if wanted_route:
            for i, route in enumerate(self._route_rows):
                if str(route.id or "").strip() == wanted_route:
                    self.tbl_routes.selectRow(i)
                    item = self.tbl_routes.item(i, 0)
                    if item is not None:
                        self.tbl_routes.scrollToItem(item, QAbstractItemView.ScrollHint.PositionAtCenter)
                    return True

        if wanted_project or wanted_client:
            for i, row_item in enumerate(self._priority_rows):
                issue = row_item["issue"]
                project_ok = (not wanted_project) or (wanted_project in str(issue.project_name or "").lower())
                client_ok = (not wanted_client) or (wanted_client in str(issue.client_name or "").lower())
                if project_ok and client_ok:
                    self.tbl_priority.selectRow(i)
                    item = self.tbl_priority.item(i, 0)
                    if item is not None:
                        self.tbl_priority.scrollToItem(item, QAbstractItemView.ScrollHint.PositionAtCenter)
                    return True

            for i, route in enumerate(self._route_rows):
                project_ok = (not wanted_project) or (wanted_project in str(route.project_name or "").lower())
                client_ok = (not wanted_client) or (wanted_client in str(route.client_name or "").lower())
                if project_ok and client_ok:
                    self.tbl_routes.selectRow(i)
                    item = self.tbl_routes.item(i, 0)
                    if item is not None:
                        self.tbl_routes.scrollToItem(item, QAbstractItemView.ScrollHint.PositionAtCenter)
                    return True
        return False

    def _refresh_priorities(self) -> None:
        self._priority_rows = self._store.list_priority_candidates(
            role=self._role,
            worker_name=self._worker_name,
            text=self.p_text.text().strip(),
            status=str(self.p_status.currentData() or "all"),
            area=str(self.p_area.currentData() or "all"),
        )
        self._populate_priority_table()

    def _refresh_routes(self) -> None:
        self._route_rows = self._store.filter_routes(
            planned_date=self.r_date.date().toString("yyyy-MM-dd"),
            crew=self.r_crew.text().strip(),
            route_group=self.r_group.text().strip(),
            city=self.r_city.text().strip(),
            status=str(self.r_status.currentData() or "all"),
            text=self.r_text.text().strip(),
            role=self._role,
            worker_name=self._worker_name,
        )
        self._populate_routes_table()

    def _populate_priority_table(self) -> None:
        self.tbl_priority.setRowCount(0)
        for row_item in self._priority_rows:
            issue: IssueRecord = row_item["issue"]
            row = self.tbl_priority.rowCount()
            self.tbl_priority.insertRow(row)
            work_left = "Malo" if issue.is_quick_close_candidate() else "Srednio/duzo"
            values = [
                f"{float(row_item['score']):.1f}",
                issue.project_name,
                issue.client_name,
                issue.title or issue.description[:80],
                issue.issue_type,
                issue.status,
                work_left,
                str(int(issue.estimated_time_minutes or 0)),
                _fmt_money(issue.estimated_revenue_unlock),
                _fmt_money(issue.estimated_cost),
                _bool_pl(issue.blocks_invoice),
                _bool_pl(issue.is_overdue()),
                _bool_pl(bool(row_item["quick_close"])),
                issue.owner,
                issue.due_date,
            ]
            for col, val in enumerate(values):
                self.tbl_priority.setItem(row, col, QTableWidgetItem(str(val)))
        if self.tbl_priority.rowCount() > 0:
            self.tbl_priority.selectRow(0)

    def _populate_routes_table(self) -> None:
        self.tbl_routes.setRowCount(0)
        for row_data in self._route_rows:
            row = self.tbl_routes.rowCount()
            self.tbl_routes.insertRow(row)
            po_drodze = "TAK" if "po_drodze" in str(row_data.notes or "").lower() else "NIE"
            values = [
                row_data.planned_date,
                row_data.crew,
                row_data.route_group,
                row_data.project_name,
                row_data.client_name,
                row_data.city,
                row_data.address,
                row_data.task_type,
                row_data.notes[:80],
                str(int(row_data.estimated_time_minutes or 0)),
                f"{float(row_data.route_score or 0.0):.1f}",
                row_data.status,
                po_drodze,
                row_data.notes,
            ]
            for col, val in enumerate(values):
                self.tbl_routes.setItem(row, col, QTableWidgetItem(str(val)))
        if self.tbl_routes.rowCount() > 0:
            self.tbl_routes.selectRow(0)

    def _selected_priority_issue_id(self) -> str:
        model = self.tbl_priority.selectionModel()
        if model is None or not model.selectedRows():
            return ""
        row = int(model.selectedRows()[0].row())
        if row < 0 or row >= len(self._priority_rows):
            return ""
        return str(self._priority_rows[row]["issue"].id)

    def _selected_route(self):
        model = self.tbl_routes.selectionModel()
        if model is None or not model.selectedRows():
            return None
        row = int(model.selectedRows()[0].row())
        if row < 0 or row >= len(self._route_rows):
            return None
        return self._route_rows[row]

    def _on_create_route_from_selected_issue(self) -> None:
        issue_id = self._selected_priority_issue_id()
        if not issue_id:
            QMessageBox.information(self, "Priorytety i trasy", "Wybierz problem z tabeli priorytetow.")
            return
        planned_date = self.p_date.date().toString("yyyy-MM-dd")
        crew = self.p_crew.text().strip()
        if not crew:
            QMessageBox.information(self, "Priorytety i trasy", "Podaj ekipe.")
            return
        route_group = self.p_group.text().strip()
        created = self._store.create_route_task_from_issue(issue_id, planned_date, crew, route_group=route_group)
        if created is None:
            QMessageBox.warning(self, "Priorytety i trasy", "Nie udalo sie utworzyc trasy z tego problemu.")
            return
        self.refresh_data()
        self._notify_change()

    def _on_assign_route_group(self) -> None:
        route = self._selected_route()
        if route is None:
            QMessageBox.information(self, "Priorytety i trasy", "Wybierz trase do grupowania.")
            return
        value, ok = QInputDialog.getText(self, "Grupa trasy", "Nazwa grupy:", text=route.route_group)
        if not ok:
            return
        route.route_group = str(value or "").strip()
        self._store.update_route_task(route)
        self.refresh_data()
        self._notify_change()

    def _on_mark_route_done(self) -> None:
        route = self._selected_route()
        if route is None:
            QMessageBox.information(self, "Priorytety i trasy", "Wybierz trase.")
            return
        route.status = "wykonane"
        self._store.update_route_task(route)
        self.refresh_data()
        self._notify_change()
