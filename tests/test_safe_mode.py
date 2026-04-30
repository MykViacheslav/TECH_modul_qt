"""Tests for src/safe_mode.py — Phase 1 Safe Work Mode.

Covers:
- env detection (prod/dev/test) including pytest auto-detection
- DB path selection per env, plus override
- assert_not_prod / require_prod_confirmation behavior
- assert_test_isolation refuses prod DB during a pytest run
- backup_prod_db_or_die: no-op in dev/test; copies file in prod
- bootstrap_legacy_prod_db: idempotent legacy migration

Tests use monkeypatch to flip env vars; pytest is always running, so we also
patch `_running_under_pytest` where we need to simulate a non-pytest context.
"""

import os
import sqlite3
from pathlib import Path

import pytest

from src import safe_mode


# ---------------------------------------------------------------------------
# Env detection
# ---------------------------------------------------------------------------

def test_pytest_always_overrides_to_test(monkeypatch):
    monkeypatch.setenv("TECH_MODUL_ENV", "prod")  # even with prod set...
    assert safe_mode.current_env() == "test"      # pytest detection wins


def test_env_dev_when_pytest_not_active_and_no_env_set(monkeypatch):
    monkeypatch.delenv("TECH_MODUL_ENV", raising=False)
    monkeypatch.setattr(safe_mode, "_running_under_pytest", lambda: False)
    assert safe_mode.current_env() == "dev"


def test_env_prod_when_set_and_pytest_off(monkeypatch):
    monkeypatch.setenv("TECH_MODUL_ENV", "prod")
    monkeypatch.setattr(safe_mode, "_running_under_pytest", lambda: False)
    assert safe_mode.current_env() == "prod"
    assert safe_mode.is_prod() is True
    assert safe_mode.is_dev() is False


def test_env_test_when_set_explicitly(monkeypatch):
    monkeypatch.setenv("TECH_MODUL_ENV", "test")
    monkeypatch.setattr(safe_mode, "_running_under_pytest", lambda: False)
    assert safe_mode.current_env() == "test"
    assert safe_mode.is_test() is True


def test_env_unknown_value_falls_back_to_dev(monkeypatch):
    monkeypatch.setenv("TECH_MODUL_ENV", "garbage")
    monkeypatch.setattr(safe_mode, "_running_under_pytest", lambda: False)
    assert safe_mode.current_env() == "dev"


# ---------------------------------------------------------------------------
# DB path selection
# ---------------------------------------------------------------------------

def test_db_path_default_test(monkeypatch):
    # Pytest is active -> test path.
    monkeypatch.delenv("TECH_MODUL_DB_PATH", raising=False)
    expected = (safe_mode.get_repo_root() / "database" / "tech_modul_test.db").resolve()
    assert safe_mode.get_db_path() == expected


def test_db_path_default_prod(monkeypatch):
    monkeypatch.delenv("TECH_MODUL_DB_PATH", raising=False)
    monkeypatch.setenv("TECH_MODUL_ENV", "prod")
    monkeypatch.setattr(safe_mode, "_running_under_pytest", lambda: False)
    expected = (safe_mode.get_repo_root() / "database" / "tech_modul_prod.db").resolve()
    assert safe_mode.get_db_path() == expected


def test_db_path_default_dev(monkeypatch):
    monkeypatch.delenv("TECH_MODUL_DB_PATH", raising=False)
    monkeypatch.delenv("TECH_MODUL_ENV", raising=False)
    monkeypatch.setattr(safe_mode, "_running_under_pytest", lambda: False)
    expected = (safe_mode.get_repo_root() / "database" / "tech_modul_dev.db").resolve()
    assert safe_mode.get_db_path() == expected


def test_db_path_override_wins(monkeypatch, tmp_path):
    custom = tmp_path / "my.db"
    monkeypatch.setenv("TECH_MODUL_DB_PATH", str(custom))
    assert safe_mode.get_db_path() == custom.resolve()


# ---------------------------------------------------------------------------
# Prod guards
# ---------------------------------------------------------------------------

def test_assert_not_prod_no_op_in_dev(monkeypatch):
    monkeypatch.setenv("TECH_MODUL_ENV", "dev")
    monkeypatch.setattr(safe_mode, "_running_under_pytest", lambda: False)
    safe_mode.assert_not_prod("seed_demo")  # must not raise


def test_assert_not_prod_no_op_in_test():
    # pytest is active so this is "test" mode; must not raise.
    safe_mode.assert_not_prod("seed_demo")


