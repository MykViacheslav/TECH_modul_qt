from __future__ import annotations
from datetime import date
from typing import Any, Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

class ScheduleTable(QFrame):
    """
    Nowoczesna tabela harmonogramu projektu.
    Pozwala wyświetlać i zarządzać etapami prac (od-do).
    """
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("uiCard", "true")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.table = QTableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Etap / Faza", "Data od", "Data do", "Notatki"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setStyleSheet("border: none; background: transparent;")
        
        layout.addWidget(self.table)
        
        self._data: list[dict[str, Any]] = []

    def set_schedule(self, data: list[dict[str, Any]]) -> None:
        self._data = data
        self.table.setRowCount(len(data))
        for row, item in enumerate(data):
            self.table.setItem(row, 0, QTableWidgetItem(str(item.get("stage", ""))))
            self.table.setItem(row, 1, QTableWidgetItem(str(item.get("date_start", ""))))
            self.table.setItem(row, 2, QTableWidgetItem(str(item.get("date_end", ""))))
            self.table.setItem(row, 3, QTableWidgetItem(str(item.get("note", ""))))

    def get_schedule(self) -> list[dict[str, Any]]:
        return self._data

    def add_entry(self, stage: str, d_start: str, d_end: str, note: str) -> None:
        entry = {
            "stage": stage,
            "date_start": d_start,
            "date_end": d_end,
            "note": note
        }
        self._data.append(entry)
        self.set_schedule(self._data)
