from __future__ import annotations

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

from src.domain.assembly_models import FurnitureAssemblyDef
from src.storage.assembly_store_json import AssemblyStoreJson


def _clone_assembly(assembly: FurnitureAssemblyDef | None) -> FurnitureAssemblyDef | None:
    if assembly is None:
        return None
    return FurnitureAssemblyDef.from_dict(assembly.to_dict())


def _assembly_info_text(assembly: FurnitureAssemblyDef | None) -> str:
    if assembly is None:
        return "Brak wybranego kompletu."

    lines = [
        f'Nazwa: {getattr(assembly, "name", "") or ""}',
        f'Klient: {getattr(assembly, "client_name", "") or "-"}',
        f'Zamowienie: {getattr(assembly, "order_name", "") or "-"}',
        f'Pracownik: {getattr(assembly, "worker_name", "") or "-"}',
        f'Powiazana sciana: {getattr(assembly, "wall_name", "") or "-"}',
        f'Moduly: {len(getattr(assembly, "items", []) or [])}',
        f'Wymiary: {float(getattr(assembly, "width_mm", 0.0) or 0.0):.0f} x '
        f'{float(getattr(assembly, "height_mm", 0.0) or 0.0):.0f} x '
        f'{float(getattr(assembly, "depth_mm", 0.0) or 0.0):.0f} mm',
    ]
    return "\n".join(lines)


class LoadAssemblyDialog(QDialog):
    def __init__(self, parent: QWidget | None, store: AssemblyStoreJson) -> None:
        super().__init__(parent)
        self._store = store
        self._selected_name = ""
        self._selected_assembly: FurnitureAssemblyDef | None = None

        self.setWindowTitle("Wczytaj komplet")
        self.resize(820, 500)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        head = QLabel("Komplety zapisane w bazie")
        head.setStyleSheet("font-weight:700;")
        root.addWidget(head)

        self.tbl = QTableWidget(0, 6, self)
        self.tbl.setHorizontalHeaderLabels(["Nazwa", "Klient", "Zamowienie", "Pracownik", "Sciana", "Moduly"])
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.tbl, 1)

        manage_row = QHBoxLayout()
        self.btn_delete = QPushButton("Usun z bazy", self)
        self.btn_delete.setEnabled(False)
        self.lab_err = QLabel("", self)
        self.lab_err.setWordWrap(True)
        self.lab_err.setStyleSheet("color:#666666;")
        manage_row.addWidget(self.btn_delete, 0)
        manage_row.addWidget(self.lab_err, 1)
        root.addLayout(manage_row)

        self.info = QLabel("Brak wybranego kompletu.", self)
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
        return self._selected_name

    def selected_assembly(self) -> FurnitureAssemblyDef | None:
        return _clone_assembly(self._selected_assembly)

    def _reload(self) -> None:
        assemblies = self._store.list_assemblies() if hasattr(self._store, "list_assemblies") else []
        self.tbl.setRowCount(len(assemblies))

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
                item = QTableWidgetItem(value)
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, getattr(assembly, "name", ""))
                self.tbl.setItem(row, col, item)

        if self.tbl.rowCount() > 0:
            self.tbl.selectRow(0)
            self._on_pick(0, 0, -1, -1)
        else:
            self._selected_name = ""
            self._selected_assembly = None
            self.btn_delete.setEnabled(False)
            self.box_btns.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
            self.info.setText("Brak wybranego kompletu.")

    def _on_pick(self, current_row: int, _current_col: int, _prev_row: int, _prev_col: int) -> None:
        if current_row < 0 or current_row >= self.tbl.rowCount():
            self._selected_name = ""
            self._selected_assembly = None
            self.btn_delete.setEnabled(False)
            self.box_btns.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
            self.info.setText("Brak wybranego kompletu.")
            return

        item = self.tbl.item(current_row, 0)
        name = str(item.data(Qt.ItemDataRole.UserRole) or item.text() or "") if item is not None else ""
        self._selected_name = name
        self._selected_assembly = self._store.get(name) if name else None
        self.btn_delete.setEnabled(bool(self._selected_assembly))
        self.box_btns.button(QDialogButtonBox.StandardButton.Ok).setEnabled(bool(self._selected_assembly))
        self.info.setText(_assembly_info_text(self._selected_assembly))

    def _accept_current(self) -> None:
        if self._selected_assembly is None:
            return
        self.accept()

    def _confirm_delete(self, name: str) -> bool:
        answer = QMessageBox.question(
            self,
            "Usun komplet",
            f'Czy na pewno usunac komplet "{name}" z bazy...',
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
