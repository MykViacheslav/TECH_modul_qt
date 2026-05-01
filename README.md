# TECH_modul

Desktop + kiosk system for order flow, workers, services, costs, and work-time registration (including Android tablet QR flow).

## Quick Start

- Working with real data safely
- Before making changes to production data, always create a backup using the following tool:
- Run: python scripts/backup_data.py
- This will back up the current data/ directory (or the directory defined by TECH_MODUL_DATA_DIR) into data_backups/backup_<timestamp> using a straightforward, offline copy (no encryption).
- If you’re using a sandbox data directory, ensure TECH_MODUL_DATA_DIR is set to that path before running the backup.

- Switching between data directories
- You can set the environment variable TECH_MODUL_DATA_DIR to point the application at a different data directory (e.g., a sandbox or production DB) without changing code:
- Windows: setx TECH_MODUL_DATA_DIR "C:\path\to\data"
- macOS/Linux: export TECH_MODUL_DATA_DIR=/path/to/data
- The app will use the directory from TECH_MODUL_DATA_DIR if provided; otherwise it uses the default <repo_root>/data.

```powershell
cd C:\PythonProject\TECH_modul
.\.venv\Scripts\python.exe .\src\app\main.py
```

## Run as Server (Tablet/Kiosk)

HTTP:

```powershell
.\.venv\Scripts\python.exe .\src\app\main.py --server --server-port 8000
```

HTTPS:

```powershell
.\.venv\Scripts\python.exe .\src\app\main.py --server --https --https-port 8443
```

## Debugging KPI Dashboard

- KPI core: `src/services/kpi_service.py`
- Dashboard tab: `src/tabs/dashboard/tab_dashboard.py`
- To force KPI recomputation: call `KPIService.refresh()`
- Dashboard refresh in GUI:
  - manual button refresh
  - periodic timer refresh
  - background worker for non-blocking updates

## Theme and Accessibility

- Theme settings tab: `src/tabs/rysunek/tab_rysunek.py`
- Supported motifs: `cream`, `blue`, `gray`, `green`, `contrast`
- Font scaling is persisted in settings (`font_scale`) and applied globally.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_kpi_service.py tests\test_dashboard_services_kpi.py tests\test_theme_accessibility.py
```

## MSI Tech Module

Moduł techniczny do obliczeń BOM, reguł okuć i konfiguracji modułów meblowych.

- Dokumentacja: [`docs/msi_tech_module/README.md`](docs/msi_tech_module/README.md)
- Architektura (Mermaid): [`docs/msi_tech_module/ARCHITECTURE.md`](docs/msi_tech_module/ARCHITECTURE.md)
- Flowchart procesu: [`docs/msi_tech_module/FLOWCHART.md`](docs/msi_tech_module/FLOWCHART.md)
- Kod bazowy: `src/modules/msi_tech/`

```python
from src.modules.msi_tech import TechModule, TechModuleService

module = TechModule(id="", name="Szafka 60", width_mm=600, height_mm=720, depth_mm=560)
bom = TechModuleService().calculate_bom(module)
```

## Documentation

- Architecture: `docs/architecture.md`
- Developer guide: `docs/developer_guide.md`
- Switching between data directories
- You can set the environment variable TECH_MODUL_DATA_DIR to point the application at a different data directory (e.g., a sandbox or production DB) without changing code:
- Windows: setx TECH_MODUL_DATA_DIR "C:\path\to\data"
- macOS/Linux: export TECH_MODUL_DATA_DIR=/path/to/data
- The app will use the directory from TECH_MODUL_DATA_DIR if provided; otherwise it uses the default <repo_root>/data.
- Quick switch between data directories via config file
- Run: python scripts/data_dir_config.py to apply settings from data_config.json (or data_config.json.template)
- Then run the application as usual.
