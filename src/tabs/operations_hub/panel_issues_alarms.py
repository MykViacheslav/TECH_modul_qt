from __future__ import annotations

from datetime import date
from typing import Any, Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGridLayout,
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
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.core.operations_models import (
    AREA_VALUES,
    IMPACT_LEVEL_VALUES,
    ISSUE_TYPE_VALUES,
    PRIORITY_VALUES,
    STATUS_VALUES,
    IssueRecord,
)
from src.core.operations_store import OperationsStore


def _bool_pl(value: bool) -> str:
    return "TAK" if bool(value) else "NIE"


def _fmt_money(value: float) -> str:
    return f"{float(value or 0.0):.2f}"


class IssueEditDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, record: IssueRecord | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Problem i alarm")
        self.setModal(True)
        self.setMinimumWidth(640)
        self._record = record or IssueRecord()

        root = QVBoxLayout(self)
        form = QFormLayout()

        self.ed_title = QLineEdit(self)
        self.ed_project = QLineEdit(self)
        self.ed_client = QLineEdit(self)
        self.cb_area = QComboBox(self)
        for key, label in AREA_VALUES.items():
            self.cb_area.addItem(label, key)
        self.cb_type = QComboBox(self)
        for key, label in ISSUE_TYPE_VALUES.items():
            self.cb_type.addItem(label, key)
        self.cb_impact = QComboBox(self)
        for key, label in IMPACT_LEVEL_VALUES.items():
            self.cb_impact.addItem(label, key)
        self.cb_priority = QComboBox(self)
        for key, label in PRIORITY_VALUES.items():
            self.cb_priority.addItem(label, key)
        self.cb_status = QComboBox(self)
        for key, label in STATUS_VALUES.items():
            self.cb_status.addItem(label, key)
        self.ed_owner = QLineEdit(self)
        self.ed_due = QLineEdit(self)
        self.ed_due.setPlaceholderText("YYYY-MM-DD")
        self.ed_cost = QLineEdit(self)
        self.ed_unlock = QLineEdit(self)
        self.ed_minutes = QLineEdit(self)
        self.ed_city = QLineEdit(self)
        self.ed_address = QLineEdit(self)
        self.ed_tags = QLineEdit(self)
        self.ed_tags.setPlaceholderText("tag1,tag2")
        self.chk_invoice = QCheckBox("Blokuje fakture", self)
        self.chk_prod = QCheckBox("Blokuje produkcje", self)
        self.chk_install = QCheckBox("Blokuje montaz", self)
        self.txt_desc = QTextEdit(self)
        self.txt_notes = QTextEdit(self)

        form.addRow("Temat", self.ed_title)
        form.addRow("Projekt", self.ed_project)
        form.addRow("Klient", self.ed_client)
        form.addRow("Obszar", self.cb_area)
        form.addRow("Typ problemu", self.cb_type)
        form.addRow("Wplyw", self.cb_impact)
        form.addRow("Priorytet", self.cb_priority)
        form.addRow("Status", self.cb_status)
        form.addRow("Odpowiedzialny", self.ed_owner)
        form.addRow("Termin", self.ed_due)
        form.addRow("Szacowany koszt", self.ed_cost)
        form.addRow("Mozliwy odzysk przychodu", self.ed_unlock)
        form.addRow("Czas [min]", self.ed_minutes)
        form.addRow("Miasto", self.ed_city)
        form.addRow("Adres", self.ed_address)
        form.addRow("Tagi", self.ed_tags)
        form.addRow("", self.chk_invoice)
        form.addRow("", self.chk_prod)
        form.addRow("", self.chk_install)
        form.addRow("Opis", self.txt_desc)
        form.addRow("Notatki", self.txt_notes)
        root.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

        self._load()

    def _set_combo_data(self, combo: QComboBox, value: str) -> None:
        idx = combo.findData(str(value or "").strip().lower())
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _load(self) -> None:
        r = self._record
        self.ed_title.setText(r.title)
        self.ed_project.setText(r.project_name)
        self.ed_client.setText(r.client_name)
        self._set_combo_data(self.cb_area, r.area)
        self._set_combo_data(self.cb_type, r.issue_type)
        self._set_combo_data(self.cb_impact, r.impact_level)
        self._set_combo_data(self.cb_priority, r.priority_manual)
        self._set_combo_data(self.cb_status, r.status)
        self.ed_owner.setText(r.owner)
        self.ed_due.setText(r.due_date)
        self.ed_cost.setText(str(r.estimated_cost))
        self.ed_unlock.setText(str(r.estimated_revenue_unlock))
        self.ed_minutes.setText(str(r.estimated_time_minutes))
        self.ed_city.setText(r.city)
        self.ed_address.setText(r.address)
        self.ed_tags.setText(",".join(r.tags))
        self.chk_invoice.setChecked(r.blocks_invoice)
        self.chk_prod.setChecked(r.blocks_production)
        self.chk_install.setChecked(r.blocks_installation)
        self.txt_desc.setPlainText(r.description)
        self.txt_notes.setPlainText(r.notes)

    def get_record(self) -> IssueRecord:
        base = self._record
        base.title = self.ed_title.text().strip()
        base.project_name = self.ed_project.text().strip()
        base.client_name = self.ed_client.text().strip()
        base.area = str(self.cb_area.currentData() or "biuro")
        base.issue_type = str(self.cb_type.currentData() or "inne")
        base.impact_level = str(self.cb_impact.currentData() or "sredni")
        base.priority_manual = str(self.cb_priority.currentData() or "normalny")
        base.status = str(self.cb_status.currentData() or "nowe")
        base.owner = self.ed_owner.text().strip()
        base.due_date = self.ed_due.text().strip()
        base.blocks_invoice = self.chk_invoice.isChecked()
        base.blocks_production = self.chk_prod.isChecked()
        base.blocks_installation = self.chk_install.isChecked()
        try:
            base.estimated_cost = float(self.ed_cost.text().strip() or 0.0)
        except Exception:
            base.estimated_cost = 0.0
        try:
            base.estimated_revenue_unlock = float(self.ed_unlock.text().strip() or 0.0)
        except Exception:
            base.estimated_revenue_unlock = 0.0
        try:
            base.estimated_time_minutes = int(self.ed_minutes.text().strip() or 0)
        except Exception:
            base.estimated_time_minutes = 0
        base.city = self.ed_city.text().strip()
        base.address = self.ed_address.text().strip()
        base.tags = [x.strip() for x in self.ed_tags.text().split(",") if x.strip()]
        base.description = self.txt_desc.toPlainText().strip()
        base.notes = self.txt_notes.toPlainText().strip()
        return base


