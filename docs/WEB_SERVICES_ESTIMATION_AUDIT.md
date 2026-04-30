# WEB SERVICES & ESTIMATION AUDIT

**Date:** 2026-04-22  
**Codebase:** C:\PythonProject\TECH_modul  
**Auditor:** Claude Sonnet 4.6 (automated codebase inspection)

---

## 1. Executive Summary

The desktop application (PyQt6) is the fully working product. It has complete implementations of Services (Usługi), four estimation modes, a Quick Estimation calculator, a unified pricing summary, and the full Moduł → Ściana → Komplet → Wycena flow.

The web frontend (Next.js 14) is a modern parallel UI that shares the same FastAPI backend. It currently covers: workspace/project management, wall obstacle editing, 3D Constructor import, per-module production costing, and a basic AI agent for dimension changes. It does **not yet** have a Services tab, an Estimation Hub, Quick Estimation, or the full Moduł → Komplet → Wycena flow.

The FastAPI backend is more complete than the web frontend suggests — several estimation-relevant endpoints already exist but have no web UI consuming them.

---

## 2. Scope of This Audit

**Included:**
- Services tab / Usługi module (desktop and web)
- Estimation / pricing / wycena (all modes found in both layers)
- AI / agent estimation
- Moduł → Ściana → Komplet → Wycena flow
- Import-based estimation from 3D Constructor
- Quick estimation flows

**Intentionally excluded:**
- HR / RCP / Kiosk time tracking
- Finance hub (invoices, tax summaries)
- Calendar, alarms, operations hub
- Production terminals
- Email/Telegram integrations
- Database management screens (clients, materials, catalog)

---

## 3. Relevant Web Structure

### Pages (Next.js App Router)

| Route | File | Relevant to audit |
|---|---|---|
| `/workspace` | `frontend/src/app/workspace/page.tsx` | Project list and workspace overview |
| `/workspace/import` | `frontend/src/app/workspace/import/page.tsx` | 3D Constructor import wizard |
| `/wall` | `frontend/src/app/wall/page.tsx` | Wall obstacle editor |
| `/configuration` | `frontend/src/app/configuration/page.tsx` | Module list + production/pricing summary |
| `/orders/offer` | `frontend/src/app/orders/offer/page.tsx` | Offer/document builder |
| `/ai/predictions` | `frontend/src/app/ai/predictions/page.tsx` | AI rule-based predictions |
| `/simulations` | `frontend/src/app/simulations/page.tsx` | Simulations (scope unclear) |

**No web page exists for:** Services/Usługi, Quick Estimation, Estimation Hub, Wycena modes.

### Key Components

| Component | File | Purpose |
|---|---|---|
| `AgentPanel` | `frontend/src/components/AgentPanel.tsx` | NLP input → dimension change preview/apply |
| `PersistentAgent` | `frontend/src/components/PersistentAgent.tsx` | Always-visible agent panel wrapper |
| `ConfigurationValuationTab` | `frontend/src/components/configuration/ConfigurationValuationTab.tsx` | Production cost summary per module |
| `WallObstacleManager` | `frontend/src/components/WallObstacleManager.tsx` | Wall obstacle placement |

### Services (API layer)

| File | Purpose |
|---|---|
| `frontend/src/services/api.ts` | `TechModulAPI` — all typed API calls |
| `frontend/src/services/agent.ts` | `parseAgentCommand()` — sends NLP text to backend |
| `frontend/src/services/operations.ts` | `previewBulkModuleOperation` / `applyBulkModuleOperation` |
| `frontend/src/services/operation-contract.ts` | Maps operation changes to UI preview rows |
| `frontend/src/services/project-context.ts` | Selected project ID state |

---

## 4. Desktop Reference Structure

Used only as comparison for the four target areas.

### Services / Usługi

| File | Role |
|---|---|
| `src/tabs/uslugi/tab_uslugi.py` | Main Services tab — cennik editor + service quote builder |
| `src/tabs/baza_uslug/tab_baza_uslug.py` | Read-only service definitions catalog |
| `src/domain/service_models.py` | `ServiceDef` dataclass, `SERVICE_TYPES` constants |
| `src/storage/service_store_json.py` | JSON persistence for service definitions |
| `src/storage/service_component_store_json.py` | Service components |
| `src/services/project_model_service_adapter.py` | `build_service_quote_project_model()` |
| `data/services.json` | Live service definitions |
| `data/usluga_quotes.json` | Saved service quotes |
| `data/usluga_formula_profile.json` | Pricing formula profiles |

