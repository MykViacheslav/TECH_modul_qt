"""
User role definitions and permission system for TECH_modul.
RBAC with 4 roles: Wlasciciel, Biuro, Produkcja, Magazyn.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, Set

from src.storage.access_control_store_json import AccessControlStoreJson

_ACCESS_STORE = AccessControlStoreJson()


class UserRole(Enum):
    """User roles with hierarchical permissions."""

    WLASCICIEL = "wlasciciel"  # Full access - owner, all features
    BIURO = "biuro"  # Office - orders, clients, pricing, reports
    PRODUKCJA = "produkcja"  # Production - production calendar, time tracking
    MAGAZYN = "magazyn"  # Warehouse - materials, inventory, purchases


# Role hierarchy (higher number = more permissions)
ROLE_HIERARCHY: Dict[str, int] = {
    "wlasciciel": 100,
    "biuro": 75,
    "magazyn": 60,
    "produkcja": 40,
}

# Role display labels
ROLE_LABELS: Dict[str, str] = {
    "wlasciciel": "Wlasciciel",
    "biuro": "Biuro",
    "produkcja": "Produkcja",
    "magazyn": "Magazyn",
}

# Legacy role names used in older parts of the app.
ROLE_ALIASES: Dict[str, str] = {
    "admin": "wlasciciel",
    "manager": "biuro",
    "operator": "produkcja",
    "viewer": "magazyn",
    "owner": "wlasciciel",
    "sales": "biuro",
    "production": "produkcja",
    "warehouse": "magazyn",
}

# All defined roles
ALL_ROLES = ("wlasciciel", "biuro", "produkcja", "magazyn")


# Permission matrix: view/edit/delete/export/approve
class Permission:
    """Permission identifiers with action types."""

    # === ZAMOWIENIA (Biuro/Wlasciciel) ===
    VIEW_ORDERS = "orders_view"
    EDIT_ORDERS = "orders_edit"
    DELETE_ORDERS = "orders_delete"
    APPROVE_ORDERS = "orders_approve"
    EXPORT_ORDERS = "orders_export"

    # === WYCENA (Biuro/Wlasciciel) ===
    VIEW_PRICING = "pricing_view"
    EDIT_PRICING = "pricing_edit"
    APPROVE_PRICING = "pricing_approve"

    # === MAGAZYN (Magazyn/Biuro/Wlasciciel) ===
    VIEW_INVENTORY = "inventory_view"
    EDIT_INVENTORY = "inventory_edit"  # Rezerwacja, spisanie, przyjecie
    CREATE_PURCHASE = "purchase_create"  # Tworzenie zakupow
    APPROVE_PURCHASE = "purchase_approve"
    EXPORT_INVENTORY = "inventory_export"

    # === PRODUKCJA (Produkcja/Biuro/Wlasciciel) ===
    VIEW_PRODUCTION = "production_view"
    EDIT_PRODUCTION = "production_edit"  # Zmiana statusow produkcji
    VIEW_CALENDAR = "calendar_view"
    EDIT_CALENDAR = "calendar_edit"  # Tylko Produkcja/Wlasciciel

    # === PRACOWNICY (Wlasciciel) ===
    VIEW_WORKERS = "workers_view"
    EDIT_WORKERS = "workers_edit"
    MANAGE_WORKERS = "workers_manage"  # Full HR

    # === ALARMY (Wszyscy view, Wybrani actions) ===
    VIEW_ALARMS = "alarms_view"
    RESOLVE_ALARMS = "alarms_resolve"
    CREATE_ALARM_ACTION = "alarms_action"  # Utworz zakup, spisz itp.

    # === USTAWIENIA (Wlasciciel) ===
    VIEW_SETTINGS = "settings_view"
    EDIT_SETTINGS = "settings_edit"
    MANAGE_SETTINGS = "settings_manage"
    MANAGE_USERS = "users_manage"

    # === EXPORT/REPORTS (Biuro/Wlasciciel) ===
    VIEW_REPORTS = "reports_view"
    EXPORT_DATA = "data_export"
    VIEW_AVATAR = "avatar_view"

    # === Legacy aliases (backward compatibility) ===
    # Keep old names mapped to current permission ids so stale mappings
    # cannot crash with AttributeError.
    VIEW_START = VIEW_ORDERS
    VIEW_NEW_ORDER = VIEW_ORDERS
    VIEW_QUOTATION = VIEW_PRICING
    VIEW_MODULE = VIEW_PRODUCTION
    VIEW_ASSEMBLY = VIEW_PRODUCTION
    VIEW_WALL = VIEW_PRODUCTION
    VIEW_WORK_TIME = VIEW_CALENDAR
    VIEW_EXPENSES = VIEW_REPORTS
    VIEW_DATABASES = VIEW_INVENTORY
    VIEW_MATERIALS = VIEW_INVENTORY
    VIEW_SERVICES = VIEW_PRICING
    VIEW_PLAN = VIEW_REPORTS
    VIEW_SCHEMAT = VIEW_REPORTS


# Matryca uprawnien: view / edit / delete / export / approve
ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    "wlasciciel": {
        # WLASCICIEL - wszystko
        Permission.VIEW_ORDERS, Permission.EDIT_ORDERS, Permission.DELETE_ORDERS,
        Permission.APPROVE_ORDERS, Permission.EXPORT_ORDERS,
        Permission.VIEW_PRICING, Permission.EDIT_PRICING, Permission.APPROVE_PRICING,
        Permission.VIEW_INVENTORY, Permission.EDIT_INVENTORY, Permission.CREATE_PURCHASE,
        Permission.APPROVE_PURCHASE, Permission.EXPORT_INVENTORY,
        Permission.VIEW_PRODUCTION, Permission.EDIT_PRODUCTION,
        Permission.VIEW_CALENDAR, Permission.EDIT_CALENDAR,
        Permission.VIEW_WORKERS, Permission.EDIT_WORKERS, Permission.MANAGE_WORKERS,
        Permission.VIEW_ALARMS, Permission.RESOLVE_ALARMS, Permission.CREATE_ALARM_ACTION,
        Permission.VIEW_SETTINGS, Permission.EDIT_SETTINGS, Permission.MANAGE_SETTINGS,
        Permission.MANAGE_USERS,
        Permission.VIEW_REPORTS, Permission.EXPORT_DATA,
        Permission.VIEW_AVATAR,
    },
    "biuro": {
        # BIURO - Zamowienia, wycena, klienci, raporty (bez ustawien i HR)
        Permission.VIEW_ORDERS, Permission.EDIT_ORDERS, Permission.DELETE_ORDERS,
        Permission.APPROVE_ORDERS, Permission.EXPORT_ORDERS,
        Permission.VIEW_PRICING, Permission.EDIT_PRICING, Permission.APPROVE_PRICING,
        Permission.VIEW_INVENTORY,  # Tylko podglad magazynu
        Permission.VIEW_PRODUCTION,  # Tylko podglad produkcji
        Permission.VIEW_CALENDAR,  # Tylko podglad kalendarza
        Permission.VIEW_WORKERS,  # Tylko lista pracownikow
        Permission.VIEW_ALARMS, Permission.RESOLVE_ALARMS, Permission.CREATE_ALARM_ACTION,
        Permission.VIEW_REPORTS, Permission.EXPORT_DATA,
        Permission.VIEW_AVATAR,
    },
    "magazyn": {
        # MAGAZYN - Pelna kontrola nad magazynem + podglad zamowien
        Permission.VIEW_ORDERS,  # Podglad zamowien (do kontekstu)
        Permission.VIEW_INVENTORY, Permission.EDIT_INVENTORY,  # Full magazyn
        Permission.CREATE_PURCHASE, Permission.APPROVE_PURCHASE,  # Zakupy
        Permission.EXPORT_INVENTORY,
        Permission.VIEW_PRODUCTION,  # Podglad co jest w produkcji
        Permission.VIEW_CALENDAR,
        Permission.VIEW_ALARMS, Permission.RESOLVE_ALARMS, Permission.CREATE_ALARM_ACTION,
        Permission.VIEW_AVATAR,
    },
    "produkcja": {
        # PRODUKCJA - Kalendarz produkcji, zmiana statusow, swoj czas pracy
        Permission.VIEW_ORDERS,  # Podglad zamowien (do kontekstu)
        Permission.VIEW_PRODUCTION, Permission.EDIT_PRODUCTION,  # Statusy produkcji
        Permission.VIEW_CALENDAR, Permission.EDIT_CALENDAR,  # Swoj kalendarz
        Permission.VIEW_WORKERS,  # Lista (tylko podglad)
        Permission.VIEW_INVENTORY,  # Podglad dostepnych materialow
        Permission.VIEW_ALARMS,  # Podglad alarmow
        Permission.VIEW_AVATAR,
    },
}


def has_permission(role: str, permission: str) -> bool:
    """
    Check if a role has a specific permission.

    Args:
        role: User role (admin, manager, operator, viewer)
        permission: Permission identifier

    Returns:
        True if role has the permission, False otherwise
    """
    role = normalize_role(role)
    if not role or role not in ROLE_PERMISSIONS:
        return False
    return permission in ROLE_PERMISSIONS.get(role, set())


def can_access_tab_by_role(role: str, tab_title: str) -> bool:
    """
    Check if a role can access a specific tab (role matrix only).

    Args:
        role: User role
        tab_title: Tab title

    Returns:
        True if role can access the tab
    """

    def _permission_by_name(*names: str) -> str | None:
        for name in names:
            value = getattr(Permission, name, None)
            if isinstance(value, str):
                return value
        return None

    tab_permission_map = {
        # Sales
        "Start": _permission_by_name("VIEW_START", "VIEW_ORDERS"),
        "Briefing": _permission_by_name("VIEW_START", "VIEW_ORDERS"),
        "Nowe zamowienie": _permission_by_name("VIEW_NEW_ORDER", "VIEW_ORDERS"),
        "Nowe zamówienie": _permission_by_name("VIEW_NEW_ORDER", "VIEW_ORDERS"),
        "Wycena": _permission_by_name("VIEW_QUOTATION", "VIEW_PRICING"),
        "Sekcje do wyceny": _permission_by_name("VIEW_QUOTATION", "VIEW_PRICING"),
        # Service tab should be available in operational roles as well.
        "Uslugi": _permission_by_name("VIEW_ORDERS", "VIEW_SERVICES", "VIEW_PRICING"),

        # Project
        "Modul": _permission_by_name("VIEW_MODULE", "VIEW_PRODUCTION"),
        "Moduł": _permission_by_name("VIEW_MODULE", "VIEW_PRODUCTION"),
        "Komplet": _permission_by_name("VIEW_ASSEMBLY", "VIEW_PRODUCTION"),
        "Sciana": _permission_by_name("VIEW_WALL", "VIEW_PRODUCTION"),
        "Ściana": _permission_by_name("VIEW_WALL", "VIEW_PRODUCTION"),

        # Company
        "Dashboard": _permission_by_name("VIEW_REPORTS"),
        "Stanowiska": _permission_by_name("VIEW_CALENDAR", "VIEW_PRODUCTION"),
        "Kalendarz": _permission_by_name("VIEW_CALENDAR"),
        "Czas pracy": _permission_by_name("VIEW_WORK_TIME", "VIEW_CALENDAR"),
        "Wydatki stale firmy": _permission_by_name("VIEW_EXPENSES", "VIEW_REPORTS"),
        "Wydatki stałe firmy": _permission_by_name("VIEW_EXPENSES", "VIEW_REPORTS"),
        "Wydatki zmienne": _permission_by_name("VIEW_EXPENSES", "VIEW_REPORTS"),
        "Pracownik": _permission_by_name("VIEW_WORKERS"),
        "ALARMY": _permission_by_name("VIEW_ALARMS"),
        "Zakupy": _permission_by_name("CREATE_PURCHASE", "VIEW_INVENTORY"),

        # Databases
        "Bazy": _permission_by_name("VIEW_DATABASES", "VIEW_INVENTORY"),
        "Klienci": _permission_by_name("VIEW_ORDERS", "VIEW_DATABASES"),
        "Zamowienia": _permission_by_name("VIEW_ORDERS", "VIEW_DATABASES"),
        "Pracownicy": _permission_by_name("VIEW_WORKERS", "VIEW_DATABASES"),
        "BAZA_modul": _permission_by_name("VIEW_DATABASES", "VIEW_INVENTORY"),
        "Baza materialu": _permission_by_name("VIEW_MATERIALS", "VIEW_INVENTORY"),
        "Receptura": _permission_by_name("VIEW_MATERIALS", "VIEW_INVENTORY"),
        "Baza faktur": _permission_by_name("VIEW_MATERIALS", "VIEW_INVENTORY"),
        "Baza materiału": _permission_by_name("VIEW_MATERIALS", "VIEW_INVENTORY"),
        "Baza szybkich wycen": _permission_by_name("VIEW_SERVICES", "VIEW_PRICING"),

        # Other
        # Informational tabs should not block access to the whole "Inne" group.
        "Plan": _permission_by_name("VIEW_ORDERS", "VIEW_PLAN", "VIEW_REPORTS"),
        "Schemat": _permission_by_name("VIEW_ORDERS", "VIEW_SCHEMAT", "VIEW_REPORTS"),
        "QR Telefon": _permission_by_name("VIEW_ORDERS", "VIEW_PLAN", "VIEW_REPORTS"),
        "Avatar": _permission_by_name("VIEW_AVATAR"),
        "Ustawienia": _permission_by_name("VIEW_SETTINGS"),
        "Uprawnienia": _permission_by_name("MANAGE_USERS"),
    }

    permission = tab_permission_map.get(tab_title)
    if not permission:
        return True  # Unknown tab - allow access by default
    return has_permission(role, permission)


def can_access_tab(role: str, tab_title: str, worker_name: str = "") -> bool:
    """
    Check if a user can access a specific tab.
    Per-user overrides from access_control.json have priority over role defaults.
    """
    override = None
    if str(worker_name or "").strip():
        override = _ACCESS_STORE.get_tab_override_for_worker(worker_name, tab_title)
    if isinstance(override, bool):
        return override
    return can_access_tab_by_role(role, tab_title)


def get_role_level(role: str) -> int:
    """
    Get the hierarchy level of a role.
    Higher number means more permissions.

    Args:
        role: User role

    Returns:
        Role level (0 if unknown)
    """
    role = normalize_role(role)
    return ROLE_HIERARCHY.get(role, 0)


def normalize_role(role: str) -> str:
    """Normalize legacy and mixed role names to canonical RBAC roles."""
    role_norm = str(role or "").strip().lower()
    return ROLE_ALIASES.get(role_norm, role_norm)


def can_assign_role(assigner_role: str, target_role: str) -> bool:
    """
    Check if a user can assign a role to another user.
    Users can only assign roles with lower hierarchy than their own.

    Args:
        assigner_role: Role of the user assigning
        target_role: Role being assigned

    Returns:
        True if assignment is allowed
    """
    return get_role_level(assigner_role) > get_role_level(target_role)

