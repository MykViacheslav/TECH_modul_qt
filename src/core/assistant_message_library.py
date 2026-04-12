"""
AssistantMessageLibrary — Role-aware, context-aware message templates.

Stores messages organized by:
- Role (wlasciciel, biuro, produkcja, magazyn)
- Active Tab (Nowe zamowienie, Wycena, Modul, etc.)
- Message Type (next_step, info, warning, critical)
- Level (info, next_step, warning, critical, restricted)

Ensures all responses are role-appropriate and permission-aware.
"""

from __future__ import annotations

from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class Message:
    """A structured assistant message."""
    text: str
    level: str  # info, next_step, warning, critical, restricted
    actions: list = None  # List of quick action dicts


# ============================================================================
# MESSAGE LIBRARY: GLOBAL STRUCTURE
# ============================================================================

MESSAGE_LIBRARY: Dict[str, Dict[str, Dict[str, Dict[str, Message]]]] = {
    # Tab: Nowe zamowienie (New Order)
    "nowe_zamowienie": {
        "wlasciciel": {
            "next_step": {
                "empty": Message(
                    text="Najpierw wybierz klienta z bazy, potem uzupełnij dane zamówienia.",
                    level="next_step"
                ),
                "client_selected": Message(
                    text="Świetnie. Teraz wpisz numer i nazwę zamówienia, potem dodaj pozycje do wyceny.",
                    level="next_step"
                ),
                "order_created": Message(
                    text="Zamówienie gotowe. Przejdź do wyceny lub dodaj załączniki.",
                    level="next_step"
                ),
            },
            "warning": {
                "no_client": Message(
                    text="Brakuje wybranego klienta.",
                    level="warning"
                ),
                "no_order_number": Message(
                    text="Brakuje numeru zamówienia.",
                    level="warning"
                ),
                "no_order_name": Message(
                    text="Brakuje nazwy zamówienia.",
                    level="warning"
                ),
            },
        },
        "biuro": {
            "next_step": {
                "empty": Message(
                    text="Najpierw wybierz klienta z bazy, potem uzupełnij dane zamówienia.",
                    level="next_step"
                ),
                "client_selected": Message(
                    text="Wpisz numer i nazwę zamówienia.",
                    level="next_step"
                ),
            },
            "warning": {
                "no_client": Message(
                    text="Brakuje wybranego klienta.",
                    level="warning"
                ),
            },
        },
        "produkcja": {
            "next_step": {
                "any": Message(
                    text="Ta zakładka jest dla biura. Twoje zadania są w Kalendarzu i Czasie pracy.",
                    level="info"
                ),
            },
        },
        "magazyn": {
            "next_step": {
                "any": Message(
                    text="Ta zakładka jest dla biura. Twoje materiały są w Zakupach.",
                    level="info"
                ),
            },
        },
    },

    # Tab: Wycena (Pricing)
    "wycena": {
        "wlasciciel": {
            "next_step": {
                "empty": Message(
                    text="Wybierz tryb wyceny: Projekt, Szybka wycena, albo Import 3D.",
                    level="next_step"
                ),
                "mode_selected": Message(
                    text="Dodaj pozycje i materiały do wyceny.",
                    level="next_step"
                ),
                "items_added": Message(
                    text="Przejrzyj rozkrój i usługi dodatkowe.",
                    level="next_step"
                ),
            },
            "warning": {
                "no_mode": Message(
                    text="Nie wybrano trybu wejścia do wyceny.",
                    level="warning"
                ),
                "no_items": Message(
                    text="Wycena jest pusta — dodaj pozycje.",
                    level="warning"
                ),
                "missing_mapping": Message(
                    text="Brakuje mapowania materiału dla jednej lub więcej pozycji.",
                    level="warning"
                ),
            },
        },
        "biuro": {
            "next_step": {
                "empty": Message(
                    text="Wybierz tryb wyceny.",
                    level="next_step"
                ),
            },
            "warning": {
                "no_mode": Message(
                    text="Nie wybrano trybu wyceny.",
                    level="warning"
                ),
            },
        },
        "produkcja": {
            "info": {
                "any": Message(
                    text="Nie masz dostępu do wyceny. Patrz: Kalendarz, zadania produkcyjne.",
                    level="info"
                ),
            },
        },
    },

    # Tab: Modul (Module Editor)
    "modul": {
        "wlasciciel": {
            "next_step": {
                "empty": Message(
                    text="Wybierz moduł z bazy lub utwórz nowy.",
                    level="next_step"
                ),
                "module_loaded": Message(
                    text="Edytujesz moduł. Zmień wymiary, materiały, fronty w lewym panelu.",
                    level="next_step"
                ),
            },
            "warning": {
                "no_module": Message(
                    text="Nie wczytano żadnego modułu.",
                    level="warning"
                ),
            },
        },
        "biuro": {
            "info": {
                "any": Message(
                    text="Ta zakładka jest dla projektantów. Zażądaj modułu od zespołu projektowego.",
                    level="info"
                ),
            },
        },
    },

    # Tab: Finanse (Finance) - RESTRICTED for non-authorized users
    "finanse": {
        "wlasciciel": {
            "info": {
                "cash": Message(
                    text="Stan kasy gotówkowej będzie wyświetlony po załadowaniu danych.",
                    level="info"
                ),
                "vat": Message(
                    text="Informacje o VAT będą dostępne po załadowaniu danych finansowych.",
                    level="info"
                ),
                "summary": Message(
                    text="Podsumowanie finansowe: przychody, koszty, wynik, VAT.",
                    level="info"
                ),
            },
        },
        "biuro": {
            "restricted": {
                "any": Message(
                    text="Nie masz uprawnień do danych finansowych.",
                    level="restricted"
                ),
            },
        },
        "produkcja": {
            "restricted": {
                "any": Message(
                    text="Nie masz uprawnień do danych finansowych.",
                    level="restricted"
                ),
            },
        },
        "magazyn": {
            "restricted": {
                "any": Message(
                    text="Nie masz uprawnień do danych finansowych.",
                    level="restricted"
                ),
            },
        },
    },

    # Tab: Kalendarz (Calendar)
    "kalendarz": {
        "wlasciciel": {
            "next_step": {
                "empty": Message(
                    text="Przeglądaj i zarządzaj harmonogramem produkcji i montażu.",
                    level="next_step"
                ),
            },
        },
        "produkcja": {
            "next_step": {
                "empty": Message(
                    text="Twoje zadania produkcyjne są tutaj. Kliknij na zadanie, aby zobaczyć szczegóły.",
                    level="next_step"
                ),
            },
        },
    },

    # Tab: Czas pracy (Work Time)
    "czas_pracy": {
        "produkcja": {
            "next_step": {
                "empty": Message(
                    text="Wpisz godziny pracy za dzisiaj i przypisz je do projektu.",
                    level="next_step"
                ),
            },
        },
    },

    # Global commands (not tab-specific)
    "global": {
        "wlasciciel": {
            "info": {
                "what_urgent": Message(
                    text="Ładuję dane alarmów...",
                    level="info"
                ),
            },
        },
        "biuro": {
            "info": {
                "what_urgent": Message(
                    text="Ładuję dane alarmów...",
                    level="info"
                ),
            },
        },
    },
}


