# Web Safe Work Mode — Phase 1 Implementation Plan

**Date:** 2026-04-27
**Scope:** Phase 1 — protect production data while development continues.
**Out of scope (Phase 2+):** roles/permissions, audit log, soft-delete, restore UI, backup management UI, RBAC.

---

## 1. Goal

Enable the company owner to start working with real data on `tech_modul` while developers (and Codex) keep iterating, **without ever risking the production database**.

Production data must be:
- isolated by environment (prod / dev / test)
- protected from destructive operations
- backed up before any schema change
- exportable to CSV for emergency recovery

Modules in development must be visibly labelled so the owner knows what is safe to use.

---

## 2. Current state (from exploration)

| Area | Today | Risk |
|------|-------|------|
| DB path | Hardcoded `database/tech_modul.db` (relative, CWD-sensitive) | Tests with wrong CWD could touch prod |
| Init | `TechModulDataManager.init_db()` runs on every instantiation, includes hardcoded demo technician inserts | Demo seed runs on prod every start |
| Tests | Use `tmp_path` per test, but no global `conftest.py` fixture forces isolation | A future test can forget `tmp_path` |
| Backup | `scripts/backup_data.py` exists but never tied to migrations | Schema change on prod has no safety net |
| Two schema sources | Legacy `data_manager.py` + modern `sqlite_db.py` both call `CREATE TABLE` | Acceptable for Phase 1 — leave as-is |
| CSV exports | Pattern exists for one endpoint (cutting list) | Easy to extend to core tables |
| Module labels | None | Owner can't tell what is safe |

---

## 3. Design decisions

### 3.1 Env detection — `src/safe_mode.py` (new, single source of truth)

Both `data_manager.py` and `sqlite_db.py` import from `safe_mode`. No code duplicates env logic.

**Environment variables:**
- `TECH_MODUL_ENV` = `prod` | `dev` | `test`. **Default = `dev`.**
- `TECH_MODUL_DB_PATH` = optional absolute path override (any mode)
- `TECH_MODUL_PROD_CONFIRM` = required to start in prod mode (extra safety knob; value `I_UNDERSTAND`)
- Pytest detection: presence of `PYTEST_CURRENT_TEST` or `PYTEST_VERSION` forces mode = `test` regardless of env

**Default DB paths (relative to repo root):**
- `prod` → `database/tech_modul_prod.db`
- `dev` → `database/tech_modul_dev.db`
- `test` → `database/tech_modul_test.db` (or tmp dir from pytest fixtures)

### 3.2 Legacy DB compatibility

The owner's real data is currently in `database/tech_modul.db`. Phase 1 keeps it safe:

- On first start in **prod mode**, if `tech_modul_prod.db` does not exist but `tech_modul.db` does:
  1. Take a backup of `tech_modul.db` to `backups/before_migration/`
  2. Copy `tech_modul.db` → `tech_modul_prod.db`
  3. Leave the original `tech_modul.db` untouched (so a rollback is possible)
  4. Log this loudly
- This is a **one-time bootstrap**, not a continuous sync.

### 3.3 Prod guard — `safe_mode.py` exposes:

- `current_env() -> "prod" | "dev" | "test"` — env detection
- `is_prod() -> bool`
- `is_test() -> bool`
- `get_db_path() -> Path` — canonical DB path for current env
- `assert_not_prod(action: str)` — raises `ProdGuardError` if env=prod
- `require_prod_confirmation(action: str)` — raises if env=prod and `TECH_MODUL_PROD_CONFIRM` is unset
- `assert_test_isolation(db_path)` — raises if a test path equals the prod path

Unsafe actions wrapped with these guards:
- demo seed (technicians) — `assert_not_prod("seed_demo_technicians")`
- any future reset/truncate scripts
- `init_db()` schema changes on prod call `backup_prod_db_or_die()` first

### 3.4 Backup before migration

Phase 1 ships `safe_mode.backup_prod_db_or_die(reason)`:
- Only runs when env=prod (no-op in dev/test)
- Path: `backups/before_migration/tech_modul_prod_YYYYMMDD_HHMMSS_<reason>.db`
- Uses `shutil.copy2` for byte-perfect copy + mtime preservation
- If copy fails (disk, permissions) → raises `BackupFailedError`, caller MUST not continue

Hooked into:
- `data_manager.init_db()` — before any `CREATE TABLE` on prod
- Future migration scripts (Phase 2) will reuse this helper

### 3.5 Additive-only migration policy

Phase 1 does not introduce a migration framework. It enforces **policy by code review and one helper**:

- All `CREATE TABLE` statements stay `IF NOT EXISTS` (already true)
- All new columns added in future via `ALTER TABLE ... ADD COLUMN` only (additive)
- `DROP TABLE` / `DROP COLUMN` / `DELETE FROM` on a prod connection is forbidden — `safe_mode.assert_not_prod()` must guard them
- Documented in `docs/WEB_SAFE_WORK_MODE_PHASE1_IMPLEMENTATION_PLAN.md` (this file) and `docs/MIGRATION_POLICY.md` (created)

### 3.6 Module readiness labels

**Frontend only** for Phase 1 — no backend involvement.

New file: `frontend/src/config/moduleStatus.ts` exports a map from route → status:

```ts
export type ModuleStatus = "READY_FOR_WORK" | "TESTING" | "IN_DEVELOPMENT";
export const MODULE_STATUS: Record<string, ModuleStatus> = { ... };
```