### Estimation / Wycena

| File | Role |
|---|---|
| `src/tabs/wycena/tab_wycena.py` | Main estimation tab (~153KB) — project/commercial/3D modes |
| `src/tabs/wycena_hub/tab_wycena_hub.py` | Hub: Wycena + Usługi + Rozkrój + Podsumowanie |
| `src/tabs/wycena/unified_summary_panel.py` | Merges 5 pricing sources into one summary |
| `src/tabs/szybka_wycena/tab_szybka_wycena.py` | Quick quote calculator (room sections) |
| `src/tabs/baza_szybkich_wycen/tab_baza_szybkich_wycen.py` | Quick quote archive |
| `src/tabs/sekcja_do_wyceny/tab_sekcja_do_wyceny.py` | Embedded 3D import estimation tab |
| `src/services/quote_pricing_service.py` | `QuotePricingService` — margin/VAT/transport rules |
| `src/services/project_model_cross_tab_adapter.py` | `merge_project_models()` (5 sources) |
| `src/core/costing/module_costs.py` | `calculate_module_cost_breakdown()` |
| `data/quote_pricing.json` | Pricing rules (processing%, assembly%, transport flat) |
| `data/quick_quote_in_progress.json` | In-progress quick quote state |

### AI / Agent

| File | Role |
|---|---|
| `src/api/agent_engine.py` | `TechModulAgent` — NLP command parser + valuation sheet parser |
| `src/core/assistant_context.py` | Desktop AI assistant context |
| `src/core/assistant_query_engine.py` | Query engine (desktop only) |
| `src/widgets/assistant_panel.py` | Desktop `AssistantPanel` widget |
| `src/widgets/assistant_avatar.py` | Desktop floating avatar |

### Moduł → Ściana → Komplet → Wycena

| File | Role |
|---|---|
| `src/tabs/modul/tab_modul.py` | Cabinet designer |
| `src/tabs/sciana/tab_sciana.py` | Wall scene + module placement (also used as Komplet) |
| `src/domain/wall_models.py` | `WallLayoutDef`, obstacles, measurements |
| `src/domain/assembly_models.py` | `FurnitureAssemblyDef`, `AssemblyModuleItemDef` |
| `src/domain/assembly_resolution_service.py` | `resolve_assembly_items()` → priced line items |
| `src/app/main_window_wiring.py` | Cross-tab signal wiring |
| `src/app/navigation_groups.py` | Tab groups: Projekt (Moduł/Komplet/Ściana) + Sprzedaż (Wycena) |

---

## 5. Services: Desktop vs Web

### Desktop — what exists

The desktop has a **fully functional Services module** with two sub-tabs in the Wycena Hub:

- **Cennik panel** (`_CennikPanel`): editable price list for service types. Categories include `wycinanie_oklejanie`, `fronty_surowe`, `lakierowanie`, `giete_elementy`, and others defined in `SERVICE_TYPES`.
- **Service quote builder** (`TabUslugi`): select client → pick services from cennik → set quantities → compute totals → save to `usluga_quotes.json`.
- **ProjectModel integration**: `build_service_quote_project_model()` converts a service quote into a `ProjectModel` with `ProjectServiceLine` and `ProjectQuoteLine` objects, feeding into the unified summary.
- **Service definitions catalog** (`TabBazaUslug`): read-only view of all service definitions.
- **Formula profiles**: `usluga_formula_profile.json` stores pricing formula presets.

### Web — what exists

**Nothing.** There is no Services page, no service cennik, no service quote builder, and no API endpoints for services. The `data/services.json` file exists and contains real data, but no web route reads or writes it.

### Status table

| Feature | Status |
|---|---|
| Service definitions catalog (view) | MISSING |
| Cennik / price list editor | MISSING |
| Service quote builder | MISSING |
| Service → ProjectModel adapter | MISSING (backend code exists, no web route) |
| Link to unified estimation summary | MISSING |
| Service quote archive/history | MISSING |

### Recommended target for web

A `/services` route with two sub-views:
1. **Cennik** — editable table of service types and prices, backed by a new `GET/POST/PATCH /api/services` endpoint.
2. **Nowa Wycena Usług** — select services + quantities → compute total → save → link to project.

---

## 6. Estimation Modes Found in the Codebase

### Mode 1 — Project / Handlowa Estimation (desktop)

