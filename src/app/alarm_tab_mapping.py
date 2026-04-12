"""
Mapowanie kategorii alarmów do zakładek aplikacji.
Umożliwia wyświetlanie wskaźników alarmów na odpowiednich zakładkach.
"""

from __future__ import annotations

from src.domain.alarm_models import AlarmDef


# Mapowanie: kategoria alarmu -> lista zakładek które powinny pokazać wskaźnik
ALARM_CATEGORY_TO_TABS = {
    "terminy": ["Nowe zamowienie", "Kalendarz"],
    "projekty": ["Wycena", "OPERACJE"],  # OPERACJE zbiera sprawy wykonawcze i blokady
    "pracownicy": ["Pracownik", "Czas pracy"],
    "materialy": ["Baza materialu", "Bazy"],
    "platnosci": ["Nowe zamowienie", "Finanse", "OPERACJE"],
    "kasa": ["Finanse", "OPERACJE"],
    "faktury": ["Bazy"],
    "inne": ["Dashboard"],
}


def get_tabs_for_alarm(alarm: AlarmDef) -> list[str]:
    """
    Zwraca listę zakładek powiązanych z danym alarmem.

    Args:
        alarm: Obiekt alarmu

    Returns:
        Lista nazw zakładek które powinny pokazać wskaźnik alarmu
    """
    return ALARM_CATEGORY_TO_TABS.get(alarm.category, ["ALARMY"])


def get_alarm_badge_color(severity: str) -> str:
    """
    Zwraca kolor badge'a na podstawie severity alarmu.

    Args:
        severity: Poziom alarmu (krytyczny, ostrzezenie, info)

    Returns:
        Kod koloru HEX
    """
    severity_colors = {
        "krytyczny": "#dc2626",      # Czerwony
        "ostrzezenie": "#f59e0b",    # Bursztynowy
        "info": "#3b82f6",           # Niebieski
    }
    return severity_colors.get(severity, "#6b7280")  # Szary jako domyślny


def map_alarms_to_tabs(alarms: list[AlarmDef]) -> dict[str, int]:
    """
    Mapuje listę alarmów do liczby aktywnych alarmów na każdej zakładce.

    Args:
        alarms: Lista alarmów (zwykle nierozwiązanych)

    Returns:
        Dict {tab_title: liczba_alarmów}
    """
    tab_alarm_counts: dict[str, int] = {}

    for alarm in alarms:
        if alarm.is_resolved:
            continue

        for tab_title in get_tabs_for_alarm(alarm):
            tab_alarm_counts[tab_title] = tab_alarm_counts.get(tab_title, 0) + 1

    return tab_alarm_counts
