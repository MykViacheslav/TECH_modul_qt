"""
Network settings widget for TECH_modul.
Allows configuring server connection for multi-computer setup.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.storage.network_store import NetworkConfig


class NetworkHelpDialog(QDialog):
    """Dialog showing network setup instructions."""
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Instrukcja - Łączenie komputerów w sieć")
        self.setMinimumSize(700, 600)
        
        layout = QVBoxLayout(self)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        content = QWidget()
        self._setup_content(content)
        scroll.setWidget(content)
        
        layout.addWidget(scroll)
        
        btn_close = QPushButton("Zamknij")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)
    
    def _setup_content(self, parent: QWidget) -> None:
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        instructions = QTextEdit()
        instructions.setReadOnly(True)
        instructions.setHtml(self._get_instructions_html())
        instructions.setMinimumHeight(500)
        layout.addWidget(instructions)
    
    def _get_instructions_html(self) -> str:
        return """
        <style>
            h2 { color: #1e40af; margin-top: 20px; }
            h3 { color: #1e293b; margin-top: 15px; }
            .step { background: #f8fafc; padding: 12px; margin: 8px 0; border-radius: 8px; border-left: 4px solid #3b82f6; }
            .step-num { background: #3b82f6; color: white; padding: 4px 10px; border-radius: 50%; font-weight: bold; }
            .warning { background: #fef3c7; padding: 10px; border-radius: 8px; border-left: 4px solid #f59e0b; margin: 10px 0; }
            .tip { background: #dbeafe; padding: 10px; border-radius: 8px; border-left: 4px solid #3b82f6; margin: 10px 0; }
            code { background: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-family: monospace; }
            .cmd { background: #1e293b; color: #22c55e; padding: 10px; border-radius: 6px; font-family: monospace; margin: 5px 0; }
        </style>
        
        <h2>Instrukcja - Łączenie komputerów w sieć</h2>
        <p>Jeden komputer staje się <b>SERWEREM</b> (przechowuje dane), 
        a pozostałe łączą się do niego jako <b>KLIENCI</b>.</p>
        
        <div style="text-align: center; background: #f1f5f9; padding: 15px; border-radius: 10px; margin: 15px 0;">
            <b>Schemat:</b><br><br>
            ┌─────────────────┐<br>
            │  KOMPUTER       │<br>
            │  SERWER ◄───────┼── Port 8000<br>
            │  (Dane)   │<br>
            └─────┬───────────┘<br>
                  │<br>
            ──────┼──── Sieć LAN ────<br>
            │     │     │     │<br>
            ▼     ▼     ▼     ▼<br>
           PC2   PC3   PC4   PC5<br>
           (Klienci)<br>
        </div>
        
        <h2>KROK PO KROKU</h2>
        
        <h3>KROK 1: Wybierz komputer SERWER</h3>
        <div class="step">
            <span class="step-num">1</span> Wybierz jeden komputer jako serwer.<br>
            <b>Ważne:</b> Ten komputer musi być <b>włączony</b> cały czas!
        </div>
        
        <h3>KROK 2: Znajdź adres IP serwera</h3>
        <div class="step">
            <span class="step-num">2</span> Na komputerze-serwerze:<br>
            • Otwórz <b>Wiersz polecenia</b> (cmd)<br>
            • Wpisz: <code>ipconfig</code><br>
            • Znajdź <b>"Adres IPv4"</b> (np. 192.168.1.100)<br>
            • Zapisz ten adres!
        </div>
        
        <div class="tip">
            💡 Adres IP zwykle zaczyna się od <code>192.168.x.x</code>
        </div>
        
        <h3>KROK 3: Uruchom serwer</h3>
        <div class="step">
            <span class="step-num">3</span> Na komputerze-serwerze:<br>
            • Zamknij TECH_modul<br>
            • Otwórz terminal w folderze aplikacji<br>
            • Uruchom: <div class="cmd">python src/app/main.py --server</div>
            • Nie zamykaj tego okna!
        </div>
        
        <h3>KROK 4: Skonfiguruj klienty</h3>
        <div class="step">
            <span class="step-num">4</span> Na każdym komputerze-kliencie:<br>
            • Uruchom TECH_modul normalnie<br>
            • Idź do <b>Ustawienia → Sieć</b><br>
            • Zaznacz <b>"Włącz pracę sieciową"</b><br>
            • Wpisz adres: <code>http://192.168.1.100:8000</code><br>
            • Kliknij <b>"Test połączenia"</b><br>
            • Powinno być: ✓ Połączono
        </div>
        
        <h3>KROK 5: Synchronizuj dane</h3>
        <div class="step">
            <span class="step-num">5</span> Pierwszy raz:<br>
            • Kliknij <b>"Pobierz dane z serwera"</b><br>
            • Odśwież aplikację<br>
            • Gotowe! Wszyscy widzą te same dane
        </div>
        
        <div class="warning">
            ⚠️ <b>WAŻNE:</b><br>
            • Serwer <b>MUSI</b> być włączony gdy ktoś pracuje<br>
            • Wszyscy w <b>tej samej sieci WiFi/LAN</b><br>
            • Firewall może wymagać otwarcia portu 8000
        </div>
        
        <h2>ROZWIĄZYWANIE PROBLEMÓW</h2>
        
        <h3>"Nie można połączyć"</h3>
        <div class="step">
            • Sprawdź czy serwer jest uruchomiony<br>
            • Sprawdź adres IP<br>
            • Sprawdź czy ta sama sieć<br>
            • Spróbuj: <code>ping 192.168.1.100</code>
        </div>
        
        <h3>"Nie widzę danych"</h3>
        <div class="step">
            • Kliknij "Pobierz dane z serwera"<br>
            • Restart aplikacji<br>
            • Sprawdź czy serwer ma dane
        </div>
        """


class NetworkSettingsWidget(QWidget):
    """
    Widget for configuring network/server connection.
    
    Signals:
        settings_changed: Emitted when settings are saved
    """
    
    settings_changed = pyqtSignal()
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._config = NetworkConfig()
        self._setup_ui()
        self._load_current_settings()
    
    def _setup_ui(self) -> None:
        """Setup the widget UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # === NETWORK MODE ===
        mode_group = QGroupBox("Tryb pracy")
        mode_layout = QVBoxLayout(mode_group)
        
        self._chk_enabled = QCheckBox("Włącz pracę sieciową (połączenie z serwerem)")
        self._chk_enabled.stateChanged.connect(self._on_mode_changed)
        mode_layout.addWidget(self._chk_enabled)
        
        mode_info = QLabel(
            "Gdy włączone, dane będą pobierane/zapisywane na centralnym serwerze.\n"
            "Gdy wyłączone, aplikacja działa lokalnie na tym komputerze."
        )
        mode_info.setStyleSheet("color: #666; font-size: 11px;")
        mode_info.setWordWrap(True)
        mode_layout.addWidget(mode_info)
        
        layout.addWidget(mode_group)
        
        # === SERVER CONFIGURATION ===
        server_group = QGroupBox("Konfiguracja serwera")
        server_layout = QVBoxLayout(server_group)
        
        # Server URL
        url_layout = QHBoxLayout()
        url_label = QLabel("Adres serwera:")
        url_label.setFixedWidth(100)
        url_layout.addWidget(url_label)
        
        self._edit_url = QLineEdit()
        self._edit_url.setPlaceholderText("http://192.168.1.100:8000")
        self._edit_url.editingFinished.connect(self._on_url_changed)
        url_layout.addWidget(self._edit_url)
        
        server_layout.addLayout(url_layout)
        
        # Info text
        info_text = QLabel(
            "Adres serwera to IP komputera, na którym uruchomiono TECH_modul w trybie serwera.\n"
            "Sprawdź adres IP komputera serwera: uruchom cmd → wpisz 'ipconfig'"
        )
        info_text.setStyleSheet("color: #666; font-size: 11px;")
        info_text.setWordWrap(True)
        server_layout.addWidget(info_text)
        
        # Test connection button
        test_layout = QHBoxLayout()
        self._btn_test = QPushButton("Test połączenia")
        self._btn_test.clicked.connect(self._test_connection)
        test_layout.addWidget(self._btn_test)
        test_layout.addStretch()
        
        self._lbl_test_result = QLabel("")
        test_layout.addWidget(self._lbl_test_result)
        
        server_layout.addLayout(test_layout)
        
        layout.addWidget(server_group)
        
        # === SYNC SETTINGS ===
        sync_group = QGroupBox("Synchronizacja")
        sync_layout = QVBoxLayout(sync_group)
        
        self._chk_auto_sync = QCheckBox("Automatyczna synchronizacja co 30 sekund")
        self._chk_auto_sync.setChecked(True)
        sync_layout.addWidget(self._chk_auto_sync)
        
        sync_btn_layout = QHBoxLayout()
        self._btn_sync_to = QPushButton("Wyślij dane na serwer")
        self._btn_sync_to.clicked.connect(self._sync_to_server)
        sync_btn_layout.addWidget(self._btn_sync_to)
        
        self._btn_sync_from = QPushButton("Pobierz dane z serwera")
        self._btn_sync_from.clicked.connect(self._sync_from_server)
        sync_btn_layout.addWidget(self._btn_sync_from)
        
        sync_btn_layout.addStretch()
        sync_layout.addLayout(sync_btn_layout)
        
        layout.addWidget(sync_group)
        
        # === SERVER MODE INFO ===
        server_mode_group = QGroupBox("Tryb serwera")
        server_mode_layout = QVBoxLayout(server_mode_group)
        
        server_mode_info = QLabel(
            "Aby uruchomić ten komputer jako serwer:\n\n"
            "1. Zamknij aplikację TECH_modul\n"
            "2. Otwórz terminal (cmd)\n"
            "3. Przejdź do folderu aplikacji\n"
            "4. Uruchom: python src/app/main.py --server\n\n"
            "Serwer nasłuchuje na porcie 8000.\n"
            "Inne komputery łączą się pod adresem: http://[TWOJ_IP]:8000"
        )
        server_mode_info.setStyleSheet("color: #333; font-size: 11px; background: #f5f5f5; padding: 10px;")
        server_mode_info.setWordWrap(True)
        server_mode_layout.addWidget(server_mode_info)
        
        self._btn_start_server = QPushButton("Uruchom serwer w tle")
        self._btn_start_server.clicked.connect(self._start_background_server)
        server_mode_layout.addWidget(self._btn_start_server)
        
        layout.addWidget(server_mode_group)
        
        # === INSTRUKCJA ===
        btn_row = QHBoxLayout()
        
        self._btn_help = QPushButton("📖 Pokaż pełną instrukcję")
        self._btn_help.clicked.connect(self._show_help)
        btn_row.addWidget(self._btn_help)
        btn_row.addStretch()
        
        layout.addLayout(btn_row)
        
        # Status
        self._lbl_status = QLabel("")
        self._lbl_status.setWordWrap(True)
        layout.addWidget(self._lbl_status)
        
        layout.addStretch()
    
    def _show_help(self) -> None:
        """Show network setup instructions."""
        dialog = NetworkHelpDialog(self)
        dialog.exec()
    
    def _load_current_settings(self) -> None:
        """Load current settings into UI."""
        self._chk_enabled.setChecked(self._config.enabled)
        self._edit_url.setText(self._config.server_url)
        self._update_ui_state()
    
    def _update_ui_state(self) -> None:
        """Update UI enabled state based on network mode."""
        enabled = self._chk_enabled.isChecked()
        self._edit_url.setEnabled(enabled)
        self._btn_test.setEnabled(enabled and bool(self._edit_url.text()))
        self._btn_sync_to.setEnabled(enabled)
        self._btn_sync_from.setEnabled(enabled)
        self._chk_auto_sync.setEnabled(enabled)
    
    def _on_mode_changed(self, state: int) -> None:
        """Handle network mode checkbox change."""
        self._config.enabled = state == 2  # Qt.CheckState.Checked
        self._update_ui_state()
        self.settings_changed.emit()
    
    def _on_url_changed(self) -> None:
        """Handle URL field change."""
        self._config.server_url = self._edit_url.text().strip()
        self._update_ui_state()
    
    def _test_connection(self) -> None:
        """Test connection to server."""
        self._lbl_test_result.setText("Testowanie...")
        self._lbl_test_result.setStyleSheet("color: #666;")
        
        success, message = self._config.test_connection()
        
        if success:
            self._lbl_test_result.setText(f"✓ {message}")
            self._lbl_test_result.setStyleSheet("color: #16a34a;")
        else:
            self._lbl_test_result.setText(f"✗ {message}")
            self._lbl_test_result.setStyleSheet("color: #dc2626;")
    
    def _sync_to_server(self) -> None:
        """Sync local data to server."""
        from src.storage.network_store import HybridStore
        
        stores = ["zamowienia", "klienci", "pracownicy", "alarmy", "materialy", "uslugi"]
        total = 0
        
        for store_name in stores:
            try:
                store = HybridStore(store_name)
                count = store.sync_to_network()
                total += count
            except Exception as e:
                print(f"Sync error for {store_name}: {e}")
        
        QMessageBox.information(
            self,
            "Synchronizacja",
            f"Wysłano {total} elementów na serwer."
        )
    
    def _sync_from_server(self) -> None:
        """Sync data from server to local."""
        from src.storage.network_store import HybridStore
        
        stores = ["zamowienia", "klienci", "pracownicy", "alarmy", "materialy", "uslugi"]
        total = 0
        
        for store_name in stores:
            try:
                store = HybridStore(store_name)
                count = store.sync_from_network()
                total += count
            except Exception as e:
                print(f"Sync error for {store_name}: {e}")
        
        QMessageBox.information(
            self,
            "Synchronizacja",
            f"Pobrano {total} elementów z serwera.\n\n"
            "Uruchom ponownie aplikację, aby zobaczyć zaktualizowane dane."
        )
    
    def _start_background_server(self) -> None:
        """Start server in background thread."""
        import threading
        from src.server.data_server import DataServer
        
        try:
            server = DataServer(host="0.0.0.0", port=8000)
            thread = threading.Thread(target=server.start, kwargs={"background": False}, daemon=True)
            thread.start()
            
            self._lbl_status.setText(
                "✓ Serwer uruchomiony na porcie 8000\n"
                "Inne komputery mogą się połączyć."
            )
            self._lbl_status.setStyleSheet("color: #16a34a;")
            self._btn_start_server.setEnabled(False)
            self._btn_start_server.setText("Serwer działa...")
        except Exception as e:
            self._lbl_status.setText(f"✗ Błąd: {e}")
            self._lbl_status.setStyleSheet("color: #dc2626;")
