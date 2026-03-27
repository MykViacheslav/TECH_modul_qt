"""
Skaner powiadomień — analizuje dane aplikacji i zwraca listę alertów.
Wywoływany przez FloatingAssistantAvatar co kilka minut.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import TYPE_CHECKING


@dataclass
class Alert:
    level: str          # "error" | "warning" | "info"
    title: str          # krótki tytuł (1 linia)
    detail: str = ""    # opcjonalny dłuższy opis

    @property
    def icon(self) -> str:
        return {"error": "⛔", "warning": "⚠️", "info": "ℹ️"}.get(self.level, "•")

    def short(self) -> str:
        return f"{self.icon} {self.title}"


def scan_alerts() -> list[Alert]:
    """Skanuje wszystkie dostępne dane i zwraca listę alertów."""
    alerts: list[Alert] = []
    _check_orders(alerts)
    _check_calendar(alerts)
    _check_expenses(alerts)
    return alerts


# ---------------------------------------------------------------------------
# Zamówienia
# ---------------------------------------------------------------------------

def _check_orders(alerts: list[Alert]) -> None:
    try:
        from src.storage.order_store_json import OrderStoreJson
        orders = OrderStoreJson().list_orders()
    except Exception:
        return

    today = date.today().isoformat()

    active_statuses = {
        "Nowe", "W trakcie", "Wycena", "Do wyceny",
        "Czeka na material", "Produkcja", "Montaz",
    }

    unpaid_total = 0.0
    unpaid_orders: list[str] = []

    stuck_orders: list[str] = []

    for order in orders:
        if order.status in ("Zamknięte", "Anulowane", "Zrealizowane"):
            continue

        # Nieopłacone raty dla aktywnych zamówień
        for payment in order.customer_payments:
            if not payment.get("paid", False):
                amount = float(payment.get("amount", 0.0))
                if amount > 0:
                    unpaid_total += amount
                    if order.code not in unpaid_orders:
                        unpaid_orders.append(order.code)

        # Zamówienia utknięte — status aktywny, progress = 0
        if (
            order.status in active_statuses
            and order.progress_percent == 0.0
            and order.code
        ):
            stuck_orders.append(order.code)

    if unpaid_orders:
        count = len(unpaid_orders)
        label = f"{count} zamówieni{'e' if count == 1 else 'a' if count in (2, 3, 4) else 'ń'}"
        alerts.append(Alert(
            level="warning",
            title=f"Nieopłacone raty: {label}",
            detail=f"Łącznie {unpaid_total:,.0f} zł do odebrania. Zamówienia: {', '.join(unpaid_orders[:5])}{'...' if len(unpaid_orders) > 5 else ''}",
        ))

    if len(stuck_orders) >= 3:
        alerts.append(Alert(
            level="info",
            title=f"{len(stuck_orders)} zamówień bez postępu (0%)",
            detail=f"Sprawdź czy nie wymagają uwagi: {', '.join(stuck_orders[:5])}",
        ))


# ---------------------------------------------------------------------------
# Kalendarz — dzisiaj i jutro
# ---------------------------------------------------------------------------

def _check_calendar(alerts: list[Alert]) -> None:
    try:
        from src.storage.calendar_event_store_json import CalendarEventStoreJson
        events = CalendarEventStoreJson().list_events()
    except Exception:
        return

    today = date.today()
    tomorrow = today + timedelta(days=1)
    today_str = today.isoformat()
    tomorrow_str = tomorrow.isoformat()

    today_events = [e for e in events if e.date == today_str]
    tomorrow_events = [e for e in events if e.date == tomorrow_str]

    if today_events:
        count = len(today_events)
        label = f"{count} zdarzeni{'e' if count == 1 else 'a' if count in (2, 3, 4) else 'ń'}"
        titles = ", ".join(e.title for e in today_events[:3])
        alerts.append(Alert(
            level="info",
            title=f"Dziś w kalendarzu: {label}",
            detail=titles + ("..." if count > 3 else ""),
        ))

    if tomorrow_events:
        count = len(tomorrow_events)
        label = f"{count} zdarzeni{'e' if count == 1 else 'a' if count in (2, 3, 4) else 'ń'}"
        titles = ", ".join(e.title for e in tomorrow_events[:3])
        alerts.append(Alert(
            level="info",
            title=f"Jutro w kalendarzu: {label}",
            detail=titles + ("..." if count > 3 else ""),
        ))


# ---------------------------------------------------------------------------
# Wydatki firmowe
# ---------------------------------------------------------------------------

def _check_expenses(alerts: list[Alert]) -> None:
    try:
        from src.storage.company_expenses_store_json import CompanyExpensesStoreJson
        store = CompanyExpensesStoreJson()
        fixed_monthly = store.sum_items("fixed")
    except Exception:
        return

    if fixed_monthly > 30_000:
        alerts.append(Alert(
            level="warning",
            title=f"Wysokie stałe koszty: {fixed_monthly:,.0f} zł/mies.",
            detail="Stałe koszty firmy przekraczają 30 000 zł miesięcznie. Sprawdź budżet.",
        ))
    elif fixed_monthly > 15_000:
        alerts.append(Alert(
            level="info",
            title=f"Stałe koszty: {fixed_monthly:,.0f} zł/mies.",
        ))
