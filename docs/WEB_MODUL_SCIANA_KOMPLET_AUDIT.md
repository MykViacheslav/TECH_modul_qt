# WEB MODUL SCIANA KOMPLET AUDIT

## 1. Executive Summary
Web `Modul` is the most mature of the three areas: it has real backend-backed edit operations (preview/apply) and persisted module state in SQLite (`project_modules` + `spec_json`). `Sciana` exists, but currently as a simplified point tool (utilities points), not a full wall-layout workflow. `Komplet` in web is partially real: the `/assembly` page is operationally useful for bulk module changes and module-level aggregates, but it does not expose the richer assembly domain model as a first-class persisted web entity.

## 2. Scope of This Audit
Included:
- Web frontend routes/components and API client used by `Modul`, `Sciana`, `Komplet`.
- Backend endpoints, domain operations, and persistence used by those routes.
- Real current data flow and save/load behavior.

Excluded:
- Unrelated modules (invoices, warehouse, services pricing, dashboard KPI, etc.).
- Desktop-only UI logic except where needed to explain missing/partial web parity.
- Redesign proposals or implementation.

## 3. Relevant Web Structure
Frontend routes/pages:
- `frontend/src/app/configuration/page.tsx` (Modul editor).
- `frontend/src/app/wall/page.tsx` (Sciana point tool).
- `frontend/src/app/assembly/page.tsx` (Komplet-oriented bulk management view).

Frontend services:
- `frontend/src/services/api.ts`
  - `getProjectModules(projectId)` -> `/config/modules/{project_id}`
  - `getProjectAssemblySummary(projectId)` -> `/projects/{project_id}/assembly-summary`
  - `getProjectWallSummary(projectId)` -> `/projects/{project_id}/wall-summary`
  - `getWallPoints(wallName)` -> `/wall/{wall_name}`
  - module ops: `/operations/module/preview|apply`, `/operations/module/bulk/preview|apply`
  - wall ops: `/operations/wall/preview|apply`
  - obstacles: `/projects/{project_id}/obstacles`

Backend/API:
- `src/api/main_api.py`
  - `/config/modules/{project_id}`
  - `/projects/{project_id}/assembly-summary`
  - `/config/wall/{project_id}`
  - `/projects/{project_id}/wall-summary`
  - `/wall/{wall_name}`
  - `/operations/module/...` and `/operations/wall/...`
- `src/api/data_manager.py`
  - `project_modules` storage and aggregate summaries.
  - `projects.obstacles_json` read/write.
- `src/domain/operations/module_ops.py`
- `src/domain/operations/wall_ops.py`
- `src/domain/operations/adapters/sqlite_project_module_repository.py`
- `src/domain/operations/adapters/wall_repository.py`
- `src/storage/wall_store_json.py`

Domain models (important for gap analysis):
- `src/domain/wall_models.py` (rich wall model exists in domain).
- `src/domain/assembly_models.py` (rich assembly/komplet model exists in domain).

## 4. Moduł — Current State
Current UI structure:
- Multi-tab module editor in `configuration/page.tsx` (`main`, `options`, `fittings`, `settings`, `cam`) plus 3D viewer and part inspector.
- Module selection from loaded project modules.

Current editable inputs:
- Dimensions (width/height/depth), carcass/front materials, edgebands, many hardware and construction options, part-level properties, visibility/locks, finish flags, etc.

Current preview/rendering:
- Uses operation contract flow: preview first, then apply.
- 3D viewer is present and interactive (`Module3DViewer`).

Current generated outputs:
- Module valuation (`/config/modules/{module_id}/valuation`).
- Production-part related data and part inspector interactions are present in UI.

Current save/load behavior:
- Load: `/config/modules/{project_id}`.
- Write: operation endpoints (`/operations/module/preview|apply`, bulk equivalents).
- Persistence: SQLite `project_modules` columns + full JSON in `spec_json` via repository adapter.

What works:
- Real backend mutation pipeline for module edits.
- Preview/apply contract is implemented.
- Core module persistence is real.

What is partial:
- Some UI actions in module/assembly areas are placeholders (for example visible add/copy/delete buttons without complete backend flow in current page context).
- Not all rich module fields are guaranteed to be consistently surfaced by the read endpoint (`get_project_modules` mostly returns core SQL columns).

What is broken or unclear:
- Potential read/write model mismatch: many advanced fields are written into `spec_json`, while list endpoint is SQL-column centric; exact parity of all edited fields in every view is uncertain without deeper runtime verification.

## 5. Ściana — Current State
Current UI structure:
- `wall/page.tsx` is a point-placement canvas with three tools (`bolt`, `droplet`, `flame`) representing utility points.

Current wall model:
- Web flow currently uses `WallOperations.get_points()` abstraction (id/type/x/y point list).
- Domain has richer `WallLayoutDef` (layout type, dimensions A/B/C, island params, obstacles, photos, measurements), but web page does not expose most of that model.

Obstacles / points / geometry handling:
- Points are stored as mapped obstacles (`socket`, `plumbing`, `pipe`) with prefixed names.
- Geometry handling in web page is 2D click coordinates only.
- No full wall contour editing, no true obstacle dimension editor, no full measurement/photo workflow in this page.

Module placement support:
- No direct module-on-wall placement workflow in current `wall/page.tsx`.

Save/load behavior:
- Read points: `/wall/WEB_PROJECT_{projectId}`.
- Mutations: `/operations/wall/preview|apply` for add/remove point.
- Persistence backend for wall ops uses JSON wall repository (`WallStoreJson`), not SQLite.

