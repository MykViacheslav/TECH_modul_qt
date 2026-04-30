from __future__ import annotations
from typing import Any, List, Dict
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, 
    QTableWidgetItem, QPushButton, QDoubleSpinBox, QComboBox,
    QHeaderView, QMessageBox, QFrame, QAbstractItemView
)
from PyQt6.QtCore import Qt

from src.services.material_advanced_service import MaterialAdvancedService
from src.services.invoice_pdf_import_service import InvoiceParseResult

class InvoiceImportDialog(QDialog):
    def __init__(self, parse_result: InvoiceParseResult, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Import Faktury: {parse_result.supplier} ({parse_result.invoice_number})")
        self.resize(1100, 700)
        
        self._result = parse_result
        self._service = MaterialAdvancedService()
        
        layout = QVBoxLayout(self)
        
        # Header Info
        hdr = QFrame()
        hdr.setStyleSheet("background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 10px;")
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.addWidget(QLabel(f"<b>Dostawca:</b> {parse_result.supplier}"))
        hdr_lay.addWidget(QLabel(f"<b>Nr:</b> {parse_result.invoice_number}"))
        hdr_lay.addWidget(QLabel(f"<b>Data:</b> {parse_result.invoice_date}"))
        hdr_lay.addStretch()
        layout.addWidget(hdr)
        
        # Discount and Warehouse Globally
        ctrl_row = QHBoxLayout()
        ctrl_row.addWidget(QLabel("Globalna zniżka [%]:"))
        self.sp_discount = QDoubleSpinBox()
        self.sp_discount.setRange(0, 100)
        self.sp_discount.setSuffix(" %")
        self.sp_discount.valueChanged.connect(self._refresh_table)
        ctrl_row.addWidget(self.sp_discount)
        
        ctrl_row.addWidget(QLabel("Magazyn:"))
        self.cb_warehouse = QComboBox()
        self.cb_warehouse.addItems(self._service.get_warehouse_types())
        ctrl_row.addWidget(self.cb_warehouse)
        ctrl_row.addStretch()
        layout.addWidget(QFrame()) # spacer
        layout.addLayout(ctrl_row)

        # Table
        self.tbl = QTableWidget(0, 7)
        self.tbl.setHorizontalHeaderLabels([
            "Produkt", "Ilość", "Jdn", "Cena Netto", "Po Rabacie", "Porównanie", "Status"
        ])
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        h = self.tbl.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tbl)
        
        # Summary
        self.lab_summary = QLabel("Łącznie: 0.00 zł")
        self.lab_summary.setStyleSheet("font-weight: 800; font-size: 14px;")
        layout.addWidget(self.lab_summary, 0, Qt.AlignmentFlag.AlignRight)
        
        # Buttons
        btns = QHBoxLayout()
        self.btn_import = QPushButton("Importuj do bazy")
        self.btn_import.setStyleSheet("background: #1d4ed8; color: white; padding: 8px 16px; font-weight: 800; border-radius: 8px;")
        self.btn_cancel = QPushButton("Anuluj")
        btns.addStretch()
        btns.addWidget(self.btn_cancel)
        btns.addWidget(self.btn_import)
        layout.addLayout(btns)
        
        self.btn_import.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)
        
        self._refresh_table()

    def _refresh_table(self):
        self.tbl.setRowCount(0)
        discount = self.sp_discount.value() / 100.0
        total_after = 0.0
        
        for item in self._result.items:
            row = self.tbl.rowCount()
            self.tbl.insertRow(row)
            
            # 1. Name
            self.tbl.setItem(row, 0, QTableWidgetItem(item.name))
            # 2. Qty
            self.tbl.setItem(row, 1, QTableWidgetItem(f"{item.quantity:.2f}"))
            # 3. Unit
            self.tbl.setItem(row, 2, QTableWidgetItem(item.unit or "-"))
            # 4. Net Price
            price_net = float(getattr(item, "unit_price_net", 0.0) or 0.0)
            self.tbl.setItem(row, 3, QTableWidgetItem(f"{price_net:.2f}"))
            # 5. After Discount
            after_price = price_net * (1.0 - discount)
            self.tbl.setItem(row, 4, QTableWidgetItem(f"{after_price:.2f}"))
            
            # 6. Comparison
            comp = self._service.compare_prices(item.name, after_price)
            comp_item = QTableWidgetItem()
            if comp["status"] == "new":
                comp_item.setText("Nowość")
                comp_item.setForeground(Qt.GlobalColor.darkBlue)
            elif comp["status"] == "more_expensive":
                comp_item.setText(f"▲ {comp['diff_percent']}% (było {comp['last_price']:.2f})")
                comp_item.setForeground(Qt.GlobalColor.red)
            elif comp["status"] == "cheaper":
                comp_item.setText(f"▼ {abs(comp['diff_percent'])}% (było {comp['last_price']:.2f})")
                comp_item.setForeground(Qt.GlobalColor.darkGreen)
            else:
                comp_item.setText(f"OK ({comp['last_price']:.2f})")
                comp_item.setForeground(Qt.GlobalColor.gray)
            
            self.tbl.setItem(row, 5, comp_item)
            
            # Status / Logic
            self.tbl.setItem(row, 6, QTableWidgetItem("Gotowy"))
            
            total_after += after_price * item.quantity

        self.lab_summary.setText(f"Łącznie po rabacie: {total_after:.2f} PLN")

    def get_import_settings(self) -> Dict[str, Any]:
        return {
            "discount_percent": self.sp_discount.value(),
            "warehouse": self.cb_warehouse.currentText()
        }