**Where:** Desktop only (`src/tabs/wycena/tab_wycena.py`)  
**Status:** DONE (desktop), MISSING (web)  
**Input:** Project modules from `ProjectModel`, material catalog, pricing rules from `quote_pricing.json`  
**Output:** Price breakdown (material cost, labor, processing%, assembly%, transport, margin, VAT, architect commission)  
**Main files:** `tab_wycena.py`, `quote_pricing_service.py`, `module_costs.py`  
**Missing in web:** Full estimation UI with editable pricing rules, margin sliders, mode switcher

### Mode 2 — 3D Constructor Import Estimation

**Where:** Desktop (full dialog) + Web (import wizard, but no pricing step)  
**Status:** PARTIAL  
**Input:** `.project` XML file from 3D Constructor  
**Output (desktop):** `Constructor3dcQuoteImportData` → `ProjectModel` with `ProjectQuoteLine`s → unified summary  
**Output (web):** Parsed rows shown in table → finalize creates project record → redirects to `/configuration` — **no pricing computed**  
**Main files:** `import_router.py`, `constructor_3dc_quote_import_service.py`, `project_model_import_adapter.py`, `workspace/import/page.tsx`  
**Missing in web:** Material mapping step, price computation from imported data, connection to estimation output

### Mode 3 — Quick Estimation (desktop)

**Where:** Desktop only (`src/tabs/szybka_wycena/tab_szybka_wycena.py`)  
**Status:** DONE (desktop), MISSING (web)  
**Input:** Cabinet sections (Górne/Dolne szafki, Słupki, etc.) with room-level dimensions and quantities  
**Output:** Total price from catalog auto-pricing, saved to `quick_quote_archive.json`  
**Main files:** `tab_szybka_wycena.py`, `tab_baza_szybkich_wycen.py`, `quick_quote_in_progress.json`  
**Missing in web:** Entire feature

### Mode 4 — Service-Based Estimation (desktop)

**Where:** Desktop only (`src/tabs/uslugi/tab_uslugi.py`)  
**Status:** DONE (desktop), MISSING (web)  
**Input:** Service definitions (cennik), client, quantities  
**Output:** `ProjectModel` via `build_service_quote_project_model()`, feeds unified summary  
**Missing in web:** Entire feature (see Section 5)

### Mode 5 — Assembly / Komplet Estimation (desktop)

**Where:** Desktop only (`assembly_resolution_service.py`, connected to `tab_wycena.py`)  
**Status:** DONE (desktop), MISSING (web)  
**Input:** `FurnitureAssemblyDef` with module items  
**Output:** `resolve_assembly_items()` → priced line items per module → feeds unified summary  
**Missing in web:** Assembly definition UI, resolution service call, wiring to any pricing output

### Mode 6 — Valuation Sheet Text Parsing (backend + no web UI)

**Where:** Backend API exists (`POST /agent/parse-valuation-sheet`), no web page uses it  
**Status:** PARTIAL  
**Input:** Multi-line text: "Szafka dolna 600x820x560, dąb 2szt"  
**Output:** Structured list of `{name, width, height, depth, quantity, material_query}` items  
**Main files:** `agent_engine.py` (`parse_valuation_sheet()`), `main_api.py` line 384  
**Missing in web:** A UI that sends text → receives parsed items → computes pricing from catalog

---

## 7. Current Web Estimation Flow

The web currently has **one partial estimation path**:

```
1. User opens /workspace/import
2. Uploads .project file
3. POST /import-3d/parse → backend parses XML, returns rows + summary
4. User sees table of parts (sections, dimensions, materials)
5. User clicks "Finalizuj"
6. POST /import-3d/finalize → creates project record in SQLite, adds parts as modules
7. Redirect to /configuration?id=<project_id>
8. /configuration calls GET /api/production/project/{id}/summary
9. ProductionService computes module-level costs (material m2 * price + edgeband + assembly rate)
10. ConfigurationValuationTab displays: final_price, material_cost, labor_cost, per-module costs
```

**Where it breaks / is incomplete:**

