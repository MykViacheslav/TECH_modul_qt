"""Safe Work Mode — Phase 1.

Single source of truth for environment detection, database path resolution,
production guards, and backup-before-migration helper.

See docs/WEB_SAFE_WORK_MODE_PHASE1_IMPLEMENTATION_PLAN.md for the full design.

Public API:
    current_env() -> Literal["prod", "dev", "test"]
    is_prod() -> bool
    is_dev() -> bool
    is_test() -> bool
    get_db_path() -> Path
    get_repo_root() -> Path
    assert_not_prod(action: str) -> None
    require_prod_confirmation(action: str) -> None
    assert_test_isolation(db_path) -> None
    backup_prod_db_or_die(reason: str) -> Path | None
    bootstrap_legacy_prod_db() -> None

Errors:
    ProdGuardError — raised when an unsafe action is attempted in prod
    BackupFailedError — raised when a required backup cannot be created
"""

from __future__ import annotations

import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

EnvName = Literal["prod", "dev", "test"]

ENV_VAR = "TECH_MODUL_ENV"
DB_PATH_OVERRIDE = "TECH_MODUL_DB_PATH"
PROD_CONFIRM_VAR = "TECH_MODUL_PROD_CONFIRM"
PROD_CONFIRM_VALUE = "I_UNDERSTAND"

LEGACY_DB_FILENAME = "tech_modul.db"
DB_FILENAMES: dict[EnvName, str] = {
    "prod": "tech_modul_prod.db",
    "dev": "tech_modul_dev.db",
    "test": "tech_modul_test.db",
}


class ProdGuardError(RuntimeError):
    """Raised when an unsafe action is attempted in production mode."""


class BackupFailedError(RuntimeError):
    """Raised when a required production backup cannot be created."""


def get_repo_root() -> Path:
    """Return the project root (the parent of the `src/` directory)."""
    return Path(__file__).resolve().parent.parent


def _running_under_pytest() -> bool:
    if "PYTEST_CURRENT_TEST" in os.environ:
        return True
    if "PYTEST_VERSION" in os.environ:
        return True
    if "pytest" in sys.modules:
        return True
    return False


def current_env() -> EnvName:
    """Detect the current environment.

    Order of precedence:
    1. If pytest is running -> "test" (always wins, even if user set ENV=prod)
    2. TECH_MODUL_ENV env var if set to a known value
    3. Default: "dev"
    """
    if _running_under_pytest():
        return "test"
    raw = os.environ.get(ENV_VAR, "").strip().lower()
    if raw == "prod":
        return "prod"
    if raw == "test":
        return "test"
    return "dev"


def is_prod() -> bool:
    return current_env() == "prod"


def is_dev() -> bool:
    return current_env() == "dev"


def is_test() -> bool:
    return current_env() == "test"


def get_db_path() -> Path:
    """Resolve the canonical SQLite DB path for the current environment.

    Order:
    1. TECH_MODUL_DB_PATH override (any env)
    2. <repo_root>/database/<filename for current env>
    """
    override = os.environ.get(DB_PATH_OVERRIDE, "").strip()
    if override:
        return Path(override).resolve()
    env = current_env()
    return (get_repo_root() / "database" / DB_FILENAMES[env]).resolve()


def assert_not_prod(action: str) -> None:
    """Raise ProdGuardError if the current env is production.

    Use to guard demo seeds, resets, destructive migrations, truncates, etc.
    """
    if is_prod():
        raise ProdGuardError(
            f"Refusing to perform unsafe action {action!r} in PROD mode. "
            f"This action is only allowed in dev/test."
        )


def require_prod_confirmation(action: str) -> None:
    """In prod, require TECH_MODUL_PROD_CONFIRM=I_UNDERSTAND. No-op elsewhere.

    Use for destructive ops that *might* be allowed in prod with explicit owner consent.
    """
    if not is_prod():
        return
    actual = os.environ.get(PROD_CONFIRM_VAR, "").strip()
    if actual != PROD_CONFIRM_VALUE:
        raise ProdGuardError(
            f"Action {action!r} requires {PROD_CONFIRM_VAR}={PROD_CONFIRM_VALUE} in PROD mode."
        )


