"""
Wall calendar view for kiosk mode - displays on 4 monitors.
Shows timeline of tasks for employees with large, easy-to-read format.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.domain.calendar_event import CalendarEvent
from src.storage.calendar_event_store_json import CalendarEventStoreJson


# Station filters for production kiosk
STATION_FILTERS = {
    "Wszystkie": "",
    "CNC": "cnc",
    "Oklejanie": "oklejanie", 
    "Lakiernia": "lakiernia",
    "Montaż": "montaz",
}

STATION_COLORS = {
    "cnc": "#3b82f6",      # Blue
    "oklejanie": "#f59e0b", # Orange
    "lakiernia": "#8b5cf6", # Purple
    "montaz": "#10b981",   # Green
    "default": "#64748b",  # Gray
}


class WallCalendarView(QWidget):
    """
    Large calendar view designed for wall display / kiosk mode.
    Shows timeline of tasks for today and upcoming days.
    
    Features:
    - Large text for easy reading from distance
    - Color-coded by event type
    - Auto-refreshes every 30 seconds
    - Shows current time prominently
    - Highlights overdue tasks
    - Station filters: CNC, Oklejanie, Lakiernia, Montaż
    """
    
    def __init__(self, parent: Optional[QWidget] = None, station_filter: str = "") -> None:
        super().__init__(parent)
        self._calendar_store = CalendarEventStoreJson()
        self._station_filter = station_filter  # Filter by station
        self._setup_ui()
        self._setup_auto_refresh()
        self._refresh_view()
    
    def _setup_ui(self) -> None:
        """Setup the wall calendar UI."""
        self.setStyleSheet("""
            QWidget {
                background-color: #1a1a2e;
                color: #ffffff;
            }
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 20, 30, 20)
        main_layout.setSpacing(15)
        
        # Header: Time and Date
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #16213e;
                border-radius: 15px;
                padding: 15px;
            }
        """)
        header_layout = QHBoxLayout(header)
        
        self._time_label = QLabel()
        self._time_label.setFont(QFont("Arial", 72, QFont.Weight.Bold))
        self._time_label.setStyleSheet("color: #00d4ff;")
        header_layout.addWidget(self._time_label, 2)
        
        date_info = QVBoxLayout()
        
        self._date_label = QLabel()
        self._date_label.setFont(QFont("Arial", 28))
        self._date_label.setStyleSheet("color: #e0e0e0;")
        date_info.addWidget(self._date_label)
        
        self._day_label = QLabel()
        self._day_label.setFont(QFont("Arial", 20))
        self._day_label.setStyleSheet("color: #a0a0a0;")
        date_info.addWidget(self._day_label)
        
        header_layout.addLayout(date_info, 1)
        
        # Status indicator
        self._status_label = QLabel("AKTYWNY")
        self._status_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self._status_label.setStyleSheet("""
            background-color: #00c853;
            color: #ffffff;
            padding: 8px 20px;
            border-radius: 20px;
        """)
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self._status_label)
        
        main_layout.addWidget(header)
        
        # Tasks header
        tasks_header = QLabel("ZADANIA NA DZISIAJ")
        tasks_header.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        tasks_header.setStyleSheet("color: #00d4ff; margin-top: 10px;")
        main_layout.addWidget(tasks_header)
        
        # Scroll area for tasks
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: #2a2a4a;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #00d4ff;
                border-radius: 6px;
            }
        """)
        
        self._tasks_container = QWidget()
        self._tasks_layout = QVBoxLayout(self._tasks_container)
        self._tasks_layout.setSpacing(10)
        self._tasks_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        scroll.setWidget(self._tasks_container)
        main_layout.addWidget(scroll, 1)
        
        # Footer with alarms count
        footer = QFrame()
        footer.setStyleSheet("""
            QFrame {
                background-color: #16213e;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        footer_layout = QHBoxLayout(footer)
        
        self._alarms_label = QLabel("⚠ Brak aktywnych alarmów")
        self._alarms_label.setFont(QFont("Arial", 16))
        self._alarms_label.setStyleSheet("color: #00c853;")
        footer_layout.addWidget(self._alarms_label)
        
        self._worker_label = QLabel("Pracownik: —")
        self._worker_label.setFont(QFont("Arial", 16))
        self._worker_label.setStyleSheet("color: #a0a0a0;")
        self._worker_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        footer_layout.addWidget(self._worker_label)
        
        main_layout.addWidget(footer)
        
        # Timer for updating time
        self._clock_timer = QTimer(self)
        self._clock_timer.setInterval(1000)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start()
    
    def _setup_auto_refresh(self) -> None:
        """Setup auto-refresh timer for calendar events."""
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(30000)  # 30 seconds
        self._refresh_timer.timeout.connect(self._refresh_view)
        self._refresh_timer.start()
    
    def _update_clock(self) -> None:
        """Update the clock display."""
        now = datetime.now()
        self._time_label.setText(now.strftime("%H:%M:%S"))
        self._date_label.setText(now.strftime("%d %B %Y"))
        
        days_pl = [
            "Poniedziałek", "Wtorek", "Środa", "Czwartek",
            "Piątek", "Sobota", "Niedziela"
        ]
        self._day_label.setText(days_pl[now.weekday()])
    
    def _refresh_view(self) -> None:
        """Refresh the calendar events view."""
        # Clear existing tasks
        while self._tasks_layout.count():
            item = self._tasks_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Get today's events
        today = datetime.now().strftime("%Y-%m-%d")
        all_events = self._calendar_store.list_events()
        
        # Filter by station if set
        if self._station_filter:
            all_events = [
                e for e in all_events
                if str(getattr(e, "station", "") or "").strip().lower() == self._station_filter.lower()
                or str(getattr(e, "event_type", "") or "").strip().lower() == self._station_filter.lower()
            ]
        
        today_events = []
        overdue_events = []
        upcoming_events = []
        
        for event in all_events:
            event_date = str(getattr(event, "date", "") or "").strip()
            if not event_date:
                continue
            
            if event_date == today:
                today_events.append(event)
            elif event_date < today:
                overdue_events.append(event)
            elif len(upcoming_events) < 10:  # Limit upcoming events
                upcoming_events.append((event_date, event))
        
        # Sort upcoming events by date
        upcoming_events.sort(key=lambda x: x[0])
        
        # Show overdue events first (if any)
        if overdue_events:
            header = QLabel("PRZETERMINOWANE")
            header.setFont(QFont("Arial", 18, QFont.Weight.Bold))
            header.setStyleSheet("color: #ff5252; margin-top: 10px;")
            self._tasks_layout.addWidget(header)
            
            for event in overdue_events[:5]:
                self._add_task_card(event, is_overdue=True)
        
        # Show today's events
        if today_events:
            header = QLabel("DZISIAJ")
            header.setFont(QFont("Arial", 18, QFont.Weight.Bold))
            header.setStyleSheet("color: #00d4ff; margin-top: 10px;")
            self._tasks_layout.addWidget(header)
            
            for event in today_events:
                self._add_task_card(event, is_overdue=False)
        
        # Show upcoming events
        if upcoming_events:
            header = QLabel("NADCHODZĄCE")
            header.setFont(QFont("Arial", 18, QFont.Weight.Bold))
            header.setStyleSheet("color: #64b5f6; margin-top: 10px;")
            self._tasks_layout.addWidget(header)
            
            for _, event in upcoming_events:
                self._add_task_card(event, is_overdue=False, is_upcoming=True)
        
        # Show message if no events
        if not today_events and not overdue_events and not upcoming_events:
            no_events = QLabel("Brak zaplanowanych zadań")
            no_events.setFont(QFont("Arial", 20))
            no_events.setStyleSheet("color: #666; margin: 50px;")
            no_events.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._tasks_layout.addWidget(no_events)
    
    def _add_task_card(self, event: CalendarEvent, is_overdue: bool = False, is_upcoming: bool = False) -> None:
        """Add a task card to the view."""
        card = QFrame()
        
        # Color based on event type and status
        if is_overdue:
            bg_color = "#4a1a1a"
            border_color = "#ff5252"
        else:
            event_type = str(getattr(event, "event_type", "") or "").strip().lower()
            type_colors = {
                "montaz": ("#1a3a4a", "#00d4ff"),
                "produkcja": ("#2a3a1a", "#76ff03"),
                "projekt": ("#3a2a1a", "#ffab00"),
                "lakiernia": ("#3a1a3a", "#e040fb"),
                "default": ("#1a2a3a", "#64b5f6"),
            }
            bg_color, border_color = type_colors.get(event_type, type_colors["default"])
        
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border-left: 4px solid {border_color};
                border-radius: 8px;
                padding: 15px;
            }}
            QFrame:hover {{
                background-color: {border_color}22;
            }}
        """)
        
        card_layout = QHBoxLayout(card)
        card_layout.setSpacing(20)
        
        # Time
        time_label = QLabel(str(getattr(event, "date", "") or ""))
        time_label.setFont(QFont("Arial", 16))
        time_label.setStyleSheet("color: #a0a0a0;")
        time_label.setFixedWidth(120)
        card_layout.addWidget(time_label)
        
        # Title and details
        details = QVBoxLayout()
        
        title = QLabel(str(getattr(event, "title", "") or "Bez tytułu"))
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: #ffffff;")
        details.addWidget(title)
        
        # Worker and order info
        worker = str(getattr(event, "worker_name", "") or "").strip()
        order = str(getattr(event, "order_code", "") or "").strip()
        info_parts = []
        if worker:
            info_parts.append(f"👤 {worker}")
        if order:
            info_parts.append(f"📦 {order}")
        
        if info_parts:
            info_label = QLabel("  |  ".join(info_parts))
            info_label.setFont(QFont("Arial", 14))
            info_label.setStyleSheet("color: #a0a0a0;")
            details.addWidget(info_label)
        
        card_layout.addLayout(details, 1)
        
        # Event type badge
        event_type = str(getattr(event, "event_type", "") or "").strip()
        type_badge = QLabel(event_type.upper())
        type_badge.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        type_badge.setStyleSheet(f"""
            background-color: {border_color};
            color: #000000;
            padding: 5px 12px;
            border-radius: 12px;
        """)
        type_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(type_badge)
        
        self._tasks_layout.addWidget(card)
    
    def set_worker_filter(self, worker_name: str) -> None:
        """Set filter to show only specific worker's tasks."""
        self._worker_label.setText(f"Pracownik: {worker_name or '—'}")
        self._refresh_view()
    
    def update_alarms_count(self, critical: int, warning: int) -> None:
        """Update the alarms count display."""
        if critical > 0:
            self._alarms_label.setText(f"⚠ {critical} alarmów krytycznych!")
            self._alarms_label.setStyleSheet("color: #ff5252; font-weight: bold;")
        elif warning > 0:
            self._alarms_label.setText(f"⚠ {warning} ostrzeżeń")
            self._alarms_label.setStyleSheet("color: #ffab00;")
        else:
            self._alarms_label.setText("✓ Brak aktywnych alarmów")
            self._alarms_label.setStyleSheet("color: #00c853;")


def create_wall_view_for_screen(
    screen_index: int,
    worker_name: str = "",
    station: str = "",
) -> WallCalendarView:
    """
    Create a wall calendar view for a specific screen.
    
    Args:
        screen_index: Monitor index (0-3 for 4 monitors)
        worker_name: Optional worker filter
        station: Station filter (cnc, oklejanie, lakiernia, montaz)
        
    Returns:
        Configured WallCalendarView
    """
    view = WallCalendarView(station_filter=station)
    if worker_name:
        view.set_worker_filter(worker_name)
    return view


def create_production_kiosk_stations() -> dict[str, WallCalendarView]:
    """
    Create wall views for 4 production stations.
    Returns dict of station_name -> WallCalendarView.
    """
    return {
        "CNC": create_wall_view_for_screen(0, station="cnc"),
        "Oklejanie": create_wall_view_for_screen(1, station="oklejanie"),
        "Lakiernia": create_wall_view_for_screen(2, station="lakiernia"),
        "Montaż": create_wall_view_for_screen(3, station="montaz"),
    }
