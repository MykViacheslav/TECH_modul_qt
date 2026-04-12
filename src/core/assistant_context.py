"""
AssistantContext — Manages the contextual state for the assistant.

This singleton tracks:
- User identity (worker_name, role, permissions)
- Active navigation context (tab, subtab)
- Selected entities (order, project, client, module, assembly, wall)

The context is source-independent and decoupled from MainWindow.
It is updated via setters that can be called from MainWindow or tab widgets.
"""

from __future__ import annotations

from typing import Optional, Set
from dataclasses import dataclass, field
from enum import Enum

from src.domain.permissions import (
    UserRole,
    Permission,
    has_permission,
    normalize_role,
    ROLE_HIERARCHY,
)


class MessageLevel(Enum):
    """Message severity/type levels."""
    INFO = "info"
    NEXT_STEP = "next_step"
    WARNING = "warning"
    CRITICAL = "critical"
    RESTRICTED = "restricted"


@dataclass
class AssistantContextData:
    """Immutable snapshot of current assistant context."""
    # User identity
    worker_name: str = ""
    display_name: str = ""
    role: str = "produkcja"
    permissions: Set[str] = field(default_factory=set)

    # Navigation context
    active_tab: str = "Start"
    active_subtab: Optional[str] = None
    current_route: Optional[str] = None

    # Selected entities
    selected_project_id: Optional[str] = None
    selected_order_id: Optional[str] = None
    selected_order_code: Optional[str] = None
    selected_client_id: Optional[str] = None

    # Active entity in editors
    active_module_id: Optional[str] = None
    active_assembly_id: Optional[str] = None
    active_wall_id: Optional[str] = None

    def get_context_dict(self) -> dict:
        """Return context as a dictionary for serialization/logging."""
        return {
            "worker_name": self.worker_name,
            "display_name": self.display_name,
            "role": self.role,
            "active_tab": self.active_tab,
            "active_subtab": self.active_subtab,
            "selected_order_id": self.selected_order_id,
            "selected_order_code": self.selected_order_code,
            "selected_project_id": self.selected_project_id,
            "selected_client_id": self.selected_client_id,
            "active_module_id": self.active_module_id,
            "active_assembly_id": self.active_assembly_id,
            "active_wall_id": self.active_wall_id,
        }