def assert_test_isolation(db_path) -> None:
    """When running under pytest, refuse to use the production DB path.

    Call from any test fixture that opens a DB.
    """
    if not _running_under_pytest():
        return
    if db_path is None:
        return
    candidate = Path(str(db_path)).resolve()
    prod_path = (get_repo_root() / "database" / DB_FILENAMES["prod"]).resolve()
    legacy_path = (get_repo_root() / "database" / LEGACY_DB_FILENAME).resolve()
    if candidate == prod_path or candidate == legacy_path:
        raise ProdGuardError(
            f"Test attempted to use production DB at {candidate!r}. "
            f"Use tmp_path or set TECH_MODUL_DB_PATH explicitly."
        )


def backup_prod_db_or_die(reason: str) -> Optional[Path]:
    """Create a timestamped backup of the prod DB before a schema-changing operation.

    Returns the backup path if a backup was made, or None if env is dev/test
    (which is the no-op case).

    Raises BackupFailedError if env=prod and the backup cannot be created.
    The caller MUST NOT proceed with the migration if this raises.
    """
    if not is_prod():
        return None

    src = get_db_path()
    if not src.exists():
        # Nothing to back up yet (fresh install). Allow init to proceed.
        return None

    repo_root = get_repo_root()
    backup_dir = repo_root / "backups" / "before_migration"
    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise BackupFailedError(
            f"Cannot create backup directory {backup_dir!r}: {e}"
        ) from e

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_reason = "".join(c if c.isalnum() or c in "-_" else "_" for c in reason)[:40]
    dest = backup_dir / f"tech_modul_prod_{timestamp}_{safe_reason}.db"
    try:
        shutil.copy2(src, dest)
    except OSError as e:
        raise BackupFailedError(
            f"Failed to copy {src!r} -> {dest!r}: {e}"
        ) from e

    if not dest.exists() or dest.stat().st_size == 0:
        raise BackupFailedError(
            f"Backup {dest!r} is missing or empty after copy attempt."
        )
    return dest


def bootstrap_legacy_prod_db() -> Optional[Path]:
    """One-time copy of legacy `tech_modul.db` to `tech_modul_prod.db` on first prod start.

    Idempotent: only runs in prod, only when prod DB is missing AND legacy DB exists.
    Always takes a backup of the legacy DB first.

    Returns the new prod DB path if a copy was made, otherwise None.
    """
    if not is_prod():
        return None

    repo_root = get_repo_root()
    prod_path = repo_root / "database" / DB_FILENAMES["prod"]
    legacy_path = repo_root / "database" / LEGACY_DB_FILENAME

    if prod_path.exists():
        return None  # Already migrated.
    if not legacy_path.exists():
        return None  # Nothing to migrate from.

    backup_dir = repo_root / "backups" / "before_migration"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    legacy_backup = backup_dir / f"tech_modul_legacy_{timestamp}_bootstrap.db"
    try:
        shutil.copy2(legacy_path, legacy_backup)
    except OSError as e:
        raise BackupFailedError(
            f"Failed to back up legacy DB before bootstrap: {e}"
        ) from e

    try:
        shutil.copy2(legacy_path, prod_path)
    except OSError as e:
        raise BackupFailedError(
            f"Failed to copy legacy DB to prod path: {e}"
        ) from e

    return prod_path


def env_summary() -> dict:
    """Diagnostic dict — useful for logs and the `/api/safe-mode/status` endpoint."""
    env = current_env()
    return {
        "env": env,
        "db_path": str(get_db_path()),
        "is_prod": env == "prod",
        "is_dev": env == "dev",
        "is_test": env == "test",
        "pytest_active": _running_under_pytest(),
        "prod_confirm_set": os.environ.get(PROD_CONFIRM_VAR, "").strip() == PROD_CONFIRM_VALUE,
    }