Classification (per spec):
- `READY_FOR_WORK`: `/calendar`, `/inventory`, `/database`, `/finance` (invoices), `/finance/fixed-costs`, `/cashboxes`, `/alarms`, `/orders/new` (clients side)
- `TESTING`: `/services`, `/workspace/production`, `/wall`, `/operations`, `/production/handoff`
- `IN_DEVELOPMENT`: `/configuration`, `/assembly`, `/workspace`, `/cri`, `/overview`

A small badge is rendered next to the side-bar icon and on the page header (small color dot). No layout redesign.

### 3.7 CSV exports

Phase 1 ships **5 read-only endpoints** under `/api/export/csv/`:

| Endpoint | Source table | Priority |
|----------|--------------|----------|
| `/api/export/csv/clients` | `clients` | 1 |
| `/api/export/csv/materials` | `materials` | 2 |
| `/api/export/csv/invoices` | `invoices` | 3 |
| `/api/export/csv/invoice-line-items` | `invoice_line_items` | 3 |
| `/api/export/csv/calendar-events` | `calendar_events` | 4 |

Pattern follows the existing `/api/production/.../export/csv` style (FastAPI `Response`, `Content-Disposition: attachment`, Polish-friendly UTF-8 with BOM for Excel).

**Work time** is stored as JSON, not a table — Phase 1 ships JSON download instead at `/api/export/json/work-time`. (Phase 2: convert to table.)

Endpoints are read-only — they only `SELECT`. Safe on prod. Behind same FastAPI app.

### 3.8 Tests

New file: `tests/test_safe_mode.py` — covers:
- env detection from `TECH_MODUL_ENV`
- pytest auto-detection (forces test mode)
- DB path selection per env
- `is_prod()` / `is_test()` correctness
- `assert_not_prod()` raises in prod, no-op elsewhere
- `require_prod_confirmation()` requires the env var
- `backup_prod_db_or_die()` skips dev/test, runs in prod, fails loud on disk error

New file: `tests/test_csv_exports.py` — covers:
- `/api/export/csv/clients` returns 200, `text/csv` content-type, has expected header row
- `/api/export/csv/materials` returns CSV
- `/api/export/csv/invoices` returns CSV
- exports operate against a `tmp_path` test DB seeded with one row each

Updated: `tests/conftest.py` — sets `TECH_MODUL_ENV=test` for the whole pytest session and asserts no test ever resolves to the prod DB path.

### 3.9 Files changed/created

**New:**
- `src/safe_mode.py` — env detection, path resolution, guards, backup helper
- `src/api/csv_exports.py` — 5 export endpoint handlers (registered into main_api app)
- `frontend/src/config/moduleStatus.ts` — module status map
- `frontend/src/components/ModuleStatusBadge.tsx` — small badge component
- `tests/test_safe_mode.py`
- `tests/test_csv_exports.py`
- `docs/MIGRATION_POLICY.md` — short rules document
- `docs/WEB_SAFE_WORK_MODE_PHASE1_IMPLEMENTATION_PLAN.md` — this file

**Modified:**
- `src/api/data_manager.py` — DB path from `safe_mode.get_db_path()`; demo seed gated by `safe_mode.is_prod()`; `init_db()` calls `backup_prod_db_or_die()` first on prod
- `src/storage/sqlite_db.py` — DB path from `safe_mode.get_db_path()`
- `src/api/main_api.py` — register CSV export router
- `tests/conftest.py` — pytest fixture that forces `TECH_MODUL_ENV=test` and asserts isolation
- `frontend/src/components/AppShell.tsx` — render `ModuleStatusBadge` next to nav items

---

## 4. Acceptance criteria (per spec)

- [x] Production DB path clearly separated (`tech_modul_prod.db`)
- [x] Tests cannot accidentally use production DB (conftest enforce + assertion in `safe_mode`)
- [x] Migrations on production create backup first (`backup_prod_db_or_die()` before any `CREATE TABLE` on prod)
- [x] Unsafe destructive operations blocked in production (`assert_not_prod()` on demo seed; documented policy)
- [x] Owner can export at least core data to CSV (5 endpoints + 1 JSON)
- [x] UI clearly labels which modules are safe vs testing/development (status badges in nav)

---

## 5. How to run

**Production (real company work):**
```cmd
set TECH_MODUL_ENV=prod
set TECH_MODUL_PROD_CONFIRM=I_UNDERSTAND
START_WEB.bat
```
Uses `database/tech_modul_prod.db`. On first start migrates legacy `tech_modul.db` once.

**Development (default — Codex/dev experiments):**
```cmd
START_WEB.bat
```
Uses `database/tech_modul_dev.db`. No effect on prod.

**Tests:**
```cmd
.venv\Scripts\python.exe -m pytest
```
Pytest is auto-detected → uses `database/tech_modul_test.db` or per-test `tmp_path`. **Cannot reach prod even if a test forgets to isolate.**

---

## 6. What is intentionally NOT changed in Phase 1

- Two parallel schema systems (`data_manager.py` + `sqlite_db.py`) — left as-is, future consolidation
- No role-based access / authentication changes
- No audit log, soft-delete, or restore UI
- No backup management UI (cron / retention) — manual backups via filesystem
- No automated schema migrations framework (Alembic etc.) — additive-only by code review
- No mass refactor of API to use `safe_mode` everywhere — only the entry points and demo seed
- No automated work_time → table migration (still JSON)

These are explicit Phase 2 candidates.
