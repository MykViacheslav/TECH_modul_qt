# WEB WORKSPACE MODUL SCIANA KOMPLET CODE MAP

## 1. Frontend: miejsca kluczowe

### Workspace host
- `C:\PythonProject\TECH_modul\frontend\src\app\workspace\page.tsx`
  - Docelowy shell dla trybow Modul/Sciana/Komplet.
  - Tu warto osadzic wspolny `WorkspaceState` i przełączanie kontekstu.

### Modul (aktualnie oddzielnie)
- `C:\PythonProject\TECH_modul\frontend\src\app\configuration\page.tsx`
  - Obecny editor modulu (preview/apply dla operacji modulowych).
  - Do refaktoru: wydzielenie komponentu panelu modulu do ponownego uzycia w workspace.

### Sciana (aktualnie oddzielnie)
- `C:\PythonProject\TECH_modul\frontend\src\app\wall\page.tsx`
  - Obecny flow punktow/sciany.
  - Do refaktoru: wydzielenie komponentu panelu sciany do workspace.

### Komplet / assembly (aktualnie oddzielnie)
- `C:\PythonProject\TECH_modul\frontend\src\app\assembly\page.tsx`
  - Obecny bulk-flow + assembly summary.
  - Do refaktoru: osadzenie jako tryb `Komplet` we wspolnym shellu.

### API client i typy
- `C:\PythonProject\TECH_modul\frontend\src\services\api.ts`
  - Istniejace metody:
    - `getProjectModules`
    - `getProjectAssemblySummary`
    - `getProjectWallSummary`
    - `previewModuleOperation` / `applyModuleOperation`
    - `previewBulkModuleOperation` / `applyBulkModuleOperation`
    - `getWallPoints`
    - `previewWallOperation` / `applyWallOperation`
  - Tu dodac ewentualnie `getWorkspaceSnapshot` (jesli backend doda endpoint agregujacy).

## 2. Backend/API: miejsca kluczowe

### API endpoints
- `C:\PythonProject\TECH_modul\src\api\main_api.py`
  - Konfiguracje:
    - `GET /config/wall/{project_id}` (linia ~371)
    - `GET /config/modules/{project_id}` (linia ~393)
    - `GET /projects/{project_id}/assembly-summary` (linia ~397)
    - `GET /projects/{project_id}/wall-summary` (linia ~413)
  - Operacje modulu:
    - `POST /operations/module/preview` (linia ~1826)
    - `POST /operations/module/apply` (linia ~1840)
    - `POST /operations/module/bulk/preview` (linia ~1903)
    - `POST /operations/module/bulk/apply` (linia ~1935)
  - Operacje sciany:
    - `POST /operations/wall/preview` (linia ~1970)
    - `POST /operations/wall/apply` (linia ~1984)

### Persistencja i agregacje
- `C:\PythonProject\TECH_modul\src\api\data_manager.py`
  - Tabele i pola:
    - `project_modules`
    - `spec_json`
    - `projects.obstacles_json`
  - Metody kluczowe:
    - pobieranie/updating modulu
    - pobieranie/updating obstacles
    - `get_project_assembly_summary`
  - Uwaga: wall/obstacles i modules maja split persistence (JSON + SQL), co trzeba kontrolowac na poziomie kontraktu.

## 3. Domain layer
- `C:\PythonProject\TECH_modul\src\domain\operations\module_ops.py`
  - logika operacji modułowych (preview/apply).
- `C:\PythonProject\TECH_modul\src\domain\operations\wall_ops.py`
  - logika operacji sciany.
- `C:\PythonProject\TECH_modul\src\domain\operations\adapters\sqlite_project_module_repository.py`
  - repozytorium modulu w SQLite.
- `C:\PythonProject\TECH_modul\src\domain\operations\adapters\wall_repository.py`
  - repozytorium danych sciany.
- `C:\PythonProject\TECH_modul\src\domain\wall_models.py`
  - model sciany (bogatszy niz to, co obecnie ujawnia web UI).
- `C:\PythonProject\TECH_modul\src\domain\assembly_models.py`
  - model assembly/komplet (obecnie czesciowo wykorzystany w web).

## 4. Minimalny plan zmian plikowych (Phase 1)

1. Zmodyfikowac:
- `frontend/src/app/workspace/page.tsx`
  - dodać wspolny shell i przełączanie trybow.

2. Wydzielic komponenty:
- nowy folder, np. `frontend/src/components/workspace/`
  - `WorkspaceShell.tsx`
  - `ModulePanel.tsx` (z `configuration/page.tsx`)
  - `WallPanel.tsx` (z `wall/page.tsx`)
  - `AssemblyPanel.tsx` (z `assembly/page.tsx`)

3. Zmodyfikowac:
- `frontend/src/services/api.ts`
  - utrzymac wspolne typy i metody dla wszystkich 3 trybow.
  - opcjonalnie dodać `getWorkspaceSnapshot`.

4. Opcjonalnie dodac backend endpoint:
- `src/api/main_api.py` (+ `data_manager.py` helper)
  - `GET /projects/{id}/workspace-snapshot`
  - tylko agregaty i licznikowe dane potrzebne do shella.

5. Nie zmieniac w Phase 1:
- fundamentu domain pricing/production poza wymaganym reuse operacji.
- pelnego modelu CAD/3D.

## 5. Checkpointy techniczne
- Po kazdym etapie sprawdzic:
  - brak regresji w `/configuration`, `/wall`, `/assembly`.
  - poprawne preview/apply.
  - poprawny reload danych projektu.
