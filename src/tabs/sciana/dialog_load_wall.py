from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.domain.wall_models import WallLayoutDef
from src.storage.wall_store_json import WallStoreJson
from src.ui.theme_utils import get_muted_color


def _clone_wall(wall: WallLayoutDef | None) -> WallLayoutDef | None:
    if wall is None:
        return None
    return WallLayoutDef.from_dict(wall.to_dict())


def _wall_info_text(wall: WallLayoutDef | None) -> str:
    if wall is None:
        return "Brak wybranej sciany."

    lines = [
        f'Nazwa: {getattr(wall, "name", "") or ""}',
        f'Klient: {getattr(wall, "client_name", "") or "-"}',
        f'Zamówienie: {getattr(wall, "order_name", "") or "-"}',
        f'Typ ukladu: {getattr(wall, "layout_type", "") or "line"}',
        f'Widok z przodu: {getattr(wall, "front_view_wall_side", "") or "A"}',
        f'Przeszkody: {len(getattr(wall, "obstacles", []) or [])}',
        f'Zdjecia: {len(getattr(wall, "photos", []) or [])}',
    ]
    return "\n".join(lines)


class LoadWallDialog(QDialog):
    def __init__(self, parent: QWidget | None, store: WallStoreJson) -> None:
        super().__init__(parent)
        self._store = store
        self._selected_wall_name = ""
        self._selected_wall: WallLayoutDef | None = None

        self.setWindowTitle("Wczytaj sciane")
        self.resize(760, 480)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        head = QLabel("Sciany zapisane w bazie")
        head.setStyleSheet("font-weight:700;")
        root.addWidget(head)

        self.tbl = QTableWidget(0, 5, self)
        self.tbl.setHorizontalHeaderLabels(["Nazwa", "Klient", "Zamówienie", "Typ", "Przeszkody"])
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.tbl, 1)

        manage_row = QHBoxLayout()
        self.btn_delete = QPushButton("Usuń z bazy", self)
        self.btn_delete.setEnabled(False)
        self.lab_err = QLabel("", self)
        self.lab_err.setWordWrap(True)
        self.lab_err.setStyleSheet(f"color:{get_muted_color()};")
        manage_row.addWidget(self.btn_delete, 0)
        manage_row.addWidget(self.lab_err, 1)
        root.addLayout(manage_row)

        self.info = QLabel("Brak wybranej sciany.", self)
        self.info.setWordWrap(True)
        self.info.setStyleSheet("color:#333333;")
        root.addWidget(self.info)

        self.box_btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            Qt.Orientation.Horizontal,
            self,
        )
        self.box_btns.button(QDialogButtonBox.StandardButton.Ok).setText("Wczytaj")
        self.box_btns.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        root.addWidget(self.box_btns)

        self.tbl.currentCellChanged.connect(self._on_pick)
        self.tbl.itemDoubleClicked.connect(lambda _item: self._accept_current())
        self.btn_delete.clicked.connect(self._delete_current)
        self.box_btns.accepted.connect(self._accept_current)
        self.box_btns.rejected.connect(self.reject)

        self._reload()

    def selected_name(self) -> str:
        return self._selected_wall_name

    def selected_wall(self) -> WallLayoutDef | None:
        return _clone_wall(self._selected_wall)

    def _reload(self) -> None:
        layouts = self._store.list_layouts() if hasattr(self._store, "list_layouts") else []
        self.tbl.setRowCount(len(layouts))

        for row, wall in enumerate(layouts):
            values = [
                str(getattr(wall, "name", "") or ""),
                str(getattr(wall, "client_name", "") or "-"),
                str(getattr(wall, "order_name", "") or "-"),
                str(getattr(wall, "layout_type", "") or "line"),
                str(len(getattr(wall, "obstacles", []) or [])),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, getattr(wall, "name", ""))
                self.tbl.setItem(row, col, item)

        if self.tbl.rowCount() > 0:
            self.tbl.selectRow(0)
            self._on_pick(0, 0, -1, -1)
        else:
            self._selected_wall_name = ""
            self._selected_wall = None
            self.btn_delete.setEnabled(False)
            self.box_btns.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
            self.info.setText("Brak wybranej sciany.")

    def _on_pick(self, current_row: int, _current_col: int, _prev_row: int, _prev_col: int) -> None:
        if current_row < 0 or current_row >= self.tbl.rowCount():
            self._selected_wall_name = ""
            self._selected_wall = None
            self.btn_delete.setEnabled(False)
            self.box_btns.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
            self.info.setText("Brak wybranej sciany.")
            return

        item = self.tbl.item(current_row, 0)
        name = str(item.data(Qt.ItemDataRole.UserRole) or item.text() or "") if item is not None else ""
        self._selected_wall_name = name
        self._selected_wall = self._store.get(name) if name else None
        self.btn_delete.setEnabled(bool(self._selected_wall))
        self.box_btns.button(QDialogButtonBox.StandardButton.Ok).setEnabled(bool(self._selected_wall))
        self.info.setText(_wall_info_text(self._selected_wall))

    def _accept_current(self) -> None:
        if self._selected_wall is None:
            return
        self.accept()

    def _confirm_delete(self, name: str) -> bool:
        answer = QMessageBox.question(
            self,
            "Usuń ścianę",
            f'Czy na pewno usunąć ścianę "{name}" z bazy...',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _delete_current(self) -> None:
        name = self.selected_name()
        if not name:
            return
        if not self._confirm_delete(name):
            return

        result = self._store.delete(name)
        self.lab_err.setText(result.message_pl)
        self.lab_err.setStyleSheet("color:#0f6a2f;" if result.ok else "color:#a61b1b;")
        self._reload()