def test_assert_not_prod_raises_in_prod(monkeypatch):
    monkeypatch.setenv("TECH_MODUL_ENV", "prod")
    monkeypatch.setattr(safe_mode, "_running_under_pytest", lambda: False)
    with pytest.raises(safe_mode.ProdGuardError) as exc:
        safe_mode.assert_not_prod("seed_demo_clients")
    assert "seed_demo_clients" in str(exc.value)


def test_require_prod_confirmation_no_op_in_non_prod(monkeypatch):
    monkeypatch.setenv("TECH_MODUL_ENV", "dev")
    monkeypatch.setattr(safe_mode, "_running_under_pytest", lambda: False)
    monkeypatch.delenv("TECH_MODUL_PROD_CONFIRM", raising=False)
    safe_mode.require_prod_confirmation("dangerous_op")  # must not raise


def test_require_prod_confirmation_raises_without_token(monkeypatch):
    monkeypatch.setenv("TECH_MODUL_ENV", "prod")
    monkeypatch.setattr(safe_mode, "_running_under_pytest", lambda: False)
    monkeypatch.delenv("TECH_MODUL_PROD_CONFIRM", raising=False)
    with pytest.raises(safe_mode.ProdGuardError):
        safe_mode.require_prod_confirmation("dangerous_op")


def test_require_prod_confirmation_passes_with_token(monkeypatch):
    monkeypatch.setenv("TECH_MODUL_ENV", "prod")
    monkeypatch.setattr(safe_mode, "_running_under_pytest", lambda: False)
    monkeypatch.setenv("TECH_MODUL_PROD_CONFIRM", "I_UNDERSTAND")
    safe_mode.require_prod_confirmation("dangerous_op")  # must not raise


# ---------------------------------------------------------------------------
# Test isolation guard (refuses prod DB while pytest is running)
# ---------------------------------------------------------------------------

def test_assert_test_isolation_blocks_prod_path():
    prod = safe_mode.get_repo_root() / "database" / "tech_modul_prod.db"
    with pytest.raises(safe_mode.ProdGuardError):
        safe_mode.assert_test_isolation(prod)


def test_assert_test_isolation_blocks_legacy_path():
    legacy = safe_mode.get_repo_root() / "database" / "tech_modul.db"
    with pytest.raises(safe_mode.ProdGuardError):
        safe_mode.assert_test_isolation(legacy)


def test_assert_test_isolation_allows_tmp_path(tmp_path):
    safe_mode.assert_test_isolation(tmp_path / "ok.db")  # must not raise


def test_assert_test_isolation_no_op_when_not_pytest(monkeypatch):
    monkeypatch.setattr(safe_mode, "_running_under_pytest", lambda: False)
    prod = safe_mode.get_repo_root() / "database" / "tech_modul_prod.db"
    safe_mode.assert_test_isolation(prod)  # outside pytest, no enforcement


# ---------------------------------------------------------------------------
# Backup before migration
# ---------------------------------------------------------------------------

def test_backup_no_op_in_dev(monkeypatch):
    monkeypatch.setenv("TECH_MODUL_ENV", "dev")
    monkeypatch.setattr(safe_mode, "_running_under_pytest", lambda: False)
    assert safe_mode.backup_prod_db_or_die("init_db") is None


def test_backup_no_op_in_test():
    assert safe_mode.backup_prod_db_or_die("init_db") is None


def test_backup_creates_file_in_prod(monkeypatch, tmp_path):
    # Set up a fake repo root with a DB file.
    fake_root = tmp_path / "fakeproj"
    (fake_root / "database").mkdir(parents=True)
    fake_db = fake_root / "database" / "tech_modul_prod.db"
    sqlite3.connect(str(fake_db)).close()  # creates a valid empty SQLite file
    fake_db.write_bytes(b"hello world payload" + fake_db.read_bytes())

    monkeypatch.setenv("TECH_MODUL_ENV", "prod")
    monkeypatch.setattr(safe_mode, "_running_under_pytest", lambda: False)
    monkeypatch.setattr(safe_mode, "get_repo_root", lambda: fake_root)
    monkeypatch.delenv("TECH_MODUL_DB_PATH", raising=False)

    backup = safe_mode.backup_prod_db_or_die("schema_change")
    assert backup is not None
    assert backup.exists()
    assert backup.parent == fake_root / "backups" / "before_migration"
    assert backup.stat().st_size > 0
    assert backup.stat().st_size == fake_db.stat().st_size