- **Step 6 bug:** `finalize` maps imported parts as individual modules (each formatka/front becomes a module), not as cabinet assemblies. Depths are set to thickness_mm (e.g., 18mm) instead of actual cabinet depth.
- **Step 9:** `ProductionService` uses hardcoded rates (`RATE_CUTTING=5 PLN`, `RATE_EDGEBAND=4 PLN`, `RATE_ASSEMBLY=50 PLN`, `MARGIN_PERCENT=0.60`). These are not connected to the `quote_pricing.json` rules used by the desktop.
- **No margin editor:** `/projects/{id}/margin` endpoint exists and is typed in `api.ts`, but no web UI exposes it.
- **No pricing rules editor:** Processing %, transport, architect commission are not editable in web.
- **No PDF with real pricing:** The PDF export button (`/projects/{id}/export-pdf`) calls `generate_offer_pdf()` — this works but uses production summary data, not a full quote with all pricing modes.

**Result:** The web can show a rough cost estimate for a 3D-imported project, but the number is based on simplified rates and does not match the desktop Wycena output.

---

## 8. Module → Wall → Complete → Estimation Flow

### Desktop flow (complete)

```
Moduł (tab_modul.py)
  ↓ design cabinet → save to modules.json / SQLite
Ściana (tab_sciana.py)
  ↓ drag modules onto wall scene → layout saved to walls.json
Komplet (= TabSciana in assembly mode)
  ↓ named assembly → FurnitureAssemblyDef → assemblies.json
  ↓ resolve_assembly_items() → priced line items
Wycena (tab_wycena_hub.py → tab_wycena.py)
  ↓ merge_project_models() from 5 sources
  ↓ apply QuotePricingService rules
  ↓ UnifiedSummaryPanel shows final price
```

Signal wiring is handled in `main_window_wiring.py`. Cross-tab data flows via `ProjectModel` shared context.

### Web flow (partial)

```
/configuration
  ↓ lists modules from GET /config/modules/{project_id}
  ↓ shows per-module cost from ProductionService
/wall
  ↓ obstacle editor (windows/doors/sockets)
  ↓ wall points stored via /operations/wall/apply
```

**What is present in web:**
- Module list and per-module production cost (`ConfigurationValuationTab`)
- Wall obstacle placement (`WallObstacleManager`)
- Wall point storage (`/wall/{wall_name}` endpoint)
- Data types: `AssemblySummary`, `WallSummary`, `FinanceSummary` all defined in `api.ts`

**What is missing:**
- No wall scene with cabinet placement (only obstacle editor)
- No module-onto-wall drag placement in web
- No Komplet / assembly builder in web
- No assembly → pricing handoff in web
- No unified estimation output in web (only production cost approximation)
- `GET /projects/{id}/assembly-summary` exists in API and is typed, but no web page uses it meaningfully for pricing

**What would complete the flow in web:**
1. Wall scene with module placement (or a simplified list-based komplet builder)
2. Assembly definition → `resolve_assembly_items()` backend call
3. Estimation output page with editable pricing rules
4. Save and export as PDF offer

---

## 9. AI / Agent Estimation

### What exists in the backend

**`TechModulAgent`** (`src/api/agent_engine.py`):
- `parse_command(text)` — Polish NLP regex parser. Handles: set/increase/decrease + depth/width/height + value. Example: "zwiększ głębokość o 50" → `{action: modify_dimension, param: depth, value: 50, operation: add}`.
- `parse_valuation_sheet(text)` — multi-line text → structured item list. Example: "Szafka dolna 600x820x560, dąb 2szt" → parsed with regex for dimensions and quantities.
- Dimension constraints: depth 100–1200mm, width 150–2800mm, height 100–2500mm.
- **No LLM is used.** All parsing is regex-based.

**API endpoints for agent:**
- `POST /agent/command` — parse text, generate preview of dimension changes for all project modules
- `POST /agent/apply` — apply confirmed changes to SQLite
- `POST /agent/parse-valuation-sheet` — parse multi-line text into item list

**`/api/ai/predictions`** — rule-based delay/bottleneck/cost forecasting (no LLM). Uses overdue task count and load map to generate hardcoded prediction templates.

**`/api/ai/advisor`** — rule-based business tips. Checks overdue count, revenue unlock totals, missing materials. Returns canned tip text with real variable values inserted.

### What exists in the web frontend

**`AgentPanel.tsx`** — a polished UI component:
- Text input with Enter-to-submit
- Calls `parseAgentCommand(text, projectId)` → `POST /agent/command`
- Builds bulk operation groups from the response
- Calls `previewBulkModuleOperation` → `POST /operations/module/bulk/preview` for each group
- Shows diff preview (`OperationPreviewList`) with before/after values
- "Zatwierdź" button calls `applyBulkModuleOperation` → `POST /operations/module/bulk/apply`
- Safety message: "AI nigdy nie zmienia danych bez Twojego potwierdzenia"

