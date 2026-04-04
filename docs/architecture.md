# TECH_modul - Architecture

## High-Level Layers

- `src/app`: application bootstrap, `MainWindow`, theme/scale settings, navigation wiring.
- `src/tabs`: business screens (orders, workers, dashboard, calendar, etc.).
- `src/widgets`: reusable UI widgets and dialogs.
- `src/domain`: domain models, permissions, work-time and business rules.
- `src/storage`: persistence adapters (JSON/SQLite stores).
- `src/services`: cross-tab services (KPI, calendar sync, alarms, backups, kiosk helpers).
- `src/server`: HTTP/HTTPS server and kiosk web page for tablet time tracking.

## Data Flow

1. UI tabs read/write through store classes in `src/storage`.
2. Services aggregate data from multiple stores (`KPIService`, sync/automation helpers).
3. Main window wires tab-to-tab interactions in `src/app/main_window_wiring.py`.
4. Kiosk mode exposes selected flows over HTTP/HTTPS for Android tablet usage.

## JSON Schema Versioning

- Key map-based stores use versioned envelope:
  - `{ "schema_version": 2, "items": { "<key>": { ... } } }`
- Legacy plain-map files are auto-migrated on read.
- Shared helpers live in `src/storage/schema_versioning.py`.

## Dashboard/KPI Path

- `src/services/kpi_service.py`:
  - computes monthly/supplier/trend KPI data
  - exposes cached payload for dashboard (`build_dashboard_payload`)
  - supports explicit cache reset via `refresh()`
- `src/tabs/dashboard/tab_dashboard.py`:
  - reads payload from `KPIService`
  - renders KPI cards + charts
  - refreshes asynchronously in GUI mode (background worker + timer)

## Theme and Accessibility

- Theme palette + app stylesheet: `src/app/main_window.py`
- Saved theme preferences: `src/app/app_settings.py` (`theme_mode`, `theme_motif`)
- Saved font scale: `src/app/app_settings.py` (`font_scale`)
- Settings UI: `src/tabs/rysunek/tab_rysunek.py`

## Runtime Modes

- Desktop GUI: standard app launch (`src/app/main.py`).
- Server/kiosk mode: app in HTTP/HTTPS mode for tablet clocking.
- Testing mode: `TECH_MODUL_TESTING=1` to simplify deterministic behavior in tests.
