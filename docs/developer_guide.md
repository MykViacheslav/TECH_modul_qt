# TECH_modul - Developer Guide

## 1. Local Setup

```powershell
cd C:\PythonProject\TECH_modul
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If `requirements.txt` is incomplete in your local branch, install missing packages manually based on import errors.

## 2. Run Modes

Desktop GUI:

```powershell
.\.venv\Scripts\python.exe .\src\app\main.py
```

HTTP server mode:

```powershell
.\.venv\Scripts\python.exe .\src\app\main.py --server --server-port 8000
```

HTTPS kiosk mode:

```powershell
.\.venv\Scripts\python.exe .\src\app\main.py --server --https --https-port 8443
```

## 3. Testing

Focused tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_kpi_service.py tests\test_dashboard_services_kpi.py
```

Theme/accessibility tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_theme_accessibility.py
```

## 4. Adding a New Tab

1. Create tab widget in `src/tabs/<area>/tab_<name>.py`.
2. Register it in `src/tabs/registry.py`.
3. Add tab title to the correct group in `src/app/navigation_groups.py`.
4. If cross-tab events are needed, wire them in `src/app/main_window_wiring.py`.
5. Add tests for at least the main non-GUI logic.

## 5. Adding a New KPI

1. Extend dataclass or payload logic in `src/services/kpi_service.py`.
2. Add/adjust payload fields in `_compute_dashboard_payload`.
3. Render KPI in `src/tabs/dashboard/tab_dashboard.py` (`_apply_kpi_payload`).
4. Add/extend tests in:
   - `tests/test_kpi_service.py`
   - `tests/test_dashboard_services_kpi.py`

## 6. Data and Schema Evolution

- Prefer store-level compatibility changes (default values, tolerant parsing).
- For JSON changes, keep backward compatibility with old keys whenever possible.
- If introducing required new fields, add migration-on-load logic in store class.
- For map-based JSON stores, use versioned wrapper with `schema_version` + `items`.
- Reuse `src/storage/schema_versioning.py` for migration/read/write behavior.

## 7. Coding Conventions

- Keep UI changes incremental and testable.
- Avoid direct file IO in tabs; route through storage/service layers.
- Use explicit names for tabs, controls, and `accessibleName` on key interactive widgets.
- Keep long-running computations out of UI thread (worker/thread/timer patterns).