**`/ai/predictions` page** — renders `AiPrediction[]` from `GET /api/ai/predictions`. Shows delay/bottleneck/finance predictions with severity badges and confidence bars.

### What the AI agent can and cannot do

| Capability | Status |
|---|---|
| Change module dimensions via text command | DONE |
| Preview changes before applying | DONE |
| Parse valuation sheet text into items | Backend DONE, no web UI |
| Estimate price from text description | MISSING |
| Suggest service prices | MISSING |
| Compute full quote from NLP input | MISSING |
| Use LLM (GPT/Claude/Gemini) | MISSING — no API keys, no model config, no LLM calls anywhere |
| AI prediction of delays | PARTIAL (rule-based templates, not true ML) |
| AI business advisor tips | PARTIAL (rule-based, not true AI) |

**Important:** Despite the name "AI estimation" and the "Tech Assistant / Asystent AI" label in the UI, there is **no actual machine learning or language model** in this codebase. All "AI" features are deterministic Python rules and regex parsers.

### Limitations

- Agent only modifies dimensions of modules. It cannot create a new module, delete one, assign materials, or compute pricing.
- `parse_valuation_sheet` returns structured items but does not look up prices in the catalog or compute any totals. There is no web page that uses this output.
- The desktop has a richer `AssistantPanel` (floating avatar, contextual messages, query engine) — none of this exists in web.
- No environment variables, feature flags, or model configuration for LLM integration exist in the codebase.

---

## 10. Imports and 3D Constructor Estimation

### What is implemented end-to-end

**Desktop:**
- `DialogImport3dcWycena` (~56KB) — full dialog with tabs: parse, mapping, GiB Lab export, result preview
- `TabSekcjaDoWyceny` — embeds the import dialog as a permanent tab in the desktop sidebar
- `parse_3dc_project_for_quote_import()` — XML parser for `.project` files. Extracts: formatki (panels), fronty (fronts), okucia (hardware), łączniki (fasteners), operacje (CNC). Returns `Constructor3dcQuoteImportData`
- `build_import_3d_project_model()` — converts import data into `ProjectModel` with `ProjectQuoteLine`s grouped by section
- `constructor_3dc_mapping_store_json.py` — stores material code mappings between 3DC and internal catalog
- Real sample files tested: `Jerzy_WYCENA.project`, `ZEUS_wc_szafka_Ola.project`, `Drawing2.project`, `Spiri.project`
- GiB Lab cutting optimization integration (`build_giblab_result_from_project_file()`)

**Web:**
- `/workspace/import` page — file upload → parse → table view → finalize
- `POST /import-3d/parse` — parses XML, returns rows + summary + modules list
- `POST /import-3d/finalize` — creates project, adds parts as modules, syncs to GitLab
- Typed in `api.ts`: `ImportResult`, `importParse()`, `importFinalize()`

### What is missing in web

| Feature | Status |
|---|---|
| File upload and parse | DONE |
| Table display of parsed rows | DONE |
| Material code → internal catalog mapping UI | MISSING (desktop has full mapper dialog) |
| GiB Lab cutting optimization step | MISSING |
| Pricing computation from imported data | MISSING |
| Section grouping in estimation output | MISSING |
| Import history / re-parse saved files | MISSING |
| Reverse export (web project → .project file) | Backend exists (`/api/production/project/{id}/export/project`), no web button |

### Known bug in `finalize`

The `/import-3d/finalize` endpoint adds each `Formatka` and `Front` row as an individual module. The `depth` is set to `thickness_mm` (typically 18mm). This means a project with 40 parts becomes 40 modules of 18mm depth — not a representation of actual cabinets. The desktop version handles this correctly because `DialogImport3dcWycena` assembles parts into logical furniture groups before creating `ProjectQuoteLine`s.

---

## 11. What Is Already Done in Web

- Project list, creation, and workspace overview
- Module list per project with per-module production cost (area, parts, PLN)
- Total project cost display (material cost + labor + final price with 60% margin)
- Wall obstacle editor (window, door, socket, pipe placement)
- Wall point storage via operations API
- 3D Constructor file upload, parse, and table display
- Project creation from 3D import (with limitations noted above)
- AI agent panel — text input for dimension changes with preview and confirm
- AI predictions page (rule-based delay/bottleneck alerts)
- PDF export button (production summary → PDF)
- Order creation (title, client, deadline, budget, status)
- Finance summary per project (margin, base_cost, total_net, VAT, gross, profit)
- Material database CRUD
- Client database CRUD
- MVP readiness checker per project

