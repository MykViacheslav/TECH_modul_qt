"""
Login dialog for TECH_modul workstation authentication.
Supports canonical RBAC roles from src.domain.permissions.
"""

from __future__ import annotations

from typing import Optional, Tuple

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.domain.permissions import ROLE_LABELS, UserRole, normalize_role
from src.domain.worker_models import WorkerDef
from src.storage.worker_store_json import WorkerStoreJson


class LoginDialog(QDialog):
    """
    Login dialog for selecting a worker and verifying their identity.
    
    Signals:
        login_success: Emitted when login is successful (worker_name, role)
    """
    
    login_success = pyqtSignal(str, str)  # worker_name, role
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Logowanie - TECH_modul")
        self.setModal(True)
        self.setMinimumWidth(350)
        
        self._worker_store = WorkerStoreJson()
        self._current_worker: Optional[WorkerDef] = None
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Setup the login dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Title
        title = QLabel("TECH_modul")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        subtitle = QLabel("Wybierz pracownika i podaj hasło")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("font-size: 12px; color: #666;")
        layout.addWidget(subtitle)
        
        # Form
        form = QFormLayout()
        form.setSpacing(10)
        
        # Worker selection
        self._worker_combo = QLineEdit()
        self._worker_combo.setPlaceholderText("Wpisz imię i nazwisko...")
        self._worker_combo.textChanged.connect(self._on_worker_selected)
        form.addRow("Pracownik:", self._worker_combo)
        
        # Role display (read-only, shows detected role)
        self._role_label = QLabel("—")
        self._role_label.setStyleSheet("padding: 5px; background: #f0f0f0; border-radius: 3px;")
        form.addRow("Rola:", self._role_label)
        
        # Password (simple for now)
        self._password_input = QLineEdit()
        self._password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_input.setPlaceholderText("Hasło (domyślnie: 1234)")
        self._password_input.returnPressed.connect(self._on_login_clicked)
        form.addRow("Hasło:", self._password_input)
        
        layout.addLayout(form)
        
        # Info label
        info = QLabel("Domyślne hasło dla wszystkich: 1234")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setStyleSheet("font-size: 10px; color: #888;")
        layout.addWidget(info)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self._btn_cancel = QPushButton("Anuluj")
        self._btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self._btn_cancel)
        
        self._btn_login = QPushButton("Zaloguj")
        self._btn_login.setDefault(True)
        self._btn_login.clicked.connect(self._on_login_clicked)
        btn_layout.addWidget(self._btn_login)
        
        layout.addLayout(btn_layout)
        
        # Load worker names for autocomplete
        self._load_worker_names()
    
    def _load_worker_names(self) -> None:
        """Load worker names from store."""
        try:
            names = self._worker_store.list_names()
            # Could use QCompleter here for better UX
        except Exception:
            pass
    
    def _on_worker_selected(self, text: str) -> None:
        """Handle worker selection change."""
        name = str(text or "").strip()
        if not name:
            self._role_label.setText("—")
            self._current_worker = None
            return
        
        worker = self._worker_store.get(name)
        if worker:
            self._current_worker = worker
            role = normalize_role(str(getattr(worker, "role", "") or ""))
            role_label = ROLE_LABELS.get(role, role or "Nieznana")
            self._role_label.setText(role_label)
        else:
            self._current_worker = None
            self._role_label.setText("Nowy pracownik")
    
    def _on_login_clicked(self) -> None:
        """Handle login button click."""
        name = self._worker_combo.text().strip()
        password = self._password_input.text()
        
        if not name:
            QMessageBox.warning(self, "Błąd", "Podaj imię i nazwisko pracownika.")
            return
        
        # Simple password check (in production, use proper hashing)
        if password != "1234":
            QMessageBox.warning(self, "Błąd", "Nieprawidłowe hasło.")
            return
        
        # Get or create worker
        worker = self._worker_store.get(name)
        if worker is None:
            # Create new worker with a valid default role.
            worker = WorkerDef(name=name, role="produkcja")
            result = self._worker_store.save_new(worker)
            if not result.ok:
                QMessageBox.warning(self, "Błąd", f"Nie udało się utworzyć pracownika: {result.message_pl}")
                return
        
        self._current_worker = worker
        role = normalize_role(str(getattr(worker, "role", "") or "")) or "produkcja"
        
        self.login_success.emit(name, role)
        self.accept()
    
    def get_logged_in_worker(self) -> Tuple[str, str]:
        """
        Get the logged in worker info.
        
        Returns:
            Tuple of (worker_name, role)
        """
        if self._current_worker is None:
            return ("", "")
        
        name = str(getattr(self._current_worker, "name", "") or "").strip()
        role = normalize_role(str(getattr(self._current_worker, "role", "") or "")) or "produkcja"
        return (name, role)


class QuickSwitchDialog(QDialog):
    """
    Quick worker switch dialog for switching between users.
    Shows a list of workers with their roles.
    """
    
    worker_selected = pyqtSignal(str, str)  # worker_name, role
    
    def __init__(self, current_worker: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Zmień pracownika")
        self.setModal(True)
        self.setMinimumWidth(300)
        self._current_worker = current_worker
        
        self._worker_store = WorkerStoreJson()
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Setup the quick switch dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Current user
        current_label = QLabel(f"Aktualny użytkownik: {self._current_worker or '—'}")
        current_label.setStyleSheet("font-weight: bold; margin-bottom: 5px;")
        layout.addWidget(current_label)
        
        # Worker list
        self._worker_list = QLineEdit()
        self._worker_list.setPlaceholderText("Wpisz nazwisko...")
        self._worker_list.returnPressed.connect(self._on_select_clicked)
        layout.addWidget(self._worker_list)
        
        # Password
        self._password = QLineEdit()
        self._password.setEchoMode(QLineEdit.EchoMode.Password)
        self._password.setPlaceholderText("Hasło")
        layout.addWidget(self._password)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self._btn_cancel = QPushButton("Anuluj")
        self._btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self._btn_cancel)
        
        self._btn_select = QPushButton("Zmień")
        self._btn_select.setDefault(True)
        self._btn_select.clicked.connect(self._on_select_clicked)
        btn_layout.addWidget(self._btn_select)
        
        layout.addLayout(btn_layout)
    
    def _on_select_clicked(self) -> None:
        """Handle select button click."""
        name = self._worker_list.text().strip()
        password = self._password.text()
        
        if not name:
            QMessageBox.warning(self, "Błąd", "Podaj nazwisko pracownika.")
            return
        
        if password != "1234":
            QMessageBox.warning(self, "Błąd", "Nieprawidłowe hasło.")
            return
        
        worker = self._worker_store.get(name)
        if worker is None:
            QMessageBox.warning(self, "Błąd", "Pracownik nie istnieje w bazie.")
            return
        
        role = normalize_role(str(getattr(worker, "role", "") or "")) or "produkcja"
        self.worker_selected.emit(name, role)
        self.accept()