What works:
- Real preview/apply operations for adding/removing points.
- Points persist and reload.

What is partial:
- `/config/wall/{project_id}` derives width/height heuristically from max point coordinates, not from a full wall design model.

What is missing:
- Rich wall editing (segments, angles, obstacle dimensions, full room context).
- Practical module placement and collision/layout logic in wall UI.
- Strong linkage between wall definition and komplet composition.

## 6. Komplet — Current State
Whether Komplet is real entity or UI variant:
- In domain layer, `FurnitureAssemblyDef` is a real entity (`src/domain/assembly_models.py`).
- In current web, `/assembly` behaves mainly as a module bulk-operation workspace and summary view, not a full CRUD editor of `FurnitureAssemblyDef`.

Current UI structure:
- Module list with selection.
- Aggregate cards from assembly summary endpoint.
- Bulk operations panel (set dimensions, add shelves, change material) with preview/apply.

Relation to Moduł and Ściana:
- Strongly tied to modules from `project_modules`.
- Very weak direct tie to full wall layout; current summary only counts wall points on separate endpoint.

Save/load behavior:
- Loads modules + aggregate summary via `/config/modules/{project_id}` and `/projects/{project_id}/assembly-summary`.
- Mutations happen via bulk module operation endpoints.
- No dedicated web endpoint set observed for persisting a full standalone komplet/assembly object with full assembly fields in this route.

What works:
- Useful bulk manipulation of module set.
- Real backend aggregate summary for project module set.

What is partial:
- Komplet as conceptual assembly exists, but web implementation is narrower (module set operations) than domain model capability.

What is missing:
- Full web-level assembly entity lifecycle (explicit assembly create/edit/select/save) aligned to `FurnitureAssemblyDef` richness.

## 7. Data Flow Between Moduł, Ściana, and Komplet
Current practical flow:
- `Modul` and `Komplet` (web assembly page) share the same module source (`project_modules` in SQLite).
- `Komplet` operations mutate module records through bulk module ops.
- `Sciana` stores point data in wall JSON store keyed by wall name (`WEB_PROJECT_{id}`).

Observed weakness:
- Data bridge between `Sciana` and `Komplet` is minimal in web (mostly separate tracks: wall points vs module set).
- No strong current end-to-end flow where wall geometry drives module placement in a robust persisted relationship.

## 8. Current Persistence and Model Quality
What is persisted:
- Modules: persisted in SQLite (`project_modules`) with core columns and `spec_json`.
- Wall points: persisted in JSON wall store via wall operations.
- Obstacles list in projects table (`projects.obstacles_json`) is also persisted, but wall page primary flow uses wall operations store.

What is not fully persisted in a unified way:
- Full wall layout/measurements workflow in web UI.
- Full komplet assembly object lifecycle in web route parity with domain model.

Model stability:
- Module operations model is relatively stable and operational.
- Wall model in web is simplified and stable for point use-case only.
- Komplet model quality is mixed: domain is rich, web usage is narrower.

Mismatches between UI and stored data:
- Potential mismatch between advanced module UI fields and SQL-list endpoint fields (spec JSON vs flat row response).
- Wall-related data appears split between project obstacles JSON and wall store JSON paths.

## 9. UX / Product Gaps
- `Sciana` lacks full practical wall-design workflow (dimensions, rich obstacle editing, layout context).
- `Komplet` in web feels like "bulk edit modules" rather than full komplet orchestration.
- Weak visible flow connecting wall definition to assembly/module arrangement.
- Some controls in module/assembly views look present but are not fully operational actions in current state.

## 10. Main Risks / Technical Debt
- Dual persistence patterns (SQLite modules vs JSON wall store) increase integration risk.
- Rich domain models not fully reflected in web UI can cause expectation/behavior mismatch.
- SQL-column-centric module list endpoint may under-communicate data actually edited in `spec_json`.
- Weak Moduł-Sciana-Komplet linkage may force rework later when implementing real wall-driven assembly.

## 11. Best Development Order
Recommended safest order:
1. `Modul`
2. `Sciana`
3. `Komplet`

Why:
- `Modul` is already strongest and should be made model-consistent first (read/write parity and stable schema exposure).
- `Sciana` should then be expanded from point tool toward reliable wall model inputs.
- `Komplet` should be finalized after `Modul` and `Sciana` contracts are stable, because komplet depends on both module definition and wall context.

## 12. Recommended Phase 1 for This Area
Realistic Phase 1 for these tabs only:
- Stabilize module read/write parity:
  - ensure key advanced edited fields are consistently available where needed.
- Consolidate wall data contract:
  - keep current point workflow, but formalize one canonical persisted representation and mapping.
- Add explicit minimal Komplet entity contract in web context:
  - deterministic linkage to module set and wall reference (even before full rich editor).
- Add integrity checks between these three tabs:
  - clear status when wall context is missing,
  - clear status when komplet references modules not aligned with current project set.

## 13. Plain-Language Summary for Owner
What is already usable:
- `Modul` is usable today and does real save/edit through backend.
- Basic `Sciana` point marking works.
- `Komplet` page can manage many modules at once.

What is not yet ready:
- Full wall planning in web (beyond points).
- Full komplet workflow as one rich object (as in deeper domain model).
- Strong automatic connection between wall layout and komplet arrangement.

What to fix first:
- First stabilize `Modul` data consistency.
- Then make `Sciana` a real wall input (not only points).
- Then complete `Komplet` as a true assembly workflow linked to both modules and wall.
