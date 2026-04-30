# TECH_modul - Architecture Map

This document provides a comprehensive overview of the system's database, testing, and seeding architecture.

## 1. Database Architecture

The system is transitioning from a JSON-based storage to a relational SQLite database.

### 1.1 SQLite Database (`data/tech_modul.db`)
The core schema is defined in [sqlite_db.py](file:///c:/PythonProject/TECH_modul/src/storage/sqlite_db.py).

#### Core Tables:
- **Orders**: `orders` (code, client, status, dates, spec_json).
- **Projects & Modules**: `projects`, `project_modules` (placement, dimensions, family).
- **Materials & Catalog**:
    - `materials`: Current stock and basic library.
    - `catalog_items`: Central registry of industrial materials/hardware.
    - `catalog_item_variants`: Specific sizes/finishes for catalog items.
    - `manufacturers`, `producer_collections`, `material_categories`.
- **CRM & HRM**: `clients`, `workers`.
- **Operations**:
    - `material_transactions`: Stock movements, purchases.
    - `calendar_events`: Production scheduling, montages.
    - `alarms`: System-wide alerts and issue tracking.
- **Finance**: `suppliers`, `supplier_item_links`, `price_history`, `invoices`, `invoice_line_items`.
- **Infrastructure**: `settings` (key-value pairs for app state).

### 1.2 Legacy JSON Storage
Some modules still utilize JSON files for persistence (located in `data/`):
- `access_control_store_json.py`: Permissions and roles.
- `alarm_store_json.py`: Backup/legacy alarms.
- `avatar_store_json.py`: User profile icons.
- `receptura_store_json.py`: Product formulas.
- `service_pricing_tariff_store_json.py`: Pricing rules.

---

## 2. Testing Architecture

The system uses **Pytest** with a mix of unit, integration, and E2E tests.

### 2.1 Test Categories
- **Smoke Tests**: Basic health checks (e.g., [test_smoke.py](file:///c:/PythonProject/TECH_modul/tests/test_smoke.py)).
- **Golden Path (E2E)**: Simulates full user workflows from order to production (e.g., [test_golden_path_core_workflow_smoke.py](file:///c:/PythonProject/TECH_modul/tests/test_golden_path_core_workflow_smoke.py)).
- **API Tests**: Testing FastAPI endpoints (e.g., `tests/test_api_*.py`).
- **Domain Logic**: Testing pure business rules without UI (e.g., costing, material resolution).
- **UI Tests**: PyQt6 widget and tab testing using `QApplication.processEvents()` for async logic.

### 2.2 Configuration
- `pytest.ini`: Root test config.
- `tests/conftest.py`: Shared fixtures (e.g., `qapp` for GUI tests).
- `TECH_MODUL_TESTING=1`: Environment variable to enable deterministic behavior.

---

## 3. Seeding & Initialization

### 3.1 Initialization
The [db_init.py](file:///c:/PythonProject/TECH_modul/src/storage/db_init.py) script handles:
- Creating the SQLite database if missing.
- Migrating legacy JSON files into SQLite.
- Triggering demo seeds.

### 3.2 Seeding Strategies
- **Auto-Seed**: `data_manager.py` contains `seed_demo_*` methods that populate empty tables with basic examples (Demo Project, 2 Cabinets, Standard Materials).
- **Developer Seed**: A dedicated endpoint `POST /api/dev/seed` in `main_api.py` populates the system with professional sample orders and production data.
- **Scratch Seeds**: Utility scripts like [seed_catalog.py](file:///c:/PythonProject/TECH_modul/scratch/seed_catalog.py) for bulk industrial data ingestion.

---

## 4. The 8 Core Areas

Based on the current codebase and documentation, the system is organized into 8 functional areas:

1. **Dashboard & KPI**: Business analytics and monitoring.
2. **Materials & Catalog**: relational material library and stock management.
3. **Invoices & Purchases**: Supply chain and financial document processing.
4. **Project & Wall Config**: Technical layout and room planning.
5. **Production (Komplet)**: Module assembly and cutting list generation.
6. **Workstations (Stanowiska)**: Real-time worker tracking and station flow.
7. **Scheduling (Kalendarz)**: Order deadlines and worker assignments.
8. **Knowledge Base (Codex)**: Technical documentation and AI-assisted queries.
