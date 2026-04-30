"""Pytest global fixtures and safety enforcement for TECH_modul.

Phase 1 Safe Work Mode rule: tests must NEVER touch the production database.
This conftest:
- Sets TECH_MODUL_ENV=test for the entire pytest session.
- Routes all DB access through `database/tech_modul_test.db` by default.
- Asserts at session start that `safe_mode.current_env()` is "test".
- Provides a per-test fixture that swaps in a fresh tmp_path-backed DB.
"""

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Force test mode BEFORE any project module is imported.
os.environ["TECH_MODUL_ENV"] = "test"
# Make sure no leftover prod-confirmation flag escapes from the user's shell.
os.environ.pop("TECH_MODUL_PROD_CONFIRM", None)

# Now safe to import project modules.
from src import safe_mode  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _enforce_test_mode():
    """Hard fail if anything has bumped us out of test mode."""
    assert safe_mode.current_env() == "test", (
        f"Pytest must run in test mode, got {safe_mode.current_env()!r}. "
        f"Refusing to run tests against a non-test DB."
    )
    yield


@pytest.fixture()
def isolated_db_path(tmp_path, monkeypatch):
    """Provide a fresh, isolated SQLite DB path for a single test.

    Sets TECH_MODUL_DB_PATH so any code calling safe_mode.get_db_path() also
    sees the isolated path.
    """
    db = tmp_path / "tech_modul_isolated.db"
    monkeypatch.setenv("TECH_MODUL_DB_PATH", str(db))
    safe_mode.assert_test_isolation(db)
    return db
