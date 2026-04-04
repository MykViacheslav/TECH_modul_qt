"""
Global search widget for TECH_modul.
Allows searching orders, clients, and other entities from anywhere in the app.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Callable

from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QFrame,
    QSizePolicy,
    QWidget,
    QPushButton,
)
from PyQt6.QtGui import QFont, QIcon, QColor


class SearchResultType(str, Enum):
    """Types of search results."""
    ORDER = "zamowienie"
    CLIENT = "klient"
    WORKER = "pracownik"
    MATERIAL = "materiał"


@dataclass
class SearchResult:
    """Single search result."""
    result_type: SearchResultType
    title: str
    subtitle: str = ""
    icon_text: str = ""
    data_id: str = ""
    data: dict | None = None
    
    @property
    def display_text(self) -> str:
        if self.subtitle:
            return f"{self.title}  -  {self.subtitle}"
        return self.title
    
    @property
    def type_label(self) -> str:
        labels = {
            SearchResultType.ORDER: "[Zamowienie]",
            SearchResultType.CLIENT: "[Klient]",
            SearchResultType.WORKER: "[Pracownik]",
            SearchResultType.MATERIAL: "[Material]",
        }
        return labels.get(self.result_type, self.result_type.value)


class GlobalSearchDialog(QDialog):
    """Global search dialog with live results."""
    
    sig_result_selected = pyqtSignal(object)  # emits SearchResult
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Wyszukiwarka")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self.setMaximumWidth(600)
        self.setMaximumHeight(500)
        
        self._results: list[SearchResult] = []
        self._search_callback: Optional[Callable] = None
        
        self._build_ui()
        self._setup_shortcuts()
    
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Header
        header = QLabel("🔍 Wyszukaj")
        header.setStyleSheet("font-size: 16pt; font-weight: bold; color: #1f2937;")
        layout.addWidget(header)
        
        hint = QLabel("Wpisz numer zamówienia, nazwisko klienta lub fragment nazwy...")
        hint.setStyleSheet("color: #6b7280; font-size: 10pt;")
        layout.addWidget(hint)
        
        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Szukaj...")
        self.search_input.setMinimumHeight(44)
        self.search_input.setStyleSheet("""
            QLineEdit {
                font-size: 14pt;
                padding: 8px 12px;
                border: 2px solid #d1d5db;
                border-radius: 8px;
                background: #ffffff;
            }
            QLineEdit:focus {
                border-color: #3b82f6;
            }
        """)
        layout.addWidget(self.search_input)
        
        # Results list
        self.results_list = QListWidget()
        self.results_list.setAlternatingRowColors(True)
        self.results_list.setStyleSheet("""
            QListWidget {
                font-size: 11pt;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                background: #fafafa;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #e5e7eb;
            }
            QListWidget::item:selected {
                background: #dbeafe;
                color: #1e40af;
            }
            QListWidget::item:hover {
                background: #f3f4f6;
            }
        """)
        layout.addWidget(self.results_list, 1)
        
        # Footer
        footer = QLabel("Enter — otwórz | Esc — zamknij")
        footer.setStyleSheet("color: #9ca3af; font-size: 9pt;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer)
        
        # Connect signals
        self.search_input.textChanged.connect(self._on_search_text_changed)
        self.results_list.itemDoubleClicked.connect(self._on_result_double_clicked)
    
    def _setup_shortcuts(self) -> None:
        """Setup keyboard shortcuts."""
        from PyQt6.QtGui import QShortcut, QKeySequence
        
        # Escape to close
        esc_shortcut = QShortcut(QKeySequence("Escape"), self)
        esc_shortcut.activated.connect(self.reject)
        
        # Enter to select
        enter_shortcut = QShortcut(QKeySequence("Return"), self)
        enter_shortcut.activated.connect(self._on_enter_pressed)
    
    def set_search_callback(self, callback: Callable) -> None:
        """Set callback function for searching."""
        self._search_callback = callback
    
    def _on_search_text_changed(self, text: str) -> None:
        """Handle search text changes with debounce."""
        text = text.strip()
        
        if len(text) < 2:
            self.results_list.clear()
            self._results = []
            return
        
        # Perform search
        self._perform_search(text)
    
    def _perform_search(self, query: str) -> None:
        """Perform search and update results."""
        self.results_list.clear()
        self._results = []
        
        if self._search_callback:
            self._results = self._search_callback(query)
        else:
            self._results = self._default_search(query)
        
        for result in self._results:
            item = QListWidgetItem()
            item.setText(f"{result.type_label}\n{result.display_text}")
            item.setData(Qt.ItemDataRole.UserRole, result)
            self.results_list.addItem(item)
        
        # Select first item
        if self.results_list.count() > 0:
            self.results_list.setCurrentRow(0)
    
    def _default_search(self, query: str) -> list[SearchResult]:
        """Default search implementation."""
        results = []
        
        # Try to search orders if store is available
        try:
            from src.storage.order_store_json import OrderStoreJson
            from src.storage.data_paths import data_dir
            
            store = OrderStoreJson()
            query_lower = query.lower()
            
            for order in store.list_orders():
                match = False
                code = str(getattr(order, "code", "") or "").lower()
                client = str(getattr(order, "client_name", "") or "").lower()
                
                if query_lower in code or query_lower in client:
                    match = True
                
                if match:
                    results.append(SearchResult(
                        result_type=SearchResultType.ORDER,
                        title=order.code,
                        subtitle=order.client_name,
                        data_id=order.code,
                    ))
                
                if len(results) >= 20:
                    break
        except Exception:
            pass
        
        return results
    
    def _on_result_double_clicked(self, item: QListWidgetItem) -> None:
        """Handle double-click on result."""
        result = item.data(Qt.ItemDataRole.UserRole)
        if result:
            self.sig_result_selected.emit(result)
            self.accept()
    
    def _on_enter_pressed(self) -> None:
        """Handle Enter key press."""
        item = self.results_list.currentItem()
        if item:
            self._on_result_double_clicked(item)
    
    def showEvent(self, event) -> None:
        """Handle show event - focus search input."""
        super().showEvent(event)
        self.search_input.setFocus()
        self.search_input.selectAll()


class GlobalSearchButton(QPushButton):
    """Button that opens global search dialog."""
    
    sig_navigate_to = pyqtSignal(str, str)  # (tab_title, data_id)
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setText("🔍")
        self.setToolTip("Wyszukaj (Ctrl+F)")
        self.setMinimumSize(40, 40)
        self.setStyleSheet("""
            QPushButton {
                font-size: 18px;
                border: none;
                border-radius: 8px;
                background: transparent;
            }
            QPushButton:hover {
                background: #f3f4f6;
            }
        """)
        
        self._dialog: Optional[GlobalSearchDialog] = None
    
    def open_search(self) -> None:
        """Open the search dialog."""
        if self._dialog is None:
            self._dialog = GlobalSearchDialog(self.window())
            self._dialog.sig_result_selected.connect(self._on_result_selected)
        
        self._dialog.show()
        self._dialog.raise_()
        self._dialog.activateWindow()
    
    def _on_result_selected(self, result: SearchResult) -> None:
        """Handle result selection."""
        if result.result_type == SearchResultType.ORDER:
            self.sig_navigate_to.emit("Nowe zamowienie", result.data_id)
        elif result.result_type == SearchResultType.CLIENT:
            self.sig_navigate_to.emit("Start", result.data_id)


def create_search_button(parent: Optional[QWidget] = None) -> GlobalSearchButton:
    """Factory function to create search button."""
    return GlobalSearchButton(parent)