def get_message(
    tab: str,
    role: str,
    msg_type: str,
    context_key: str = "empty",
) -> Optional[Message]:
    """
    Retrieve a message from the library.

    Args:
        tab: Active tab name (e.g., "nowe_zamowienie", "wycena")
        role: User role (e.g., "wlasciciel", "biuro")
        msg_type: Message category (e.g., "next_step", "warning")
        context_key: Specific context within the message type (e.g., "empty", "client_selected")

    Returns:
        Message object if found, None otherwise.
    """
    # Normalize tab name (convert spaces to underscores, lowercase)
    normalized_tab = tab.lower().replace(" ", "_").replace("ę", "e").replace("ł", "l")

    # Try exact match first
    if (
        normalized_tab in MESSAGE_LIBRARY
        and role in MESSAGE_LIBRARY[normalized_tab]
        and msg_type in MESSAGE_LIBRARY[normalized_tab][role]
    ):
        msg_dict = MESSAGE_LIBRARY[normalized_tab][role][msg_type]
        if context_key in msg_dict:
            return msg_dict[context_key]
        # Fallback to "any" or "empty"
        if "any" in msg_dict:
            return msg_dict["any"]
        if "empty" in msg_dict:
            return msg_dict["empty"]

    # Fallback to global messages
    if (
        "global" in MESSAGE_LIBRARY
        and role in MESSAGE_LIBRARY["global"]
        and msg_type in MESSAGE_LIBRARY["global"][role]
    ):
        msg_dict = MESSAGE_LIBRARY["global"][role][msg_type]
        if context_key in msg_dict:
            return msg_dict[context_key]
        if "any" in msg_dict:
            return msg_dict["any"]

    return None


def get_next_step_message(tab: str, role: str, context_key: str = "empty") -> Optional[Message]:
    """Get the 'next step' guidance for a specific tab and role."""
    return get_message(tab, role, "next_step", context_key)


def get_warning_message(tab: str, role: str, context_key: str = "default") -> Optional[Message]:
    """Get a warning message for a specific tab and role."""
    return get_message(tab, role, "warning", context_key)


def get_info_message(tab: str, role: str, context_key: str = "default") -> Optional[Message]:
    """Get an info message for a specific tab and role."""
    return get_message(tab, role, "info", context_key)


def get_restricted_message(role: str) -> Optional[Message]:
    """Get a generic 'access restricted' message for a role."""
    return get_message("global", role, "restricted", "default")
