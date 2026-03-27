from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox

# Ensure project root is importable when running this file directly.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.app.main_window import MainWindow
from src.domain.permissions import normalize_role
from src.widgets.login_dialog import LoginDialog


def show_error(title: str, message: str, details: str = ""):
    """Show user-friendly error dialog."""
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Icon.Critical)
    msg.setWindowTitle(title)
    msg.setText(message)
    if details:
        msg.setDetailedText(details)
    msg.exec()


def main() -> int:
    parser = argparse.ArgumentParser(description="TECH_modul - System zarządzania meblami")
    parser.add_argument(
        "--wall", action="store_true",
        help="Uruchom w trybie ściany (kiosk) na 4 monitorach"
    )
    parser.add_argument(
        "--worker", type=str, default="",
        help="Filtruj zadania dla konkretnego pracownika (tylko tryb wall)"
    )
    parser.add_argument(
        "--screen", type=int, default=0,
        help="Indeks ekranu (0-3) dla trybu wall"
    )
    parser.add_argument(
        "--station", type=str, default="",
        choices=["", "cnc", "oklejanie", "lakiernia", "montaz"],
        help="Filtr stacji dla kalendarza kiosk (cnc/oklejanie/lakiernia/montaz)"
    )
    parser.add_argument(
        "--no-login", action="store_true",
        help="Pomiń okno logowania (dla testów)"
    )
    parser.add_argument(
        "--server", action="store_true",
        help="Uruchom jako serwer danych (port 8000)"
    )
    parser.add_argument(
        "--server-port", type=int, default=8000,
        help="Port serwera (domyślnie 8000)"
    )
    parser.add_argument(
        "--safe", action="store_true",
        help="Tryb awaryjny - minimalne obciążenie"
    )
    parser.add_argument(
        "--time-kiosk", action="store_true",
        help="Uruchom sam kiosk rejestracji czasu pracy"
    )
    args = parser.parse_args()
    
    # Export safe mode flag for other modules
    import os
    if args.safe:
        os.environ["TECH_SAFE_MODE"] = "1"
    
    app = QApplication(sys.argv)
    
    # === TRYB SERWER ===
    if args.server:
        from src.server.data_server import DataServer
        
        print(f"Uruchamianie serwera TECH_modul na porcie {args.server_port}...")
        print(f"Inne komputery mogą się połączyć pod adresem: http://[TWOJ_IP]:{args.server_port}")
        print(f"Sprawdź swój IP: ipconfig (wiersz 'IPv4 Address')")
        print("Naciśnij Ctrl+C aby zatrzymać serwer")
        
        server = DataServer(host="0.0.0.0", port=args.server_port)
        server.start(background=False)  # Blocks until stopped
        return 0

    if args.time_kiosk:
        from src.widgets.time_clock_kiosk import TimeClockKioskWindow

        w = TimeClockKioskWindow()
        w.showFullScreen()
        return app.exec()
    
    # === TRYB ŚCIANY (KIOSK) ===
    if args.wall:
        from src.widgets.wall_calendar_view import WallCalendarView
        
        w = WallCalendarView(station_filter=args.station)
        w.set_worker_filter(args.worker)
        
        # Position on specified screen
        screens = app.screens()
        if args.screen < len(screens):
            screen_geometry = screens[args.screen].geometry()
            w.setGeometry(screen_geometry)
        
        w.showFullScreen()
    else:
        # === TRYB NORMALNY (KLIENT) ===
        
        # Show login dialog first (unless --no-login flag)
        current_worker = ""
        current_role = "produkcja"
        
        if not args.no_login:
            login_dialog = LoginDialog()
            result = login_dialog.exec()
            
            if result != QDialog.DialogCode.Accepted:
                # User cancelled login
                return 0
            
            current_worker, current_role = login_dialog.get_logged_in_worker()
            current_role = normalize_role(current_role)
        
        # Normal mode - show main window
        try:
            w = MainWindow()
            w.set_current_user(current_worker, current_role)
            w.showNormal()  # Use showNormal instead of showMaximized
            w.resize(1400, 900)  # Set reasonable default size
        except Exception as e:
            show_error(
                "Błąd uruchomienia",
                f"Nie można uruchomić aplikacji:\n{str(e)}\n\n"
                f"Spróbuj uruchomić z --no-login",
                traceback.format_exc()
            )
            return 1
    
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
