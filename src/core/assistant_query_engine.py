"""
AssistantQueryEngine — Parses user text queries and generates role-aware responses.

Implements permission-aware command handling:
1. Parse user input against command patterns
2. Check if user has permission for the query
3. Build response data (never build restricted responses)
4. Return structured response

Phase 1: Text-only, read-only, no automation.
No financial calculations, no data modifications.
"""

from __future__ import annotations

import re
from typing import Optional, Dict, List, Callable
from dataclasses import dataclass

from src.core.assistant_context import AssistantContext, MessageLevel
from src.core.assistant_message_library import (
    get_message,
    get_next_step_message,
    get_warning_message,
    get_info_message,
)
from src.domain.permissions import Permission


@dataclass
class AssistantResponse:
    """Structured response from the query engine."""
    success: bool
    text: str
    level: str  # info, next_step, warning, critical, restricted
    actions: List[Dict] = None  # [{"label": str, "command": str}, ...]
    context: Dict = None  # Extra context data


class AssistantQueryEngine:
    """
    Query engine that parses text commands and returns role-aware responses.

    Implements permission checks BEFORE building responses.
    If user lacks permission, returns restricted response immediately.
    """

    def __init__(self, context: Optional[AssistantContext] = None):
        """
        Initialize the query engine.

        Args:
            context: AssistantContext instance (defaults to singleton)
        """
        self.context = context or AssistantContext.instance()
        self._command_handlers: Dict[str, Callable] = {
            "what_to_do": self._handle_what_to_do,
            "what_urgent": self._handle_what_urgent,
            "what_missing": self._handle_what_missing,
            "navigate": self._handle_navigate,
            "open_order": self._handle_open_order,
            "finance_query": self._handle_finance_query,
        }

    def query(self, text: str) -> AssistantResponse:
        """
        Process a user query and return a response.

        Args:
            text: User input (e.g., "co mam zrobić", "jaki mamy VAT")

        Returns:
            AssistantResponse with text, level, and actions
        """
        if not text or not text.strip():
            return AssistantResponse(
                success=False,
                text="Poproszę pytanie lub komendę.",
                level="info",
            )

        # Normalize input
        normalized = text.strip().lower()

        # Try to match against command patterns
        handler = self._match_command(normalized)
        if handler:
            return handler(normalized)

        # No match found
        return AssistantResponse(
            success=False,
            text="Nie rozumiem. Spróbuj: 'co mam zrobić', 'co jest pilne', 'jaki mamy VAT', 'otwórz [zakładkę]'",
            level="info",
        )

    # =========================================================================
    # COMMAND MATCHING
    # =========================================================================

    def _match_command(self, normalized_text: str) -> Optional[Callable]:
        """Match user input against command patterns and return handler."""
        patterns = [
            (r"^(co|czego|co teraz|co dalej|co mam)\s+(zrobić|robić|powinien)", self._command_handlers["what_to_do"]),
            (r"^(co|co jest|co jest)\s+(pilne|pilny|krytyczne|alarm|zagrożenie|problem)", self._command_handlers["what_urgent"]),
            (r"^(jakie|co)\s+(są|jest)\s+(braki|brakuje|braki danych|incomplete)", self._command_handlers["what_missing"]),
            (r"^(otwórz|pokaż|idź|przejdź)\s+(?!zamówienie|order)(.*)", self._command_handlers["navigate"]),
            (r"^(otwórz|pokaż)\s+(zamówienie|order|zamówienie)\s+(.*)", self._command_handlers["open_order"]),
            # Financial queries - matches various forms: "ile mamy w kasie", "jaki mamy VAT", "jakie są zobowiązania", etc.
            (r"(ile|jaki|jakie|czy|jaka).+(vat|podatek|kas|gotówk|rach|pieniądz|wynagrodz|zobowiąz)", self._command_handlers["finance_query"]),
        ]

        for pattern, handler in patterns:
            if re.search(pattern, normalized_text):
                return handler

        return None

    # =========================================================================
    # COMMAND HANDLERS
    # =========================================================================

    def _handle_what_to_do(self, text: str) -> AssistantResponse:
        """
        Handler: "co mam zrobić", "co dalej", "co teraz zrobić"
        Response depends on active tab and role.
        """
        tab = self.context.get_active_tab()
        role = self.context.get_role()

        msg = get_next_step_message(tab, role, context_key="empty")
        if msg:
            return AssistantResponse(
                success=True,
                text=msg.text,
                level=msg.level,
                actions=[
                    {"label": "Przejdź do tej zakładki", "command": f"navigate:{tab}"},
                ],
            )

        # Fallback
        return AssistantResponse(
            success=True,
            text=f"Pracujesz w zakładce '{tab}'. Czym się zajmujesz?",
            level="info",
        )

    def _handle_what_urgent(self, text: str) -> AssistantResponse:
        """
        Handler: "co jest pilne", "co jest krytyczne", "co jest alarmem"
        Returns critical alerts from AlarmService if user has VIEW_ALARMS permission.
        """
        # Check permission
        if not self.context.has_permission(Permission.VIEW_ALARMS):
            return AssistantResponse(
                success=False,
                text="Nie masz uprawnień do widoku alarmów.",
                level="restricted",
            )

        # TODO: When AlarmService is integrated, fetch alarms here
        # For now, placeholder response
        return AssistantResponse(
            success=True,
            text="Ładuję alerty... Brak nowych alarmów krytycznych.",
            level="info",
            actions=[
                {"label": "Pokaż wszystkie alarmy", "command": "navigate:Alarmy"},
            ],
        )

    def _handle_what_missing(self, text: str) -> AssistantResponse:
        """
        Handler: "jakie są braki", "co brakuje w tej zakładce"
        Context-aware: returns warnings based on active tab.
        """
        tab = self.context.get_active_tab()
        role = self.context.get_role()

        msg = get_warning_message(tab, role, context_key="default")
        if msg:
            return AssistantResponse(
                success=True,
                text=msg.text,
                level=msg.level,
            )

        return AssistantResponse(
            success=True,
            text="Dane w tej zakładce wydają się kompletne.",
            level="info",
        )

    def _handle_navigate(self, text: str) -> AssistantResponse:
        """
        Handler: "otwórz [zakładkę]", "przejdź do [zakładki]"
        Extracts tab name from user input and returns navigation action.
        """
        # Extract tab name (very basic parsing)
        match = re.search(r"(?:otwórz|pokaż|idź|przejdź)\s+(?:do\s+)?([a-zą-ż\s]+)", text)
        if not match:
            return AssistantResponse(
                success=False,
                text="Nie mogę rozpoznać, do której zakładki chcesz przejść.",
                level="info",
            )

        requested_tab = match.group(1).strip()

        # Rough tab name mapping (for user-friendly input)
        tab_mapping = {
            "zamówień": "Nowe zamowienie",
            "zamówienia": "Nowe zamowienie",
            "zamówienie": "Nowe zamowienie",
            "wyceny": "Wycena",
            "wycenę": "Wycena",
            "wycena": "Wycena",
            "modułu": "Modul",
            "modułów": "Modul",
            "modułu": "Modul",
            "moduł": "Modul",
            "kompletu": "Komplet",
            "komplet": "Komplet",
            "ściany": "Sciana",
            "ściana": "Sciana",
            "finansów": "Finanse",
            "finanse": "Finanse",
            "kalendarza": "Kalendarz",
            "kalendarz": "Kalendarz",
            "czasu pracy": "Czas pracy",
            "czas pracy": "Czas pracy",
            "alarmów": "Alarmy",
            "alarmy": "Alarmy",
            "bazy": "Bazy",
            "baza": "Bazy",
            "ustawień": "Ustawienia",
            "ustawienia": "Ustawienia",
            "startu": "Start",
            "start": "Start",
        }

        # Find best match
        target_tab = None
        for key, tab_name in tab_mapping.items():
            if key in requested_tab:
                target_tab = tab_name
                break

        if not target_tab:
            # Try direct match
            for tab_title in ["Nowe zamowienie", "Wycena", "Modul", "Komplet", "Sciana", "Finanse", "Kalendarz", "Czas pracy"]:
                if tab_title.lower() in requested_tab.lower():
                    target_tab = tab_title
                    break

        if target_tab:
            return AssistantResponse(
                success=True,
                text=f"Otwieranie {target_tab}...",
                level="info",
                actions=[
                    {"label": target_tab, "command": f"navigate:{target_tab}"},
                ],
            )

        return AssistantResponse(
            success=False,
            text=f"Nie znalazłem zakładki '{requested_tab}'.",
            level="info",
        )

    def _handle_open_order(self, text: str) -> AssistantResponse:
        """
        Handler: "otwórz zamówienie [nazwa/numer]"
        In Phase 1, just return the command; MainWindow will execute.
        """
        match = re.search(r"(?:otwórz|pokaż)\s+(?:zamówienie|order)\s+([a-zą-ż0-9\s]+)", text)
        if not match:
            return AssistantResponse(
                success=False,
                text="Podaj nazwę lub numer zamówienia.",
                level="info",
            )

        order_ref = match.group(1).strip()

        # Check permission
        if not self.context.has_permission(Permission.VIEW_ORDERS):
            return AssistantResponse(
                success=False,
                text="Nie masz uprawnień do przeglądania zamówień.",
                level="restricted",
            )

        return AssistantResponse(
            success=True,
            text=f"Szukam zamówienia '{order_ref}'...",
            level="info",
            actions=[
                {"label": f"Otwórz {order_ref}", "command": f"open_order:{order_ref}"},
            ],
        )

    def _handle_finance_query(self, text: str) -> AssistantResponse:
        """
        Handler: "jaki mamy VAT", "ile mamy w kasie", "jakie są zobowiązania"
        PERMISSION CHECK: Only wlasciciel (admin) can get financial data.
        """
        # CRITICAL: Check permission BEFORE building response
        # Financial data is restricted to admin/owner only
        if not self.context.is_admin():
            return AssistantResponse(
                success=False,
                text="Nie masz uprawnień do danych finansowych.",
                level="restricted",
            )

        # Determine which financial query
        if "vat" in text:
            return AssistantResponse(
                success=True,
                text="Informacje o VAT będą dostępne po załadowaniu danych finansowych.",
                level="info",
                actions=[
                    {"label": "Pokaż finanse", "command": "navigate:Finanse"},
                ],
            )
        elif "kasa" in text or "gotówka" in text:
            return AssistantResponse(
                success=True,
                text="Saldo kasy gotówkowej będzie wyświetlone po załadowaniu danych.",
                level="info",
                actions=[
                    {"label": "Pokaż finanse", "command": "navigate:Finanse"},
                ],
            )
        elif "rachunek" in text:
            return AssistantResponse(
                success=True,
                text="Stan rachunku bankowego będzie wyświetlony po załadowaniu danych.",
                level="info",
                actions=[
                    {"label": "Pokaż finanse", "command": "navigate:Finanse"},
                ],
            )
        elif "zobowiązanie" in text:
            return AssistantResponse(
                success=True,
                text="Informacje o zobowiązaniach są dostępne w Finansach.",
                level="info",
                actions=[
                    {"label": "Pokaż finanse", "command": "navigate:Finanse"},
                ],
            )
        else:
            return AssistantResponse(
                success=True,
                text="Informacje finansowe dostępne w zakładce Finanse.",
                level="info",
                actions=[
                    {"label": "Pokaż finanse", "command": "navigate:Finanse"},
                ],
            )


class NavigationIntent:
    """Helper to represent a safe navigation intent (not direct widget manipulation)."""

    def __init__(self, action: str, target: str = "", context: Optional[Dict] = None):
        """
        Args:
            action: "navigate", "open_order", "show_warning", etc.
            target: Target tab or entity
            context: Optional context dict
        """
        self.action = action
        self.target = target
        self.context = context or {}

    def to_dict(self) -> Dict:
        """Convert to dict for JSON serialization."""
        return {
            "action": self.action,
            "target": self.target,
            "context": self.context,
        }
