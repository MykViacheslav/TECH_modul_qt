"""
Network setup instructions widget for TECH_modul.
Displays step-by-step guide for connecting multiple computers.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame,
    QLabel,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class NetworkHelpWidget(QWidget):
    """
    Widget displaying instructions for setting up multi-computer network.
    """
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Setup the instructions UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Title
        title = QLabel("Instrukcja - Łączenie komputerów w sieć")
        title.setFont(QFont("", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #1e293b;")
        layout.addWidget(title)
        
        # Instructions text
        instructions = QTextEdit()
        instructions.setReadOnly(True)
        instructions.setHtml(self._get_instructions_html())
        instructions.setMinimumHeight(400)
        layout.addWidget(instructions)
    
    def _get_instructions_html(self) -> str:
        """Return HTML formatted instructions."""
        return """
        <style>
            h2 { color: #1e40af; margin-top: 20px; }
            h3 { color: #1e293b; margin-top: 15px; }
            .step { background: #f8fafc; padding: 12px; margin: 8px 0; border-radius: 8px; border-left: 4px solid #3b82f6; }
            .step-number { background: #3b82f6; color: white; padding: 4px 10px; border-radius: 50%; font-weight: bold; }
            .warning { background: #fef3c7; padding: 10px; border-radius: 8px; border-left: 4px solid #f59e0b; margin: 10px 0; }
            .tip { background: #dbeafe; padding: 10px; border-radius: 8px; border-left: 4px solid #3b82f6; margin: 10px 0; }
            code { background: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-family: monospace; }
            .cmd { background: #1e293b; color: #22c55e; padding: 10px; border-radius: 6px; font-family: monospace; margin: 5px 0; }
        </style>
        
        <h2>🏗️ Konfiguracja dla 3-4 komputerów</h2>
        <p>Jeden komputer staje się <b>SERWEREM</b> (przechowuje dane), 
        a pozostałe łączą się do niego jako <b>KLIENCI</b>.</p>
        
        <div style="text-align: center; background: #f1f5f9; padding: 15px; border-radius: 10px; margin: 15px 0;">
            <b>Schemat połączeń:</b><br><br>
            ┌─────────────────┐<br>
            │ KOMPUTER        │<br>
            │ SERWER ◄────────┼──── Port 8000<br>
            │ (Dane) │<br>
            └────┬────────────┘<br>
                 │<br>
            ─────┼──── Sieć LAN ────<br>
            │    │    │    │<br>
            ▼    ▼    ▼    ▼<br>
           PC2  PC3  PC4  PC5<br>
           (Klienci)<br>
        </div>
        
        <h2>📋 KROK PO KROKU</h2>
        
        <h3>KROK 1: Wybierz komputer SERWER</h3>
        <div class="step">
            <span class="step-number">1</span> Wybierz jeden komputer, który będzie serwerem.<br>
            <b>Ważne:</b> Ten komputer musi być <b>włączony</b> cały czas, gdy inni pracują.
        </div>
        
        <h3>KROK 2: Znajdź adres IP serwera</h3>
        <div class="step">
            <span class="step-number">2a</span> Na komputerze-serwerze otwórz <b>Wiersz polecenia</b> (cmd)<br>
            <span class="step-number">2b</span> Wpisz komendę i naciśnij Enter:<br>
            <div class="cmd">ipconfig</div>
            <span class="step-number">2c</span> Znajdź linię <b>"Adres IPv4"</b> (np. 192.168.1.100)<br>
            <span class="step-number">2d</span> Zapisz ten adres - będziesz go potrzebować!
        </div>
        
        <div class="tip">
            💡 <b>Tip:</b> Adres IP zwykle zaczyna się od 192.168.x.x<br>
            Przykład: <code>192.168.1.100</code>, <code>192.168.0.15</code>
        </div>
        
        <h3>KROK 3: Uruchom serwer</h3>
        <div class="step">
            <span class="step-number">3a</span> Na komputerze-serwerze zamknij TECH_modul<br>
            <span class="step-number">3b</span> Otwórz terminal w folderze aplikacji<br>
            <span class="step-number">3c</span> Uruchom serwer:<br>
            <div class="cmd">python src/app/main.py --server</div>
            <span class="step-number">3d</span> Zobaczysz komunikat:<br>
            <div style="background: #22c55e20; padding: 8px; border-radius: 4px; margin: 5px 0;">
                ✅ Serwer uruchomiony na porcie 8000<br>
                Adres: http://192.168.1.100:8000
            </div>
            <b>Uwaga:</b> Nie zamykaj tego okna terminala!
        </div>
        
        <h3>KROK 4: Skonfiguruj klienty (pozostałe komputery)</h3>
        <div class="step">
            <span class="step-number">4a</span> Na każdym komputerze-kliencie uruchom TECH_modul normalnie:<br>
            <div class="cmd">python src/app/main.py</div>
            <span class="step-number">4b</span> Przejdź do <b>Ustawienia → Sieć</b><br>
            <span class="step-number">4c</span> Zaznacz <b>"Włącz pracę sieciową"</b><br>
            <span class="step-number">4d</span> Wpisz adres serwera (z kroku 2):<br>
            <div class="cmd">http://192.168.1.100:8000</div>
            <span class="step-number">4e</span> Kliknij <b>"Test połączenia"</b><br>
            <span class="step-number">4f</span> Powinien pojawić się komunikat: ✓ Połączono
        </div>
        
        <h3>KROK 5: Synchronizacja danych</h3>
        <div class="step">
            <span class="step-number">5a</span> Po raz pierwszy kliknij <b>"Pobierz dane z serwera"</b><br>
            <span class="step-number">5b</span> Odśwież aplikację (zamknij i otwórz ponownie)<br>
            <span class="step-number">5c</span> Od teraz dane są wspólne!
        </div>
        
        <div class="warning">
            ⚠️ <b>WAŻNE:</b><br>
            • Komputer-serwer <b>MUSI</b> być włączony, gdy ktoś chce pracować<br>
            • Wszyscy muszą być w <b>tej samej sieci WiFi/LAN</b><br>
            • Jeśli komputer ma firewall, może trzeba otworzyć port 8000
        </div>
        
        <h2>🔧 ROZWIĄZYWANIE PROBLEMÓW</h2>
        
        <h3>"Nie można połączyć z serwerem"</h3>
        <div class="step">
            • Sprawdź czy serwer jest uruchomiony<br>
            • Sprawdź czy adres IP jest poprawny<br>
            • Sprawdź czy oba komputery są w tej samej sieci<br>
            • Spróbuj ping: <code>ping 192.168.1.100</code>
        </div>
        
        <h3>"Błąd połączenia" / Firewall</h3>
        <div class="step">
            • Windows Firewall może blokować port 8000<br>
            • Dodaj wyjątek dla Python lub portu 8000 w firewallu<br>
            • Alternatywnie: uruchom terminal jako Administrator
        </div>
        
        <h3>"Nie widzę danych z innych komputerów"</h3>
        <div class="step">
            • Kliknij "Pobierz dane z serwera"<br>
            • Zamknij i otwórz aplikację ponownie<br>
            • Sprawdź czy serwer ma wszystkie dane
        </div>
        
        <h2>⚡ SZYBKI START (dla zaawansowanych)</h2>
        
        <p><b>Serwer (Komputer 1):</b></p>
        <div class="cmd">
            ipconfig  # Znajdź adres IPv4<br>
            python src/app/main.py --server
        </div>
        
        <p><b>Klienci (Komputery 2-4):</b></p>
        <div class="cmd">
            python src/app/main.py<br>
            # Ustawienia → Sieć → Włącz → Wpisz adres → Test
        </div>
        
        <br>
        <p style="color: #64748b; font-size: 11px;">
            W przypadku problemów skontaktuj się z administratorem IT lub sprawdź 
            dokumentację sieciową Twojego routera.
        </p>
        """
