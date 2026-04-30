from enum import Enum
from typing import Set

class Role(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    OPERATOR = "operator"
    VIEWER = "viewer"

# Mapping from legacy technician roles to new system roles
ROLE_MAPPING = {
    "wlasciciel": Role.ADMIN,
    "biuro": Role.MANAGER,
    "produkcja": Role.OPERATOR,
    "magazyn": Role.OPERATOR,
    "montaz": Role.OPERATOR,
}

# Permission definitions
class Action(str, Enum):
    RESTORE_DELETED = "restore_deleted"
    INVENTORY_CORRECTION = "inventory_correction"
    INVENTORY_SCRAP = "inventory_scrap"
    FINANCE_EDIT = "finance_edit"
    ISSUE_RESOLVE = "issue_resolve"
    ISSUE_ASSIGN = "issue_assign"
    ISSUE_UPDATE = "issue_update"
    PRODUCTION_START = "production_start"
    PRODUCTION_FINISH = "production_finish"
    PROCUREMENT_MANAGE = "procurement_manage"

# Role-to-Action mapping
PERMISSIONS: dict[Role, Set[Action]] = {
    Role.ADMIN: set(Action), # Admin can do everything
    Role.MANAGER: {
        Action.RESTORE_DELETED,
        Action.INVENTORY_CORRECTION,
        Action.INVENTORY_SCRAP,
        Action.FINANCE_EDIT,
        Action.ISSUE_RESOLVE,
        Action.ISSUE_ASSIGN,
        Action.ISSUE_UPDATE,
        Action.PRODUCTION_START,
        Action.PRODUCTION_FINISH,
        Action.PROCUREMENT_MANAGE,
    },
    Role.OPERATOR: {
        Action.ISSUE_RESOLVE,
        Action.ISSUE_UPDATE,
        Action.PRODUCTION_START,
        Action.PRODUCTION_FINISH,
        Action.INVENTORY_SCRAP, # Operators can report scrap
    },
    Role.VIEWER: set(), # Viewers have no mutation permissions
}

def has_permission(role: str | Role, action: Action) -> bool:
    if isinstance(role, str):
        # Try mapping from legacy or just match
        role_enum = ROLE_MAPPING.get(role.lower(), None)
        if not role_enum:
            try:
                role_enum = Role(role.lower())
            except ValueError:
                return False
    else:
        role_enum = role
    
    return action in PERMISSIONS.get(role_enum, set())
