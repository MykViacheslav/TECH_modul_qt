from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QDoubleSpinBox,
)

from src.app.app_settings import load_drawing_settings
from src.domain.assembly_resolution_service import resolve_assembly_items
from src.storage.assembly_store_json import AssemblyStoreJson
from src.storage.catalog_store_json import CatalogStoreJson
from src.storage.order_store_json import OrderStoreJson
from src.storage.wall_store_json import WallStoreJson


class TabWycena(QWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
        assembly_store: AssemblyStoreJson | None = None,
        order_store: OrderStoreJson | None = None,
        wall_store: WallStoreJson | None = None,
        catalog: CatalogStoreJson | None = None,
    ) -> None:
        super().__init__(parent)
        self._assembly_store = assembly_store if assembly_store is not None else AssemblyStoreJson()
        self._order_store = order_store if order_store is not None else OrderStoreJson()
        self._wall_store = wall_store if wall_store is not None else WallStoreJson()
        self._catalog = catalog if catalog is not None else CatalogStoreJson()
        self._rows: list[dict[str, object]] = []
        self._is_loading = False

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        title = QLabel("WYCENA")
        title.setStyleSheet("font-size: 22px; font-weight: 800; letter-spacing: 0.5px;")
        root.addWidget(title, 0, Qt.AlignmentFlag.AlignLeft)

        subtitle = QLabel(
            "Osobna karta handlowa dla kompletow. Tutaj liczysz robocizne, transport, montaz i marze bez obciazania karty Komplet."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color:#555555;")
        root.addWidget(subtitle, 0, Qt.AlignmentFlag.AlignLeft)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        self.card_count = self._make_metric_card("Komplety", "0")
        self.card_tech = self._make_metric_card("Koszt techniczny", "0.00 zl")
        self.card_sale = self._make_metric_card("Cena handlowa", "0.00 zl")
        self.card_profit = self._make_metric_card("Marza", "0.00 zl")
        for widget in (self.card_count, self.card_tech, self.card_sale, self.card_profit):
            stats_row.addWidget(widget)
        stats_row.addStretch(1)
        root.addLayout(stats_row)

        filters = QHBoxLayout()
        filters.setSpacing(10)
        self.ed_search = QLineEdit(self)
        self.ed_search.setPlaceholderText("Szukaj po komplecie, kliencie albo zamowieniu...")
        self.cb_order = QComboBox(self)
        self.cb_order.addItem("Wszystkie zamowienia", "")
        self.btn_refresh = QPushButton("Odswiez", self)
        filters.addWidget(QLabel("Szukaj:", self))
        filters.addWidget(self.ed_search, 1)
        filters.addWidget(QLabel("Zamowienie:", self))
        filters.addWidget(self.cb_order, 0)
        filters.addWidget(self.btn_refresh, 0)
        root.addLayout(filters)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        root.addWidget(splitter, 1)

        left = QWidget(splitter)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)
        self.tbl_assemblies = QTableWidget(0, 7, left)
        self.tbl_assemblies.setHorizontalHeaderLabels(
            ["Komplet", "Zamowienie", "Klient", "Techn.", "Robocizna", "Marza %", "Handlowa"]
        )
        self.tbl_assemblies.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_assemblies.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tbl_assemblies.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_assemblies.setAlternatingRowColors(True)
        self.tbl_assemblies.verticalHeader().setVisible(False)
        header = self.tbl_assemblies.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        left_layout.addWidget(self.tbl_assemblies, 1)
        splitter.addWidget(left)

        right = QWidget(splitter)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        editor = QFrame(right)
        editor.setStyleSheet("QFrame { border: 1px solid #d9e0ea; border-radius: 8px; background: #fbfcfe; }")
        editor_layout = QVBoxLayout(editor)
        editor_layout.setContentsMargins(12, 12, 12, 12)
        editor_layout.setSpacing(10)

        editor_title = QLabel("Kalkulacja kompletu", editor)
        editor_title.setStyleSheet("font-weight: 700;")
        editor_layout.addWidget(editor_title)

        self.lab_selected = QLabel("Wybierz komplet z listy.", editor)
        self.lab_selected.setWordWrap(True)
        editor_layout.addWidget(self.lab_selected)

        form = QFormLayout()
        self.sp_labor = QDoubleSpinBox(editor)
        self.sp_labor.setRange(0.0, 1000000.0)
        self.sp_labor.setDecimals(2)
        self.sp_labor.setSuffix(" zl")
        self.sp_transport = QDoubleSpinBox(editor)
        self.sp_transport.setRange(0.0, 1000000.0)
        self.sp_transport.setDecimals(2)
        self.sp_transport.setSuffix(" zl")
        self.sp_montage = QDoubleSpinBox(editor)
        self.sp_montage.setRange(0.0, 1000000.0)
        self.sp_montage.setDecimals(2)
        self.sp_montage.setSuffix(" zl")
        self.sp_margin = QDoubleSpinBox(editor)
        self.sp_margin.setRange(0.0, 500.0)
        self.sp_margin.setDecimals(1)
        self.sp_margin.setSuffix(" %")
        self.lab_base_total = QLabel("0.00 zl", editor)
        self.lab_base_total.setStyleSheet("font-weight:600; color:#374151;")
        self.lab_sale_total = QLabel("0.00 zl", editor)
        self.lab_sale_total.setStyleSheet("font-weight:700; color:#2f241b;")
        self.lab_profit_total = QLabel("0.00 zl", editor)
        self.lab_profit_total.setStyleSheet("font-weight:600; color:#6b5d4d;")
        form.addRow("Robocizna", self.sp_labor)
        form.addRow("Transport", self.sp_transport)
        form.addRow("Montaz", self.sp_montage)
        form.addRow("Marza", self.sp_margin)
        form.addRow("Koszt bazowy", self.lab_base_total)
        form.addRow("Cena handlowa", self.lab_sale_total)
        form.addRow("Narost", self.lab_profit_total)
        editor_layout.addLayout(form)

        actions = QHBoxLayout()
        self.btn_save = QPushButton("Zapisz wycene", editor)
        self.btn_clear = QPushButton("Wyczysc dodatki", editor)
        actions.addWidget(self.btn_save, 0)
        actions.addWidget(self.btn_clear, 0)
        actions.addStretch(1)
        editor_layout.addLayout(actions)

        self.lab_status = QLabel("", editor)
        self.lab_status.setWordWrap(True)
        editor_layout.addWidget(self.lab_status)
        right_layout.addWidget(editor, 0)

        order_box = QFrame(right)
        order_box.setStyleSheet("QFrame { border: 1px solid #d9e0ea; border-radius: 8px; background: #ffffff; }")
        order_layout = QFormLayout(order_box)
        order_layout.setContentsMargins(12, 12, 12, 12)
        self.lab_order_tech = QLabel("0.00 zl", order_box)
        self.lab_order_sale = QLabel("0.00 zl", order_box)
        self.lab_order_profit = QLabel("0.00 zl", order_box)
        order_layout.addRow("Koszt techniczny", self.lab_order_tech)
        order_layout.addRow("Cena handlowa", self.lab_order_sale)
        order_layout.addRow("Marza kwotowo", self.lab_order_profit)
        right_layout.addWidget(order_box, 0)
        right_layout.addStretch(1)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        self.ed_search.textChanged.connect(self._refresh_table)
        self.cb_order.currentIndexChanged.connect(self._refresh_table)
        self.btn_refresh.clicked.connect(self.refresh_data)
        self.tbl_assemblies.itemSelectionChanged.connect(self._on_selection_changed)
        self.btn_save.clicked.connect(self._on_save)
        self.btn_clear.clicked.connect(self._on_clear)
        self.sp_labor.valueChanged.connect(self._refresh_editor_totals)
        self.sp_transport.valueChanged.connect(self._refresh_editor_totals)
        self.sp_montage.valueChanged.connect(self._refresh_editor_totals)
        self.sp_margin.valueChanged.connect(self._refresh_editor_totals)

        self.refresh_data()

    def _make_metric_card(self, title: str, value: str) -> QFrame:
        frame = QFrame(self)
        frame.setStyleSheet("QFrame { border: 1px solid #d8e2ec; border-radius: 10px; background: #ffffff; }")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)
        lab_title = QLabel(title, frame)
        lab_title.setStyleSheet("color:#64748b; font-weight:600;")
        lab_value = QLabel(value, frame)
        lab_value.setStyleSheet("font-size: 18px; font-weight: 800; color:#0f172a;")
        lab_value.setObjectName("metricValue")
        layout.addWidget(lab_title)
        layout.addWidget(lab_value)
        frame.metric_value = lab_value  # type: ignore[attr-defined]
        return frame

    def _set_metric(self, frame: QFrame, value: str) -> None:
        label = getattr(frame, "metric_value", None)
        if isinstance(label, QLabel):
            label.setText(value)

    def _selected_name(self) -> str:
        rows = self.tbl_assemblies.selectionModel().selectedRows() if self.tbl_assemblies.selectionModel() is not None else []
        if not rows:
            return ""
        item = self.tbl_assemblies.item(int(rows[0].row()), 0)
        if item is None:
            return ""
        return str(item.data(Qt.ItemDataRole.UserRole) or "").strip()

    def _compute_totals(self, assembly) -> tuple[float, float, float, float]:
        auto_double_width = float(load_drawing_settings().auto_double_front_width_mm or 600.0)
        linked_wall = None
        wall_name = str(getattr(assembly, "wall_name", "") or "").strip()
        if wall_name:
            linked_wall = self._wall_store.get(wall_name)
        resolved_items = resolve_assembly_items(
            assembly,
            self._catalog,
            auto_double_front_width_mm=auto_double_width,
            linked_wall=linked_wall,
        )
        technical_total = sum(item.cost_breakdown.grand_total_pln for item in resolved_items)
        base_total = assembly.commercial_base_total(technical_total)
        sale_total = assembly.commercial_sale_total(technical_total)
        profit_total = sale_total - base_total
        return technical_total, base_total, sale_total, profit_total

    def refresh_data(self) -> None:
        assemblies = self._assembly_store.list_assemblies()
        orders = sorted({str(getattr(item, "order_name", "") or "").strip() for item in assemblies if str(getattr(item, "order_name", "") or "").strip()})
        current_order = str(self.cb_order.currentData() or "").strip()
        self.cb_order.blockSignals(True)
        try:
            self.cb_order.clear()
            self.cb_order.addItem("Wszystkie zamowienia", "")
            for order_name in orders:
                self.cb_order.addItem(order_name, order_name)
            idx = self.cb_order.findData(current_order)
            self.cb_order.setCurrentIndex(idx if idx >= 0 else 0)
        finally:
            self.cb_order.blockSignals(False)
        self._refresh_table()

    def _filtered_rows(self) -> list[dict[str, object]]:
        search = self.ed_search.text().strip().lower()
        order_filter = str(self.cb_order.currentData() or "").strip()
        rows: list[dict[str, object]] = []
        for assembly in self._assembly_store.list_assemblies():
            order_name = str(getattr(assembly, "order_name", "") or "").strip()
            if order_filter and order_name != order_filter:
                continue
            haystack = " ".join(
                [
                    str(getattr(assembly, "name", "") or ""),
                    str(getattr(assembly, "client_name", "") or ""),
                    order_name,
                    str(getattr(assembly, "worker_name", "") or ""),
                ]
            ).lower()
            if search and search not in haystack:
                continue
            technical_total, base_total, sale_total, profit_total = self._compute_totals(assembly)
            rows.append(
                {
                    "assembly": assembly,
                    "technical_total": technical_total,
                    "base_total": base_total,
                    "sale_total": sale_total,
                    "profit_total": profit_total,
                }
            )
        return rows

    def _refresh_table(self) -> None:
        current_name = self._selected_name()
        self._rows = self._filtered_rows()
        self.tbl_assemblies.setRowCount(0)
        total_tech = 0.0
        total_sale = 0.0
        total_profit = 0.0
        for row_idx, row in enumerate(self._rows):
            assembly = row["assembly"]
            technical_total = float(row["technical_total"])
            sale_total = float(row["sale_total"])
            profit_total = float(row["profit_total"])
            total_tech += technical_total
            total_sale += sale_total
            total_profit += profit_total
            self.tbl_assemblies.insertRow(row_idx)
            values = [
                str(getattr(assembly, "name", "") or "-"),
                str(getattr(assembly, "order_name", "") or "-"),
                str(getattr(assembly, "client_name", "") or "-"),
                f"{technical_total:.2f} zl",
                f"{float(getattr(assembly, 'labor_cost_pln', 0.0) or 0.0):.2f} zl",
                f"{float(getattr(assembly, 'margin_percent', 0.0) or 0.0):.1f} %",
                f"{sale_total:.2f} zl",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, str(getattr(assembly, "name", "") or ""))
                self.tbl_assemblies.setItem(row_idx, col, item)
        self._set_metric(self.card_count, str(len(self._rows)))
        self._set_metric(self.card_tech, f"{total_tech:.2f} zl")
        self._set_metric(self.card_sale, f"{total_sale:.2f} zl")
        self._set_metric(self.card_profit, f"{total_profit:.2f} zl")
        self.lab_order_tech.setText(f"{total_tech:.2f} zl")
        self.lab_order_sale.setText(f"{total_sale:.2f} zl")
        self.lab_order_profit.setText(f"{total_profit:.2f} zl")
        if current_name:
            for row in range(self.tbl_assemblies.rowCount()):
                item = self.tbl_assemblies.item(row, 0)
                if item is not None and str(item.data(Qt.ItemDataRole.UserRole) or "") == current_name:
                    self.tbl_assemblies.selectRow(row)
                    break
        self._on_selection_changed()

    def _selected_assembly(self):
        name = self._selected_name()
        return self._assembly_store.get(name) if name else None

    def _on_selection_changed(self) -> None:
        assembly = self._selected_assembly()
        self._is_loading = True
        try:
            if assembly is None:
                self.lab_selected.setText("Wybierz komplet z listy.")
                self.sp_labor.setValue(0.0)
                self.sp_transport.setValue(0.0)
                self.sp_montage.setValue(0.0)
                self.sp_margin.setValue(0.0)
                self.lab_base_total.setText("0.00 zl")
                self.lab_sale_total.setText("0.00 zl")
                self.lab_profit_total.setText("0.00 zl")
                return
            self.lab_selected.setText(
                f'Komplet: {assembly.name} | Zamowienie: {assembly.order_name or "-"} | Klient: {assembly.client_name or "-"}'
            )
            self.sp_labor.setValue(float(getattr(assembly, "labor_cost_pln", 0.0) or 0.0))
            self.sp_transport.setValue(float(getattr(assembly, "transport_cost_pln", 0.0) or 0.0))
            self.sp_montage.setValue(float(getattr(assembly, "montage_cost_pln", 0.0) or 0.0))
            self.sp_margin.setValue(float(getattr(assembly, "margin_percent", 0.0) or 0.0))
            self._refresh_editor_totals()
        finally:
            self._is_loading = False

    def _refresh_editor_totals(self) -> None:
        if self._is_loading:
            return
        assembly = self._selected_assembly()
        if assembly is None:
            self.lab_base_total.setText("0.00 zl")
            self.lab_sale_total.setText("0.00 zl")
            self.lab_profit_total.setText("0.00 zl")
            return
        technical_total, _base_total, _sale_total, _profit_total = self._compute_totals(assembly)
        base_total = technical_total + float(self.sp_labor.value()) + float(self.sp_transport.value()) + float(self.sp_montage.value())
        sale_total = base_total * (1.0 + (float(self.sp_margin.value()) / 100.0))
        profit_total = sale_total - base_total
        self.lab_base_total.setText(f"{base_total:.2f} zl")
        self.lab_sale_total.setText(f"{sale_total:.2f} zl")
        self.lab_profit_total.setText(f"{profit_total:.2f} zl")

    def _on_save(self) -> None:
        assembly = self._selected_assembly()
        if assembly is None:
            self._set_status("Wybierz komplet z listy.", ok=False)
            return
        assembly.labor_cost_pln = float(self.sp_labor.value())
        assembly.transport_cost_pln = float(self.sp_transport.value())
        assembly.montage_cost_pln = float(self.sp_montage.value())
        assembly.margin_percent = float(self.sp_margin.value())
        result = self._assembly_store.overwrite(assembly)
        self._refresh_table()
        self._set_status(result.message_pl, ok=result.ok)

    def _on_clear(self) -> None:
        assembly = self._selected_assembly()
        if assembly is None:
            self._set_status("Wybierz komplet z listy.", ok=False)
            return
        assembly.labor_cost_pln = 0.0
        assembly.transport_cost_pln = 0.0
        assembly.montage_cost_pln = 0.0
        assembly.margin_percent = 0.0
        result = self._assembly_store.overwrite(assembly)
        self._refresh_table()
        self._set_status("Wyczyszczono kalkulacje handlowa." if result.ok else result.message_pl, ok=result.ok)

    def _set_status(self, message: str, ok: bool) -> None:
        color = "#2d6a4f" if ok else "#b42318"
        self.lab_status.setStyleSheet(f"color:{color};")
        self.lab_status.setText(str(message or ""))