---

## 12. What Is Partially Done in Web

| Feature | What works | What is missing |
|---|---|---|
| 3D import | Upload, parse, table display, project creation | Material mapping, pricing, correct module grouping |
| Production pricing | Per-module cost shown in `/configuration` | Uses hardcoded rates, not connected to `quote_pricing.json` |
| AI agent | Dimension changes (text → preview → apply) | Cannot change materials, create modules, or estimate price |
| AI predictions | Page renders, API returns rule-based predictions | No real ML, finance prediction is hardcoded sample text |
| PDF export | Button exists, PDF generated | PDF uses production cost data, not a full quotation |
| Finance summary | `FinanceSummary` type and endpoint exist | No editable margin/pricing rules UI in web |
| Wall module | Obstacle editor works | No cabinet placement on wall, no module-onto-wall drag |

---

## 13. What Is Missing in Web Compared to Desktop

| Desktop feature | Web status |
|---|---|
| Services tab (Usługi) — cennik + quote builder | MISSING |
| Service definitions catalog (Baza Usług) | MISSING |
| Quick Estimation calculator (Szybka Wycena) | MISSING |
| Quick Estimation archive | MISSING |
| Estimation Hub (Wycena Hub) — 4 sub-tabs | MISSING |
| Full estimation mode: project/commercial pricing | MISSING |
| Unified Summary Panel (5 sources merged) | MISSING |
| Editable pricing rules (processing%, assembly%, transport) | MISSING |
| Margin / VAT / architect commission controls | MISSING (endpoint exists, no UI) |
| Komplet / assembly builder | MISSING |
| Module placement on wall scene | MISSING |
| Assembly → pricing resolution | MISSING |
| 3D import material mapping | MISSING |
| GiB Lab cutting optimization | MISSING |
| Valuation sheet text → items parser (UI) | MISSING (backend done, no web UI) |
| Desktop AI assistant (contextual, query-based) | MISSING |
| Service formula profiles | MISSING |
| Rozkrój (cutting plan) tab | MISSING |

---

## 14. UX / Product Gaps

### Services workflow
There is no services workflow in web. A user who wants to quote painting, edge-banding, or CNC cutting as a service cannot do anything in the web version.

### Estimation workflow
The web user sees a number in `ConfigurationValuationTab` but cannot understand how it was calculated, cannot change any pricing rules, cannot choose between estimation modes, and cannot generate a proper client-facing quotation (only a raw production PDF).

### Switching between estimation modes
The desktop has a clear mode switcher (project pricing / commercial pricing / 3D import) and a hub that shows all modes in one place. The web has none of this. A user importing a 3D project gets one number with no way to adjust it.

### Understanding results
`ConfigurationValuationTab` shows `final_price`, `material_cost`, and `labor_cost` without explaining what margin or rates were applied. The hardcoded 60% margin is invisible to the user.

### Editing inputs
No web user can change: pricing mode, margin percentage, processing surcharge, transport flat fee, architect commission, VAT rate. All of these are editable in the desktop.

### Viewing history / saved estimates
The desktop has `TabBazaSzybkichWycen` (quick quote archive) and `usluga_quotes.json` (service quotes). The web has no estimation history at all.

### AI estimation usability
The `AgentPanel` works well for its narrow purpose (dimension changes). However:
- It is not positioned as an "estimation" tool anywhere in the web
- A user trying to get a price quote by typing a description will be confused — the agent only changes dimensions
- `parse_valuation_sheet` output (which could be useful) is never shown in the web

---

## 15. Risks / Technical Debt

### Hardcoded pricing rates in `ProductionService`
`RATE_CUTTING = 5.0`, `RATE_EDGEBAND = 4.0`, `RATE_ASSEMBLY = 50.0`, `MARGIN_PERCENT = 0.60` are hardcoded constants in `src/api/production_service.py`. These are not read from `data/quote_pricing.json`. Any pricing the web shows will diverge from desktop quotes as soon as the owner adjusts rates in the desktop.

### `finalize` creates wrong module structure from import
`/import-3d/finalize` adds individual panel parts (formatki) as modules, not cabinets. Depth is set to thickness_mm. This is a silent correctness bug — the pricing shown after import is based on a structurally wrong model.

