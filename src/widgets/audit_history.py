"""
Audit history widget for displaying change history.
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QGroupBox,
)

from src.services.audit_log import AuditLog, AuditEntry, get_audit_log, AuditAction


class AuditHistoryWidget(QWidget):
    """Widget for displaying audit history of an entity."""
    
    sig_refresh_requested = pyqtSignal()
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._entity_type = ""
        self._entity_id = ""
        self._audit_log = get_audit_log()
        
        self._build_ui()
    
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Header
        header = QHBoxLayout()
        
        title = QLabel("Historia zmian")
        title.setStyleSheet("font-weight: bold; font-size: 12px;")
        header.addWidget(title)
        
        header.addStretch()
        
        self.btn_refresh = QPushButton("Odswiez")
        self.btn_refresh.setFixedHeight(24)
        self.btn_refresh.clicked.connect(self._refresh)
        header.addWidget(self.btn_refresh)
        
        self.btn_export = QPushButton("Eksport")
        self.btn_export.setFixedHeight(24)
        self.btn_export.clicked.connect(self._export)
        header.addWidget(self.btn_export)
        
        layout.addLayout(header)
        
        # Filter
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Filtr:"))
        
        self.cb_filter = QComboBox()
        self.cb_filter.addItem("Wszystkie", "")
        for action in AuditAction:
            self.cb_filter.addItem(action.value, action.value)
        self.cb_filter.currentIndexChanged.connect(self._refresh)
        filter_row.addWidget(self.cb_filter)
        
        filter_row.addStretch()
        layout.addLayout(filter_row)
        
        # History list
        self.history_list = QListWidget()
        self.history_list.setAlternatingRowColors(True)
        self.history_list.setStyleSheet("""
            QListWidget {
                font-size: 10pt;
                border: 1px solid #e5e7eb;
                border-radius: 6px;
                background: #fafafa;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f3f4f6;
            }
            QListWidget::item:selected {
                background: #dbeafe;
            }
        """)
        layout.addWidget(self.history_list, 1)
        
        # Footer with stats
        self.lbl_stats = QLabel("")
        self.lbl_stats.setStyleSheet("color: #6b7280; font-size: 9pt;")
        layout.addWidget(self.lbl_stats)
    
    def set_entity(self, entity_type: str, entity_id: str) -> None:
        """Set the entity to display history for."""
        self._entity_type = entity_type
        self._entity_id = entity_id
        self._refresh()
    
    def _refresh(self) -> None:
        """Refresh the history list."""
        self.history_list.clear()
        
        if not self._entity_type or not self._entity_id:
            self.lbl_stats.setText("Brak wybranego elementu")
            return
        
        # Get filter
        filter_idx = self.cb_filter.currentIndex()
        filter_action = self.cb_filter.itemData(filter_idx) if filter_idx > 0 else None
        
        # Get history
        entries = self._audit_log.get_entity_history(
            self._entity_type,
            self._entity_id,
            limit=100
        )
        
        # Apply filter
        if filter_action:
            entries = [e for e in entries if e.action.value == filter_action]
        
        # Add entries
        for entry in entries:
            item = QListWidgetItem()
            
            # Format: [timestamp] Action - details
            timestamp = entry.timestamp[:16].replace("T", " ")
            action_label = entry.action_label
            summary = entry.summary
            user = f" ({entry.user})" if entry.user else ""
            
            display = f"[{timestamp}] {action_label}{user}"
            if summary:
                display += f"\n  {summary}"
            
            item.setText(display)
            item.setData(Qt.ItemDataRole.UserRole, entry)
            self.history_list.addItem(item)
        
        # Update stats
        total = len(entries)
        self.lbl_stats.setText(f"Wpisów: {total}")
    
    def _export(self) -> None:
        """Export history to file."""
        from PyQt6.QtWidgets import QFileDialog
        from pathlib import Path
        from datetime import datetime
        
        if not self._entity_type or not self._entity_id:
            return
        
        default_name = f"historia_{self._entity_type}_{self._entity_id}_{datetime.now().strftime('%Y%m%d')}.json"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Eksport historii zmian",
            str(Path.home() / default_name),
            "Pliki JSON (*.json);;Wszystkie pliki (*.*)"
        )
        
        if file_path:
            import json
            entries = self._audit_log.get_entity_history(self._entity_type, self._entity_id)
            data = [e.to_dict() for e in entries]
            
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)


class AuditLogSummaryWidget(QWidget):
    """Widget for displaying audit log summary statistics."""
    
    sig_open_entity = pyqtSignal(str, str)  # (entity_type, entity_id)
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._audit_log = get_audit_log()
        self._build_ui()
    
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Stats panel
        stats_group = QGroupBox("Statystyki")
        stats_layout = QHBoxLayout(stats_group)
        
        self.lbl_total = QLabel("Razem: 0")
        self.lbl_total.setStyleSheet("font-size: 14pt; font-weight: bold;")
        stats_layout.addWidget(self.lbl_total)
        
        self.lbl_today = QLabel("Dziś: 0")
        self.lbl_today.setStyleSheet("font-size: 14pt;")
        stats_layout.addWidget(self.lbl_today)
        
        stats_layout.addStretch()
        layout.addWidget(stats_group)
        
        # Recent activity
        recent_group = QGroupBox("Ostatnie zmiany")
        recent_layout = QVBoxLayout(recent_group)
        
        self.recent_list = QListWidget()
        self.recent_list.setMaximumHeight(200)
        self.recent_list.itemDoubleClicked.connect(self._on_recent_clicked)
        recent_layout.addWidget(self.recent_list)
        
        btn_refresh = QPushButton("Odswiez")
        btn_refresh.clicked.connect(self._refresh)
        recent_layout.addWidget(btn_refresh)
        
        layout.addWidget(recent_group)
        
        self._refresh()
    
    def _refresh(self) -> None:
        """Refresh statistics."""
        stats = self._audit_log.get_statistics()
        
        self.lbl_total.setText(f"Razem: {stats['total']}")
        self.lbl_today.setText(f"Dziś: {stats['today']}")
        
        # Load recent entries
        self.recent_list.clear()
        entries = self._audit_log.get_recent_entries(limit=20)
        
        for entry in entries:
            item = QListWidgetItem()
            timestamp = entry.timestamp[:16].replace("T", " ")
            item.setText(f"[{timestamp}] {entry.action_label}: {entry.entity_type} {entry.entity_id}")
            item.setData(Qt.ItemDataRole.UserRole, entry)
            self.recent_list.addItem(item)
    
    def _on_recent_clicked(self, item: QListWidgetItem) -> None:
        """Handle double-click on recent entry."""
        entry = item.data(Qt.ItemDataRole.UserRole)
        if entry:
            self.sig_open_entity.emit(entry.entity_type, entry.entity_id)