class AssistantContext:
    """
    Singleton context manager for the assistant.

    Tracks user identity, role, permissions, and active context (tab, selected entities).
    This class is source-independent and designed for extensibility (e.g., session management).
    """

    _instance: Optional[AssistantContext] = None

    def __init__(self):
        """Initialize context with empty/default values."""
        self._data = AssistantContextData()

    @classmethod
    def instance(cls) -> AssistantContext:
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = AssistantContext()
        return cls._instance

    # =========================================================================
    # USER IDENTITY SETTERS
    # =========================================================================

    def set_user(
        self,
        worker_name: str,
        role: str,
        display_name: Optional[str] = None,
        permissions: Optional[Set[str]] = None,
    ) -> None:
        """
        Set the current user identity and permissions.

        Args:
            worker_name: Logged-in worker name (primary key)
            role: User role (wlasciciel, biuro, produkcja, magazyn)
            display_name: Optional display name (if different from worker_name)
            permissions: Optional set of permissions; if None, computed from role
        """
        self._data.worker_name = str(worker_name or "").strip()
        self._data.display_name = str(display_name or worker_name or "").strip()
        self._data.role = normalize_role(str(role or "produkcja"))

        # If permissions not provided, derive from role
        if permissions is None:
            self._data.permissions = self._compute_permissions_for_role(self._data.role)
        else:
            self._data.permissions = set(permissions)

    def set_role(self, role: str) -> None:
        """Update the current user's role and recompute permissions."""
        self._data.role = normalize_role(str(role or "produkcja"))
        self._data.permissions = self._compute_permissions_for_role(self._data.role)

    def clear_user(self) -> None:
        """Clear the current user (e.g., on logout)."""
        self._data.worker_name = ""
        self._data.display_name = ""
        self._data.role = "produkcja"
        self._data.permissions.clear()
        # Note: Context (tab, order, etc.) is NOT cleared on logout

    # =========================================================================
    # NAVIGATION CONTEXT SETTERS
    # =========================================================================

    def set_active_tab(self, tab_title: str, subtab: Optional[str] = None) -> None:
        """
        Set the currently active tab.

        Args:
            tab_title: Name of the active tab (e.g., "Nowe zamowienie", "Modul")
            subtab: Optional subtab name within the tab
        """
        self._data.active_tab = str(tab_title or "Start").strip()
        self._data.active_subtab = subtab
        self._data.current_route = None  # Clear route when tab changes

    def set_route(self, route: str) -> None:
        """Set the current route/path (for complex nested navigation)."""
        self._data.current_route = str(route or "").strip() or None

    # =========================================================================
    # SELECTED ENTITY SETTERS
    # =========================================================================

    def set_selected_order(
        self,
        order_id: Optional[str] = None,
        order_code: Optional[str] = None,
    ) -> None:
        """
        Set the currently selected order.

        Args:
            order_id: Sequential order ID
            order_code: Order code (unique key in store)
        """
        self._data.selected_order_id = order_id
        self._data.selected_order_code = order_code

    def set_selected_project(self, project_id: Optional[str] = None) -> None:
        """Set the currently selected project."""
        self._data.selected_project_id = project_id

    def set_selected_client(self, client_id: Optional[str] = None) -> None:
        """Set the currently selected client."""
        self._data.selected_client_id = client_id

    # =========================================================================
    # ACTIVE ENTITY SETTERS (in editors)
    # =========================================================================

    def set_active_module(self, module_id: Optional[str] = None) -> None:
        """Set the currently active module in the module editor."""
        self._data.active_module_id = module_id

    def set_active_assembly(self, assembly_id: Optional[str] = None) -> None:
        """Set the currently active assembly in the assembly editor."""
        self._data.active_assembly_id = assembly_id

    def set_active_wall(self, wall_id: Optional[str] = None) -> None:
        """Set the currently active wall in the wall editor."""
        self._data.active_wall_id = wall_id

    # =========================================================================
    # GETTERS
    # =========================================================================

    def get_worker_name(self) -> str:
        """Get the current worker name."""
        return self._data.worker_name

    def get_display_name(self) -> str:
        """Get the current display name."""
        return self._data.display_name or self._data.worker_name

    def get_role(self) -> str:
        """Get the current user's role."""
        return self._data.role

    def get_permissions(self) -> Set[str]:
        """Get the current user's permissions."""
        return self._data.permissions.copy()

    def get_active_tab(self) -> str:
        """Get the currently active tab."""
        return self._data.active_tab

    def get_active_subtab(self) -> Optional[str]:
        """Get the currently active subtab (if any)."""
        return self._data.active_subtab

    def get_selected_order_code(self) -> Optional[str]:
        """Get the code of the currently selected order."""
        return self._data.selected_order_code

    def get_selected_order_id(self) -> Optional[str]:
        """Get the ID of the currently selected order."""
        return self._data.selected_order_id

    def get_selected_project_id(self) -> Optional[str]:
        """Get the ID of the currently selected project."""
        return self._data.selected_project_id

    def get_selected_client_id(self) -> Optional[str]:
        """Get the ID of the currently selected client."""
        return self._data.selected_client_id

    def get_active_module_id(self) -> Optional[str]:
        """Get the ID of the currently active module in editor."""
        return self._data.active_module_id

    def get_active_assembly_id(self) -> Optional[str]:
        """Get the ID of the currently active assembly in editor."""
        return self._data.active_assembly_id

    def get_active_wall_id(self) -> Optional[str]:
        """Get the ID of the currently active wall in editor."""
        return self._data.active_wall_id

    def get_context_snapshot(self) -> AssistantContextData:
        """Get a snapshot of the entire context."""
        return AssistantContextData(
            worker_name=self._data.worker_name,
            display_name=self._data.display_name,
            role=self._data.role,
            permissions=self._data.permissions.copy(),
            active_tab=self._data.active_tab,
            active_subtab=self._data.active_subtab,
            current_route=self._data.current_route,
            selected_project_id=self._data.selected_project_id,
            selected_order_id=self._data.selected_order_id,
            selected_order_code=self._data.selected_order_code,
            selected_client_id=self._data.selected_client_id,
            active_module_id=self._data.active_module_id,
            active_assembly_id=self._data.active_assembly_id,
            active_wall_id=self._data.active_wall_id,
        )

    # =========================================================================
    # PERMISSION CHECKING
    # =========================================================================

    def has_permission(self, permission: str) -> bool:
        """
        Check if the current user has a specific permission.

        Args:
            permission: Permission identifier (e.g., Permission.VIEW_FINANCE)

        Returns:
            True if user has the permission, False otherwise.
        """
        return permission in self._data.permissions

    def can_access(self, permission: str) -> bool:
        """Alias for has_permission()."""
        return self.has_permission(permission)

    def get_role_level(self) -> int:
        """Get the numeric hierarchy level of the current role (higher = more permissions)."""
        return ROLE_HIERARCHY.get(self._data.role, 0)

    def is_admin(self) -> bool:
        """Check if the current user is a wlasciciel (owner/admin)."""
        return self._data.role == "wlasciciel"

    def is_office(self) -> bool:
        """Check if the current user is biuro (office)."""
        return self._data.role == "biuro"

    def is_production(self) -> bool:
        """Check if the current user is produkcja (production)."""
        return self._data.role == "produkcja"

    def is_warehouse(self) -> bool:
        """Check if the current user is magazyn (warehouse)."""
        return self._data.role == "magazyn"

    def is_logged_in(self) -> bool:
        """Check if a user is currently logged in."""
        return bool(self._data.worker_name)

    # =========================================================================
    # PRIVATE HELPERS
    # =========================================================================

    @staticmethod
    def _compute_permissions_for_role(role: str) -> Set[str]:
        """
        Compute the permission set for a given role.
        This delegates to the existing permission system.
        """
        from src.domain.permissions import ROLE_PERMISSIONS

        normalized_role = normalize_role(role)
        return set(ROLE_PERMISSIONS.get(normalized_role, set()))
