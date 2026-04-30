# Migration Policy — Phase 1 Safe Work Mode

**Status:** active since 2026-04-27
**Companion:** `docs/WEB_SAFE_WORK_MODE_PHASE1_IMPLEMENTATION_PLAN.md`

This document defines the rules every developer (human or agent) must follow
when changing the database schema. The single goal is: **a schema change must
never destroy data on the owner's production database**.

---

## 1. Environments and DB paths

`src/safe_mode.py` is the single source of truth for env detection and DB
path resolution. It exposes:

| Env | Selected when | DB file |
|-----|---------------|---------|
| `prod` | `TECH_MODUL_ENV=prod` and pytest is **not** running | `database/tech_modul_prod.db` |
| `dev` | default fallback (no env var, no pytest) | `database/tech_modul_dev.db` |
| `test` | `pytest` is detected, OR `TECH_MODUL_ENV=test` | `database/tech_modul_test.db` (or per-test `tmp_path`) |

Override (any env): `TECH_MODUL_DB_PATH=/abs/path.db`.

---

## 2. The four rules

### Rule 1 — Migrations are additive only

You **may**:
- `CREATE TABLE IF NOT EXISTS …`
- `ALTER TABLE … ADD COLUMN …` with a default
- `CREATE INDEX IF NOT EXISTS …`
- `INSERT` reference rows that are **not** demo data

You **must not** without explicit owner consent (see Rule 4):
- `DROP TABLE`, `DROP COLUMN`
- `ALTER TABLE … RENAME COLUMN …`
- `DELETE FROM …` of existing user data
- `UPDATE …` that overwrites user-entered fields

### Rule 2 — Backup is mandatory before any schema-touching code path

Every code path that runs `CREATE TABLE`, `ALTER TABLE`, or `INSERT` of
seed/reference data on startup must call:

```python
from src import safe_mode
safe_mode.backup_prod_db_or_die("<short-reason>")
```

In `dev`/`test` this is a no-op. In `prod` it copies the live DB to
`backups/before_migration/tech_modul_prod_<timestamp>_<reason>.db` and aborts
the operation if the copy fails. Code must abort if `BackupFailedError` is
raised — never swallow it.

Already wired in:
- `src/api/data_manager.py` :: `TechModulDataManager.init_db()`
- `src/storage/sqlite_db.py` :: `Database.__init__()`

When you add a third schema-touching entry point, wire it the same way.

### Rule 3 — Demo seeds are gated

Any code that inserts demo/sample/fake data must call
`safe_mode.assert_not_prod("<seed_name>")` at the top, or be wrapped in
`if not safe_mode.is_prod(): …`. This protects prod from being polluted by
test fixtures left in the codebase.

Already gated:
- module-level demo seeds in `src/api/data_manager.py`
- `seed_demo_modules_if_empty`, `seed_demo_materials_if_empty`,
  `seed_demo_clients_if_empty`
- the hardcoded `technicians` insert in `init_db()`

### Rule 4 — Destructive prod ops require explicit consent

If a non-additive change is genuinely required (rename a column, drop a
deprecated table), the script must call:

```python
safe_mode.require_prod_confirmation("rename_column_x")
```

In prod this raises `ProdGuardError` unless the owner has set
`TECH_MODUL_PROD_CONFIRM=I_UNDERSTAND` for that single run.

---

## 3. Authoring a new migration

1. Write the change as additive (`CREATE TABLE IF NOT EXISTS …` /
   `ALTER TABLE … ADD COLUMN … DEFAULT …`).
2. Wire `backup_prod_db_or_die("<reason>")` immediately before it.
3. Run on dev: `set TECH_MODUL_ENV=dev` and start the app.
4. Run the test suite: `pytest tests/test_safe_mode.py tests/test_csv_exports.py`
   plus any new tests for the change.
5. On the owner's machine, before the first prod start after the change:
   - confirm `backups/before_migration/` exists and is writable
   - run with `TECH_MODUL_ENV=prod`
   - verify a new file appears in `backups/before_migration/`

If a step fails, fix the cause. Never bypass the guard.

---

## 4. CSV exports as the safety net

Every release that ships a schema change must keep
`/api/export/csv/{clients,materials,invoices,invoice-line-items,calendar-events}`
and `/api/export/json/work-time` working. They are the owner's
last-resort recovery channel and are covered by `tests/test_csv_exports.py`.

If you change a column name, update the export's column list in
`src/api/csv_exports.py` and add a test row. The exporter is intentionally
resilient to missing columns (it pads `None`), so old DBs continue to export
even if you add a new column.

---

## 5. Out of scope for Phase 1

- Forward-only migration framework (Alembic/yoyo). Phase 2.
- Down-migrations / rollback automation. Phase 2.
- A migration history table. Phase 2.
- Any UI to manage backups or restore. Phase 2.

Phase 1 trades sophistication for predictability: every DB-touching path is
either additive, gated by `assert_not_prod`, or guarded by
`backup_prod_db_or_die`. That is enough for the owner to start using prod
while development continues.