class IssuesAlarmsPanel(QWidget):
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
        self._visible: list[IssueRecord] = []
        self._id_col = 0
        self._finance_cols = [15, 16]

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        self._build_toolbar(root)
        self._build_filters(root)
        self._build_cards(root)
        self._build_main_content(root)
        self.refresh_data()

    def set_current_user(self, worker_name: str, role: str) -> None:
        self._worker_name = str(worker_name or "").strip()
        self._role = str(role or "").strip().lower()
        self._apply_role_visibility()
        self.refresh_data()

    def _notify_change(self) -> None:
        if callable(self._on_data_changed_cb):
            self._on_data_changed_cb()

    def _build_toolbar(self, root: QVBoxLayout) -> None:
        row = QHBoxLayout()
        self.btn_add = QPushButton("Dodaj problem", self)
        self.btn_edit = QPushButton("Edytuj", self)
        self.btn_close = QPushButton("Zamknij", self)
        self.btn_assign = QPushButton("Przypisz", self)
        self.btn_critical = QPushButton("Oznacz krytyczny", self)
        self.btn_note = QPushButton("Dodaj notatke", self)
        for btn in [self.btn_add, self.btn_edit, self.btn_close, self.btn_assign, self.btn_critical, self.btn_note]:
            row.addWidget(btn)
        row.addStretch(1)
        root.addLayout(row)

        self.btn_add.clicked.connect(self._on_add_issue)
        self.btn_edit.clicked.connect(self._on_edit_issue)
        self.btn_close.clicked.connect(self._on_close_issue)
        self.btn_assign.clicked.connect(self._on_assign_issue)
        self.btn_critical.clicked.connect(self._on_mark_critical)
        self.btn_note.clicked.connect(self._on_add_note)

    def _build_filters(self, root: QVBoxLayout) -> None:
        box = QFrame(self)
        lay = QGridLayout(box)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setHorizontalSpacing(8)
        lay.setVerticalSpacing(6)

        self.f_text = QLineEdit(self)
        self.f_status = QComboBox(self)
        self.f_priority = QComboBox(self)
        self.f_area = QComboBox(self)
        self.f_type = QComboBox(self)
        self.f_project = QLineEdit(self)
        self.f_client = QLineEdit(self)
        self.f_owner = QLineEdit(self)
        self.f_overdue = QCheckBox("Po terminie", self)
        self.f_blocks_invoice = QCheckBox("Blokuje fakture", self)
        self.f_blocks_production = QCheckBox("Blokuje produkcje", self)
        self.f_blocks_installation = QCheckBox("Blokuje montaz", self)
        self.f_active_only = QCheckBox("Tylko aktywne", self)
        self.f_active_only.setChecked(True)

        self.f_status.addItem("Wszystkie statusy", "all")
        for key, label in STATUS_VALUES.items():
            self.f_status.addItem(label, key)
        self.f_priority.addItem("Wszystkie priorytety", "all")
        for key, label in PRIORITY_VALUES.items():
            self.f_priority.addItem(label, key)
        self.f_area.addItem("Wszystkie obszary", "all")
        for key, label in AREA_VALUES.items():
            self.f_area.addItem(label, key)
        self.f_type.addItem("Wszystkie typy", "all")
        for key, label in ISSUE_TYPE_VALUES.items():
            self.f_type.addItem(label, key)

        self.f_text.setPlaceholderText("Szukaj...")
        self.f_project.setPlaceholderText("Projekt")
        self.f_client.setPlaceholderText("Klient")
        self.f_owner.setPlaceholderText("Odpowiedzialny")

        lay.addWidget(self.f_text, 0, 0, 1, 2)
        lay.addWidget(self.f_status, 0, 2)
        lay.addWidget(self.f_priority, 0, 3)
        lay.addWidget(self.f_area, 0, 4)
        lay.addWidget(self.f_type, 0, 5)
        lay.addWidget(self.f_project, 1, 0)
        lay.addWidget(self.f_client, 1, 1)
        lay.addWidget(self.f_owner, 1, 2)
        lay.addWidget(self.f_overdue, 1, 3)
        lay.addWidget(self.f_blocks_invoice, 1, 4)
        lay.addWidget(self.f_blocks_production, 1, 5)
        lay.addWidget(self.f_blocks_installation, 2, 0)
        lay.addWidget(self.f_active_only, 2, 1)
        root.addWidget(box)

        self._filter_widgets = [
            self.f_text,
            self.f_status,
            self.f_priority,
            self.f_area,
            self.f_type,
            self.f_project,
            self.f_client,
            self.f_owner,
            self.f_overdue,
            self.f_blocks_invoice,
            self.f_blocks_production,
            self.f_blocks_installation,
            self.f_active_only,
        ]
        for w in self._filter_widgets:
            if isinstance(w, QLineEdit):
                w.textChanged.connect(self.refresh_data)
            elif isinstance(w, QComboBox):
                w.currentIndexChanged.connect(self.refresh_data)
            elif isinstance(w, QCheckBox):
                w.stateChanged.connect(self.refresh_data)

    def _build_cards(self, root: QVBoxLayout) -> None:
        self.cards: dict[str, QLabel] = {}
        wrap = QFrame(self)
        lay = QGridLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setHorizontalSpacing(8)
        labels = [
            ("otwarte", "Otwarte"),
            ("krytyczne", "Krytyczne"),
            ("po_terminie", "Po terminie"),
            ("blokuje_fakture", "Blokuje fakture"),
            ("blokuje_produkcje", "Blokuje produkcje"),
            ("blokuje_montaz", "Blokuje montaz"),
            ("reklamacje", "Reklamacje"),
            ("do_decyzji", "Do decyzji"),
        ]
        for i, (key, title) in enumerate(labels):
            card = QFrame(wrap)
            card.setStyleSheet("QFrame{background:#f8fafc;border:1px solid #d7e1ef;border-radius:10px;}")
            c_l = QVBoxLayout(card)
            lab_t = QLabel(title, card)
            lab_v = QLabel("0", card)
            lab_t.setStyleSheet("font-size:11px;color:#475569;")
            lab_v.setStyleSheet("font-size:18px;font-weight:700;color:#0f172a;")
            c_l.addWidget(lab_t)
            c_l.addWidget(lab_v)
            lay.addWidget(card, i // 4, i % 4)
            self.cards[key] = lab_v
        root.addWidget(wrap)

    def _build_main_content(self, root: QVBoxLayout) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.tbl = QTableWidget(0, 17, self)
        self.tbl.setHorizontalHeaderLabels(
            [
                "ID",
                "Data zgloszenia",
                "Projekt",
                "Klient",
                "Obszar",
                "Typ",
                "Opis skrocony",
                "Wplyw",
                "Priorytet",
                "Status",
                "Odpowiedzialny",
                "Termin",
                "Blokuje fakture",
                "Blokuje produkcje",
                "Blokuje montaz",
                "Szacowany koszt",
                "Mozliwy odzysk przychodu",
            ]
        )
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        h = self.tbl.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        for col in [2, 3, 4, 5, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]:
            h.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        splitter.addWidget(self.tbl)

        details = QFrame(self)
        d_l = QVBoxLayout(details)
        d_l.setContentsMargins(8, 8, 8, 8)
        d_l.addWidget(QLabel("Szczegoly problemu", self))
        self.details = QTextEdit(self)
        self.details.setReadOnly(True)
        d_l.addWidget(self.details, 1)
        splitter.addWidget(details)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 2)
        root.addWidget(splitter, 1)

        self.tbl.itemSelectionChanged.connect(self._show_issue_details)
        self._apply_role_visibility()

    def _apply_role_visibility(self) -> None:
        hide_fin = self._role in {"produkcja", "magazyn", "montaz"}
        if hasattr(self, "tbl"):
            for col in self._finance_cols:
                self.tbl.setColumnHidden(col, hide_fin)

    def _read_filters(self) -> dict[str, Any]:
        return {
            "text": self.f_text.text().strip(),
            "status": str(self.f_status.currentData() or "all"),
            "priority": str(self.f_priority.currentData() or "all"),
            "area": str(self.f_area.currentData() or "all"),
            "issue_type": str(self.f_type.currentData() or "all"),
            "project": self.f_project.text().strip(),
            "client": self.f_client.text().strip(),
            "owner": self.f_owner.text().strip(),
            "overdue_only": self.f_overdue.isChecked(),
            "blocks_invoice": self.f_blocks_invoice.isChecked(),
            "blocks_production": self.f_blocks_production.isChecked(),
            "blocks_installation": self.f_blocks_installation.isChecked(),
            "active_only": self.f_active_only.isChecked(),
            "role": self._role,
            "worker_name": self._worker_name,
        }

    def refresh_data(self) -> None:
        self._visible = self._store.filter_issues(**self._read_filters())
        self._populate_table()
        kpis = self._store.get_issue_kpis(role=self._role, worker_name=self._worker_name)
        for key, widget in self.cards.items():
            widget.setText(str(kpis.get(key, 0)))

    def navigate_to_issue(
        self,
        issue_id: str | None = None,
        project_name: str = "",
        client_name: str = "",
    ) -> bool:
        wanted_id = str(issue_id or "").strip()
        wanted_project = str(project_name or "").strip().lower()
        wanted_client = str(client_name or "").strip().lower()
        self.refresh_data()
        idx = -1
        if wanted_id:
            for i, issue in enumerate(self._visible):
                if str(issue.id or "").strip() == wanted_id:
                    idx = i
                    break
        if idx < 0 and (wanted_project or wanted_client):
            for i, issue in enumerate(self._visible):
                project_ok = (not wanted_project) or (wanted_project in str(issue.project_name or "").lower())
                client_ok = (not wanted_client) or (wanted_client in str(issue.client_name or "").lower())
                if project_ok and client_ok:
                    idx = i
                    break
        if idx < 0:
            return False
        self.tbl.selectRow(idx)
        item = self.tbl.item(idx, 0)
        if item is not None:
            self.tbl.scrollToItem(item, QAbstractItemView.ScrollHint.PositionAtCenter)
        self._show_issue_details()
        return True

    def _populate_table(self) -> None:
        self.tbl.setRowCount(0)
        for issue in self._visible:
            row = self.tbl.rowCount()
            self.tbl.insertRow(row)
            values = [
                issue.id,
                issue.created_at,
                issue.project_name,
                issue.client_name,
                issue.area,
                issue.issue_type,
                (issue.description or issue.title)[:120],
                issue.impact_level,
                issue.priority_manual,
                issue.status,
                issue.owner,
                issue.due_date,
                _bool_pl(issue.blocks_invoice),
                _bool_pl(issue.blocks_production),
                _bool_pl(issue.blocks_installation),
                _fmt_money(issue.estimated_cost),
                _fmt_money(issue.estimated_revenue_unlock),
            ]
            for col, val in enumerate(values):
                self.tbl.setItem(row, col, QTableWidgetItem(str(val)))
        if self.tbl.rowCount() > 0:
            self.tbl.selectRow(0)
        else:
            self.details.clear()

    def _selected_issue(self) -> IssueRecord | None:
        model = self.tbl.selectionModel()
        if model is None or not model.selectedRows():
            return None
        row = int(model.selectedRows()[0].row())
        if row < 0 or row >= len(self._visible):
            return None
        return self._visible[row]

    def _show_issue_details(self) -> None:
        issue = self._selected_issue()
        if issue is None:
            self.details.clear()
            return
        lines = [
            f"ID: {issue.id}",
            f"Temat: {issue.title}",
            f"Projekt: {issue.project_name}",
            f"Klient: {issue.client_name}",
            f"Obszar: {issue.area}",
            f"Typ: {issue.issue_type}",
            f"Wplyw: {issue.impact_level}",
            f"Priorytet: {issue.priority_manual}",
            f"Status: {issue.status}",
            f"Odpowiedzialny: {issue.owner}",
            f"Termin: {issue.due_date}",
            f"Po terminie: {_bool_pl(issue.is_overdue())}",
            f"Blokuje fakture: {_bool_pl(issue.blocks_invoice)}",
            f"Blokuje produkcje: {_bool_pl(issue.blocks_production)}",
            f"Blokuje montaz: {_bool_pl(issue.blocks_installation)}",
            f"Szacowany koszt: {_fmt_money(issue.estimated_cost)}",
            f"Mozliwy odzysk: {_fmt_money(issue.estimated_revenue_unlock)}",
            f"Czas [min]: {issue.estimated_time_minutes}",
            f"Miasto/adres: {issue.city} / {issue.address}",
            f"Tagi: {', '.join(issue.tags)}",
            "",
            f"Opis: {issue.description}",
            "",
            f"Notatki: {issue.notes}",
        ]
        self.details.setPlainText("\n".join(lines))

    def _on_add_issue(self) -> None:
        dialog = IssueEditDialog(self, IssueRecord(due_date=date.today().strftime("%Y-%m-%d")))
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._store.add_issue(dialog.get_record())
        self.refresh_data()
        self._notify_change()

    def _on_edit_issue(self) -> None:
        issue = self._selected_issue()
        if issue is None:
            QMessageBox.information(self, "Problemy i alarmy", "Wybierz problem do edycji.")
            return
        dialog = IssueEditDialog(self, issue)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._store.update_issue(dialog.get_record())
        self.refresh_data()
        self._notify_change()

    def _on_close_issue(self) -> None:
        issue = self._selected_issue()
        if issue is None:
            QMessageBox.information(self, "Problemy i alarmy", "Wybierz problem do zamkniecia.")
            return
        self._store.close_issue(issue.id)
        self.refresh_data()
        self._notify_change()

    def _on_assign_issue(self) -> None:
        issue = self._selected_issue()
        if issue is None:
            QMessageBox.information(self, "Problemy i alarmy", "Wybierz problem do przypisania.")
            return
        owner, ok = QInputDialog.getText(self, "Przypisz", "Odpowiedzialny:", text=issue.owner)
        if not ok:
            return
        self._store.assign_issue(issue.id, owner)
        self.refresh_data()
        self._notify_change()

    def _on_mark_critical(self) -> None:
        issue = self._selected_issue()
        if issue is None:
            return
        issue.priority_manual = "krytyczny"
        self._store.update_issue(issue)
        self.refresh_data()
        self._notify_change()

    def _on_add_note(self) -> None:
        issue = self._selected_issue()
        if issue is None:
            QMessageBox.information(self, "Problemy i alarmy", "Wybierz problem do notatki.")
            return
        note, ok = QInputDialog.getMultiLineText(self, "Dodaj notatke", "Notatka:")
        if not ok or not str(note or "").strip():
            return
        prefix = issue.notes.strip()
        issue.notes = f"{prefix}\n{note.strip()}".strip()
        self._store.update_issue(issue)
        self.refresh_data()
        self._notify_change()