### Two separate pricing engines
The desktop uses `QuotePricingService` + `module_costs.py` + `UnifiedSummaryPanel`. The web uses `ProductionService` with hardcoded rates. These two engines will produce different numbers for the same project and will drift further apart as the project evolves.

### No shared estimation data contract
`ProjectModel` (the desktop's universal quote model) has no equivalent in the web. The web uses ad-hoc dict structures from the API. Any new estimation feature built in web will need to invent its own data model.

### `agent_engine.py` comment warning
At the bottom of `agent_engine.py` there is a comment block (lines 133–137) showing example API wiring as if it has not yet been integrated. The integration does exist in `main_api.py` (line 1049), but the comment suggests this file was written before full wiring was done and may contain outdated assumptions.

### Wall "Komplet" mapping
In the desktop `navigation_groups.py`, "Komplet" maps to the same `TabSciana` class. This works in desktop because the tab has two modes. In the web, `wall/page.tsx` is only an obstacle editor — there is no assembly/komplet mode. Any web implementation of Komplet will need to decide whether to build a separate page or extend the wall page.

### CORS is open
`allow_origins=["*"]` in `main_api.py`. Acceptable for local development, must be restricted before any public-facing deployment.

### Missing API endpoints for Services
There are no `GET/POST/PATCH/DELETE /api/services` endpoints. The entire services data layer exists only in JSON files consumed by the desktop. The web cannot interact with services data at all.

---

## 16. Recommended Web Build Order

### Priority 1 — Must build now

**1a. Fix the `/import-3d/finalize` module grouping bug**  
Why: Every estimate from 3D import is currently wrong.  
Dependency: `parse_3dc_project_for_quote_import` already returns module-level data — use it.  
Complexity: **medium**

**1b. Connect web pricing to `quote_pricing.json` (eliminate hardcoded rates)**  
Why: Web and desktop will show different numbers forever until this is fixed.  
Dependency: Expose pricing config via `GET /api/pricing-config` and update `ProductionService` to read it.  
Complexity: **low**

**1c. Editable margin and pricing rules UI in `/configuration`**  
Why: Users cannot trust a price they cannot adjust.  
Dependency: `/projects/{id}/margin` endpoint exists. Add sliders for processing%, transport, assembly%.  
Complexity: **low**

**1d. Services API endpoints (`GET/POST/PATCH /api/services`)**  
Why: Services tab cannot be built without backend data.  
Dependency: `service_store_json.py` and `service_models.py` already exist — just expose via FastAPI.  
Complexity: **low**

### Priority 2 — Should build next

**2a. Services tab in web (`/services`)**  
Why: Services are a significant revenue line that is completely invisible in web.  
Dependency: Priority 1d.  
Complexity: **medium** (UI with two sub-views: cennik editor + quote builder)

**2b. Estimation Hub page (`/estimation`) with project pricing mode**  
Why: Core product feature for the sales workflow.  
Dependency: Priority 1b, 1c.  
Complexity: **high** (margin sliders, pricing rule editor, quote line breakdown, PDF generation)

**2c. Valuation sheet text input UI**  
Why: `POST /agent/parse-valuation-sheet` already works — just needs a web page.  
Dependency: None, backend is ready.  
Complexity: **low** (textarea → parse → table with prices → save as estimate)

**2d. 3D import material mapping step**  
Why: Without material mapping, imported projects use wrong material prices.  
Dependency: Need `GET /api/materials` + mapping storage.  
Complexity: **medium**

### Priority 3 — Later improvements

**3a. Quick Estimation calculator (`/quick-estimate`)**  
Why: Fast ballpark quotes by room sections — useful for initial client contact.  
Dependency: Pricing config connected.  
Complexity: **medium**

**3b. Module placement on wall (Komplet builder)**  
Why: Completes the Moduł → Ściana → Komplet → Wycena flow in web.  
Dependency: Module list, wall page.  
Complexity: **high** (needs drag-drop canvas or list-based komplet builder)

**3c. Estimation history and saved quotes**  
Why: Users need to compare versions and retrieve past quotes.  
Dependency: Priority 2b.  
Complexity: **medium**

**3d. Real LLM integration for agent estimation**  
Why: Currently the "AI" agent is pure regex. A real LLM could handle: "estimate a kitchen with 8 lower and 6 upper cabinets, oak front".  
Dependency: Priority 2a, 2b (need services + pricing to be stable first).  
Complexity: **high** (model choice, prompt design, API key management, fallback)

---

## 17. Suggested Target Web Structure

### Services (`/services`)
```
/services
  ├── /services/catalog          — view all service definitions
  ├── /services/pricelist        — edit cennik (price per service type)
  └── /services/quote/new        — create new service-based quote
                                   (client → select services → quantities → total → save)
```

### Estimation (`/estimation`)
```
/estimation
  ├── /estimation/project/{id}   — full project quote with pricing rules
  │     • module list + unit prices
  │     • margin %, processing %, transport
  │     • VAT, architect commission
  │     • total breakdown + PDF export
  ├── /estimation/quick          — quick room-section calculator
  ├── /estimation/import         — 3D import wizard (move from /workspace/import)
  │     • upload → parse → material mapping → pricing → save
  └── /estimation/text           — valuation sheet text input → parsed items → pricing
```

### AI Estimation (`/agent`)
```
/agent
  ├── current AgentPanel embedded in workspace pages (keep)
  ├── /agent/valuation           — text → items → price lookup → quote (new)
  └── /ai/predictions            — keep, improve rule quality
```

### Module → Wall → Complete → Estimation flow
```
/project/{id}/modules            — module list + designer link (exists as /configuration)
/project/{id}/wall               — wall with cabinet placement (extend current /wall)
/project/{id}/assembly           — komplet builder: named groups of modules
/estimation/project/{id}         — pricing output (Priority 2b above)
```

---

## 18. Open Questions

1. **Should Services and Estimation be separate top-level routes, or one unified `/sales` hub (like the desktop Wycena Hub)?** This is a UX decision for the owner.

2. **Which estimation mode should be the default on web?** Desktop defaults to project pricing. Web might be better served starting with 3D import (since that's already partially there).

3. **Is the 60% margin hardcoded in `ProductionService` the real business margin, or just a development placeholder?** If it's real, it needs to be exposed as a setting rather than a constant.

4. **Does the web need to match the desktop Wycena output exactly, or is a simplified model acceptable?** The desktop has 5 merged sources — the web may only need 2 or 3 to be useful.

5. **Should the material mapping from 3D import be stored per-project or as a global code mapping?** The desktop stores a global mapping in `constructor_3dc_mapping_store_json.py`. The web import wizard currently throws away unmapped codes.

6. **Will the "Komplet" concept in web be a drag-drop wall scene or a simpler list-based assembly?** The full drag-drop scene is high effort. A list-based "add module to group" builder may be sufficient.

7. **Is there a plan to integrate an actual LLM for AI estimation?** If yes, which model and where will API keys be managed? This affects architecture decisions for Priority 3d.

---

## 19. Plain-language Summary for Owner

### What we already have in the web version

The web application works well for: creating projects, importing furniture designs from your 3D Constructor program, seeing a rough cost breakdown for each cabinet module, managing wall obstacles (windows, doors), and giving voice-style commands to change cabinet sizes. You can also export a basic PDF and manage your clients and materials database.

### What we do not have yet in the web

The web is missing the features that matter most for quoting and selling to clients:

- **No Services tab (Usługi)** — you cannot quote painting, edge-banding, or CNC services from the web. This entire business area is desktop-only.
- **No proper Estimation page** — the cost number shown is calculated with fixed rates that are not connected to your desktop pricing rules. You cannot change the margin, transport cost, processing surcharge, or commission from the web.
- **No Quick Estimation** — there is no fast calculator for "I need 6 lower and 8 upper cabinets, what does it cost?"
- **No Komplet / assembly builder** — you cannot group modules into a named set and price the whole set together.
- **3D import is incomplete** — after importing a 3D project, the pricing is based on wrong data (individual panels treated as modules). Material mapping is also missing.
- **The "AI" is not truly AI** — it works by fixed rules, not by understanding language. It can change sizes but cannot create estimates or suggest prices.

### What to build first

1. **Fix the 3D import pricing** — this is already partially working and will immediately produce correct numbers (1–2 days of work).
2. **Connect web pricing to your pricing rules file** — so that when you change rates in the desktop, the web reflects them too (1 day).
3. **Add an editable margin slider to the web** — so you can adjust the price per project without opening the desktop (half a day).
4. **Build the Services backend** — so the web can read and display your service price list (1 day).
5. **Build the Services page** — cennik editor and simple quote builder for services (2–3 days).
6. **Build a proper Estimation page** — full quote with all pricing lines, PDF export (3–5 days).

After these six steps, the web will cover the two most important sales workflows: **3D import → quote → PDF** and **service-based quote → PDF**.