def test_backup_no_op_when_db_missing(monkeypatch, tmp_path):
    fake_root = tmp_path / "fakeproj"
    (fake_root / "database").mkdir(parents=True)
    monkeypatch.setenv("TECH_MODUL_ENV", "prod")
    monkeypatch.setattr(safe_mode, "_running_under_pytest", lambda: False)
    monkeypatch.setattr(safe_mode, "get_repo_root", lambda: fake_root)
    monkeypatch.delenv("TECH_MODUL_DB_PATH", raising=False)
    # No DB file exists -> not a failure, just nothing to back up.
    assert safe_mode.backup_prod_db_or_die("init_db") is None


# ---------------------------------------------------------------------------
# Legacy bootstrap
# ---------------------------------------------------------------------------

def test_bootstrap_legacy_db_skips_in_dev(monkeypatch):
    monkeypatch.setenv("TECH_MODUL_ENV", "dev")
    monkeypatch.setattr(safe_mode, "_running_under_pytest", lambda: False)
    assert safe_mode.bootstrap_legacy_prod_db() is None


def test_bootstrap_legacy_db_copies_legacy_to_prod(monkeypatch, tmp_path):
    fake_root = tmp_path / "fakeproj"
    (fake_root / "database").mkdir(parents=True)
    legacy = fake_root / "database" / "tech_modul.db"
    sqlite3.connect(str(legacy)).close()
    legacy.write_bytes(legacy.read_bytes() + b"legacy-payload")

    monkeypatch.setenv("TECH_MODUL_ENV", "prod")
    monkeypatch.setattr(safe_mode, "_running_under_pytest", lambda: False)
    monkeypatch.setattr(safe_mode, "get_repo_root", lambda: fake_root)

    new_path = safe_mode.bootstrap_legacy_prod_db()
    assert new_path == fake_root / "database" / "tech_modul_prod.db"
    assert new_path.exists()
    # Legacy DB is preserved untouched.
    assert legacy.exists()
    # A backup of the legacy DB lives in backups/before_migration/.
    backups = list((fake_root / "backups" / "before_migration").iterdir())
    assert any("tech_modul_legacy_" in b.name for b in backups)


def test_bootstrap_legacy_db_idempotent(monkeypatch, tmp_path):
    fake_root = tmp_path / "fakeproj"
    (fake_root / "database").mkdir(parents=True)
    prod = fake_root / "database" / "tech_modul_prod.db"
    sqlite3.connect(str(prod)).close()
    legacy = fake_root / "database" / "tech_modul.db"
    sqlite3.connect(str(legacy)).close()

    monkeypatch.setenv("TECH_MODUL_ENV", "prod")
    monkeypatch.setattr(safe_mode, "_running_under_pytest", lambda: False)
    monkeypatch.setattr(safe_mode, "get_repo_root", lambda: fake_root)

    # prod already exists -> bootstrap is a no-op.
    assert safe_mode.bootstrap_legacy_prod_db() is None


# ---------------------------------------------------------------------------
# Diagnostic env_summary
# ---------------------------------------------------------------------------

def test_env_summary_shape():
    summary = safe_mode.env_summary()
    for key in ("env", "db_path", "is_prod", "is_dev", "is_test", "pytest_active"):
        assert key in summary
    assert summary["pytest_active"] is True
    assert summary["env"] == "test"


# ---------------------------------------------------------------------------
# Cross-cutting: demo seed must refuse to run in prod
# ---------------------------------------------------------------------------

def test_seed_demo_clients_refuses_in_prod(monkeypatch, tmp_path):
    """The hardcoded demo client seed in TechModulDataManager must never run in prod."""
    monkeypatch.setenv("TECH_MODUL_ENV", "prod")
    monkeypatch.setattr(safe_mode, "_running_under_pytest", lambda: False)

    db = tmp_path / "fakeprod.db"
    monkeypatch.setenv("TECH_MODUL_DB_PATH", str(db))

    # Importing here so the env mutations above are seen.
    from src.api import data_manager as dm_mod

    # Build manager directly (this does init_db, which we allow as it's additive).
    mgr = dm_mod.TechModulDataManager(db_path=str(db))

    with pytest.raises(safe_mode.ProdGuardError):
        mgr.seed_demo_clients_if_empty()
    with pytest.raises(safe_mode.ProdGuardError):
        mgr.seed_demo_modules_if_empty()
    with pytest.raises(safe_mode.ProdGuardError):
        mgr.seed_demo_materials_if_empty()
