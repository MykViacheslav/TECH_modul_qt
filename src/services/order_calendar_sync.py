"""
Order to Calendar synchronization service.
Automatically creates calendar events from order stages.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from src.storage.calendar_event_store_json import CalendarEventStoreJson
from src.storage.order_store_json import OrderStoreJson


# Map order stages to calendar event types
STAGE_TO_EVENT_TYPE = {
    "Projekt": "projekt",
    "Zakup materialow": "zakup",
    "Zakup materiałów": "zakup",
    "Produkcja": "cnc",  # Default to CNC, can be overridden
    "W produkcji": "cnc",
    "Lakiernia": "lakiernia",
    "Montaz": "montaz",
    "Montaż": "montaz",
}

# Map calendar event types to stations for kiosk view
EVENT_TYPE_TO_STATION = {
    "projekt": "biuro",
    "zakup": "biuro",
    "cnc": "cnc",
    "oklejanie": "oklejanie",
    "lakiernia": "lakiernia",
    "montaz": "montaz",
}

# Date fields in order that map to stages
ORDER_DATE_FIELDS = [
    ("date_projekt", "Projekt", "projekt"),
    ("date_zakup_mat", "Zakup materiałów", "zakup"),
    ("date_produkcja", "Produkcja", "cnc"),
    ("date_lakiernia", "Lakiernia", "lakiernia"),
    ("date_montaz", "Montaż", "montaz"),
]


class OrderCalendarSync:
    """
    Syncs order stages to calendar events.
    Call sync_all() to update calendar based on current orders.
    """
    
    def __init__(self):
        self._order_store = OrderStoreJson()
        self._calendar_store = CalendarEventStoreJson()
    
    def sync_all(self, worker_filter: Optional[str] = None) -> int:
        """
        Sync all orders to calendar.
        Returns number of events created/updated.
        """
        count = 0
        orders = self._order_store.list_orders()
        
        for order in orders:
            count += self._sync_order(order, worker_filter)
        
        return count
    
    def sync_order(self, order_code: str) -> int:
        """Sync a specific order to calendar."""
        order = self._order_store.get(order_code)
        if order is None:
            return 0
        return self._sync_order(order)
    
    def _sync_order(self, order, worker_filter: Optional[str] = None) -> int:
        """Sync single order to calendar events."""
        count = 0
        
        order_code = str(getattr(order, "code", "") or "").strip()
        if not order_code:
            return 0
        
        worker_name = str(getattr(order, "worker_name", "") or "").strip()
        
        # Skip if worker filter doesn't match
        if worker_filter and worker_name != worker_filter:
            return 0
        
        client_name = str(getattr(order, "client_name", "") or "").strip()
        status = str(getattr(order, "status", "") or "").strip()
        current_stage_index = self._get_stage_index(status)
        
        for date_field, stage_name, event_type in ORDER_DATE_FIELDS:
            date_str = str(getattr(order, date_field, "") or "").strip()
            if not date_str:
                continue
            
            # Create event title
            title = f"{order_code} - {stage_name}"
            if client_name:
                title += f" ({client_name})"
            
            # Determine event status based on order status
            stage_index = self._get_stage_index(stage_name)
            
            if stage_index < current_stage_index:
                event_status = "zakończony"
            elif stage_index == current_stage_index:
                event_status = "w trakcie"
            else:
                event_status = "zaplanowany"
            
            # Check if event already exists
            existing = self._find_existing_event(order_code, stage_name, date_str)
            
            if existing:
                # Update existing event if needed
                if existing.get("status") != event_status:
                    existing["status"] = event_status
                    existing["worker_name"] = worker_name
                    self._calendar_store.save_event(existing)
                    count += 1
            else:
                # Create new event
                event = {
                    "id": f"order_{order_code}_{stage_name}_{date_str}",
                    "title": title,
                    "date": date_str,
                    "event_type": event_type,
                    "station": EVENT_TYPE_TO_STATION.get(event_type, ""),
                    "order_code": order_code,
                    "worker_name": worker_name,
                    "client_name": client_name,
                    "status": event_status,
                    "stage": stage_name,
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                self._calendar_store.save_event(event)
                count += 1
        
        return count
    
    def _get_stage_index(self, status: str) -> int:
        """Get numeric index for order stage (for comparison)."""
        status_lower = status.strip().lower()
        stage_order = [
            "nowe",
            "wycena",
            "wycena gotowa",
            "zaakceptowane",
            "zakup materialow",
            "zakup materiałów",
            "w produkcji",
            "produkcja",
            "lakiernia",
            "montaz",
            "montaż",
            "poprawki",
            "zakonczone",
            "zamknięte",
        ]
        
        try:
            return stage_order.index(status_lower)
        except ValueError:
            return -1
    
    def _find_existing_event(self, order_code: str, stage: str, date: str) -> Optional[dict]:
        """Find existing calendar event for order stage."""
        events = self._calendar_store.list_events()
        
        marker_prefix = f"order_{order_code}_{stage}_{date}"
        
        for event in events:
            event_id = str(getattr(event, "id", "") or "")
            if event_id.startswith(marker_prefix):
                # Convert event to dict if needed
                if hasattr(event, "__dict__"):
                    return event.__dict__
                return event
        
        return None
    
    def cleanup_past_events(self, days_old: int = 30) -> int:
        """Remove events older than specified days."""
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(days=days_old)
        cutoff_str = cutoff.strftime("%Y-%m-%d")
        
        events = self._calendar_store.list_events()
        removed = 0
        
        for event in events:
            event_date = str(getattr(event, "date", "") or "").strip()
            event_id = str(getattr(event, "id", "") or "")
            
            # Only remove order-generated events (they start with "order_")
            if not event_id.startswith("order_"):
                continue
            
            if event_date < cutoff_str:
                try:
                    self._calendar_store.delete_event(event_id)
                    removed += 1
                except Exception:
                    pass
        
        return removed


def sync_orders_to_calendar() -> int:
    """Convenience function to sync all orders to calendar."""
    sync = OrderCalendarSync()
    return sync.sync_all()


def sync_single_order(order_code: str) -> int:
    """Convenience function to sync a single order to calendar."""
    sync = OrderCalendarSync()
    return sync.sync_order(order_code)
