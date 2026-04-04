from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.app.navigation_groups import GROUPS
from src.domain.permissions import ROLE_LABELS, can_access_tab_by_role, normalize_role
from src.storage.access_control_store_json import AccessControlStoreJson


def _all_tab_titles() -> list[str]:
    titles: list[str] = []
    seen: set[str] = set()
    for _group_name, tab_titles in GROUPS:
        for title in tab_titles:
            t = str(title or "").strip()
            if not t or t in seen:
                continue
            seen.add(t)
            titles.append(t)
    return titles


class TabUprawnienia(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._store = AccessControlStoreJson()
        self._current_worker = ""
        self._current_role = "produkcja"
        self._accounts: list[dict] = []
        self._tab_titles = _all_tab_titles()

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        title = QLabel("Tabela uprawnien")
        title.setStyleSheet("font-size:18px; font-weight:700;")
        root.addWidget(title)

        info = QLabel(
            "Admin (wlasciciel) moze nadawac i odbierac dostep do zakladek dla pozostalych osob. "
            "Wartosc odhaczona = dostep."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color:#666;")
        root.addWidget(info)

        self.tbl = QTableWidget(0, 1, self)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.verticalHeader().setVisible(False)
        root.addWidget(self.tbl, 1)

        row = QHBoxLayout()
        self.btn_reload = QPushButton("Wczytaj")
        self.btn_save = QPushButton("Zapisz uprawnienia")
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color:#666;")
        self.lbl_status.setWordWrap(True)
        row.addWidget(self.btn_reload)
        row.addWidget(self.btn_save)
        row.addStretch(1)
        root.addLayout(row)
        root.addWidget(self.lbl_status)

        self.btn_reload.clicked.connect(self.reload_data)
        self.btn_save.clicked.connect(self.save_changes)

        self.reload_data()

    def set_current_user(self, worker_name: str, role: str) -> None:
        self._current_worker = str(worker_name or "").strip()
        self._current_role = normalize_role(str(role or "produkcja"))
        self._apply_editability()

    def _is_admin(self) -> bool:
        return normalize_role(self._current_role) == "wlasciciel"

    def _set_status(self, text: str, ok: bool = True) -> None:
        self.lbl_status.setStyleSheet(f"color:{'#2b7a2b' if ok else '#a33'};")
        self.lbl_status.setText(str(text or ""))

    def _apply_editability(self) -> None:
        can_edit = self._is_admin()
        self.btn_save.setEnabled(can_edit)
        for row in range(self.tbl.rowCount()):
            for col in range(1, self.tbl.columnCount()):
                item = self.tbl.item(row, col)
                if item is None:
                    continue
                username = str(item.data(Qt.ItemDataRole.UserRole) or "").strip()
                if not can_edit or username.casefold() == "admin":
                    item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
                else:
                    item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEditable)
        if can_edit:
            self._set_status("Tryb admin: mozesz zmieniac dostepy.", ok=True)
        else:
            self._set_status("Tylko admin moze edytowac uprawnienia.", ok=False)

    def reload_data(self) -> None:
        self._accounts = self._store.list_accounts()
        headers = ["Zakladka"]
        for account in self._accounts:
            username = str(account.get("username", "") or "").strip()
            role = normalize_role(str(account.get("role", "") or "produkcja"))
            role_label = ROLE_LABELS.get(role, role)
            headers.append(f"{username} ({role_label})")

        self.tbl.clear()
        self.tbl.setColumnCount(len(headers))
        self.tbl.setHorizontalHeaderLabels(headers)
        self.tbl.setRowCount(len(self._tab_titles))

        for row, tab_title in enumerate(self._tab_titles):
            self.tbl.setItem(row, 0, QTableWidgetItem(tab_title))
            for col, account in enumerate(self._accounts, start=1):
                username = str(account.get("username", "") or "").strip()
                role = normalize_role(str(account.get("role", "") or "produkcja"))
                overrides = account.get("tab_overrides", {})
                override = overrides.get(tab_title) if isinstance(overrides, dict) else None
                default_access = can_access_tab_by_role(role, tab_title)
                current_access = bool(override) if isinstance(override, bool) else default_access

                item = QTableWidgetItem("")
                item.setData(Qt.ItemDataRole.UserRole, username)
                item.setData(Qt.ItemDataRole.UserRole + 1, tab_title)
                item.setData(Qt.ItemDataRole.UserRole + 2, default_access)
                item.setCheckState(Qt.CheckState.Checked if current_access else Qt.CheckState.Unchecked)
                self.tbl.setItem(row, col, item)

        self.tbl.resizeColumnsToContents()
        self._apply_editability()

    def save_changes(self) -> None:
        if not self._is_admin():
            self._set_status("Brak uprawnien do zapisu.", ok=False)
            return

        for col, account in enumerate(self._accounts, start=1):
            username = str(account.get("username", "") or "").strip()
            if not username or username.casefold() == "admin":
                continue
            overrides: dict[str, bool] = {}
            for row, tab_title in enumerate(self._tab_titles):
                item = self.tbl.item(row, col)
                if item is None:
                    continue
                checked = item.checkState() == Qt.CheckState.Checked
                default_access = bool(item.data(Qt.ItemDataRole.UserRole + 2))
                if checked != default_access:
                    overrides[tab_title] = checked
            self._store.set_tab_overrides(username, overrides)

        self._set_status("Zapisano uprawnienia.", ok=True)
        self.reload_data()
