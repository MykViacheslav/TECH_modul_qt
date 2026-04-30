# UNIFIED SERVICE ITEM EDITOR PHASE 1 IMPLEMENTATION PLAN

## 1. Phase 1 Goal
Phase 1 must introduce one unified service-item editor where one row represents one real production item (formatka/element), regardless of source (manual, Excel-like list, or imported `.project`).

This solves the current problem of fragmented input flows and makes pricing, validation, and save behavior consistent and predictable.

## 2. Exact Scope
In scope:
- one unified row model for all current service modes
- one table-first editor structure for service items
- mapping of manual input, Excel-like logic, and `.project` imported rows into the same row model
- minimal backend/data alignment to persist unified rows
- reuse of existing backend pricing as single source of truth
- minimal frontend consolidation in current order/services flow
- validation/manual-review state display at row level

Out of scope:
- full app redesign
- full Excel import wizard with advanced mapping UI
- OCR/scan intake
- advanced CAD/CAM visualization
- advanced bulk spreadsheet operations
- customer portal features

## 3. Target Outcome After Phase 1
After Phase 1, user can:
- open one service-item table editor
- add rows manually in the same structure used by production sheets
- import `.project` rows into the same table
- edit row details (common + mode-specific)
- see backend-calculated price buckets and summary per row
- see row validation/manual-review status per row
- save and reopen order/project with rows preserved consistently

## 4. Current Starting Point
What exists:
- service pricing backend Phase 1 exists and calculates buckets
- `.project` import returns `technology_summary`
- frontend order flow already has service-related modes and pricing fields

What is fragmented:
- multiple mode-specific entry fragments exist instead of one unified table input model
- some mode buttons/paths are still functionally thin or partially disconnected
- row structure is not fully normalized around Excel/Giblab row logic

What will be reused:
- existing backend pricing endpoints and validation output
- existing imported `technology_summary`
- current order/project save path

## 5. Core Editor Principle
Core rule: one row = one formatka / one service item.

Why this is the bridge:
- manual entry naturally maps to one physical piece per row
- Excel sheets from customers already follow row-based item logic
- `.project` import also produces per-item rows that can be mapped 1:1

This gives one stable operational language for sales, technology, and production.

## 6. Target Unified Row Model
Unified row model must support all service items with one base structure.

Always visible/common fields:
- `row_id`
- `name`
- `description`
- `service_mode`
- `subtype`
- `base_material_id` / `base_material_name`
- `length_mm`
- `width_mm`
- `thickness_mm`
- `quantity`
- `texture_or_color`
- edge sides: `edge_top`, `edge_bottom`, `edge_left`, `edge_right`
- edge material refs: `edge_default_material_id`, `edge_top_material_id`, `edge_bottom_material_id`, `edge_left_material_id`, `edge_right_material_id`
- source flags: `source_type` (`manual`, `excel`, `project_import`)
- imported summary: `technology_summary` (nullable)
- pricing output: `material_cost`, `cnc_service_cost`, `finishing_cost`, `extra_cost`, `net_total`
- status output: `pricing_status`, `manual_review`, `validation_flags`, `summary_text`

Mode-specific/conditional fields:
- front milling: `front_model_code`, `front_model_name`, lacquer params
- veneer: side count, veneer type, veneer lacquer flags
- bent elements: geometry class, radius/shape fields
- extra layers list: `extra_layers[]` with `material_id`, `role`, `thickness_mm`, `coverage_mode`, `quantity_factor`, `notes`

## 7. Shared Table Structure
Recommended structure is table-first, inspired by Excel/Giblab row logic.

Main table columns (default visible):
- row no
- name
- material
- L
- W
- T
- qty
- texture/color
- top
- bottom
- left
- right
- mode
- subtype
- net_total
- status
- summary (short)
- actions (edit, duplicate, remove)

Row details/contextual panel should contain:
- mode-specific advanced fields
- extra layer editor
- full `technology_summary` view (collapsed blocks)
- validation details and manual-review reasons
- full pricing bucket breakdown

Side-based edge logic:
- quick mode: one default edge material for selected sides
- advanced mode: per-side material assignment
- selected side without valid material must trigger validation flag

Support simple and advanced:
- simple users can fill only common columns
- advanced users expand row details for deeper technology/finishing controls

## 8. Mode-Specific Extensions
Cutting:
- extra fields: optional cut class or priority
- common fields stay primary
- validation: base material, dimensions, qty required

Cutting + edgebanding:
- extra fields: edge mode (default/per-side), edge material assignment
- common fields stay primary
- validation: selected edges must have complete material assignment

Veneer:
- extra fields: veneer sides (1S/2S), veneer variant, optional lacquer on veneer
- common fields stay primary
- validation: base material + thickness + veneer side count required

Front milling + lacquer:
- extra fields: `front_model_code`, lacquer type/sides
- common fields stay primary
- validation: `front_model_code`, `base_material_id`, `thickness_mm` mandatory

Bent elements:
- extra fields: geometry class, shape/radius, complexity class
- common fields stay primary
- validation: base material + thickness + geometry class mandatory

## 9. Relationship to Imported `.project` Items
Imported rows should enter the same table as normal rows.

Auto-filled from import:
- name/part name
- dimensions and quantity
- material name when available
- `technology_summary`
- source marker (`project_import`)

Still manual-required:
- missing base/commercial fields needed for pricing rules
- finishing selections (lacquer, veneer, edge choices, extra layers)
- front model where needed

Coexistence rule:
- imported CNC summary contributes to CNC bucket
- manual finishing/material context contributes to finishing/material/extra buckets
- both are calculated together in one backend pricing result per row

## 10. Relationship to Customer Excel-Like Sheets
Unified editor should mirror recurring customer columns:
- material
- length
- width
- quantity
- texture
- name
- top / bottom / left / right
- description

Impact on row model:
- these columns become first-class common fields
- import mapping later can be direct with low transformation cost
- customer-provided formatki remain readable and editable without mode hopping

## 11. Required Backend/Data Changes
1. Unified row payload shape in order/project persistence.
- why: one backend contract for all row sources
- additive/breaking: additive
- migration risk: low

2. Schema version for unified service row payload.
- why: safe evolution and backward compatibility
- additive/breaking: additive
- migration risk: low

3. Row-level support for mode-specific fields and `extra_layers`.
- why: prevent split payloads and hidden UI state
- additive/breaking: additive
- migration risk: medium

4. Direct storage of imported `technology_summary` on row.
- why: stable CNC input traceability
- additive/breaking: additive
- migration risk: low

5. Row-level pricing/validation snapshot persistence.
- why: reopen behavior must keep backend result as source of truth
- additive/breaking: additive
- migration risk: low

Uncertainty:
- if current order `spec_json` size grows too much with large projects, a dedicated row table may be needed in later phase.

## 12. Required Frontend/Web Changes
1. Consolidate current service entry fragments into one table-first editor in order/services context.
- route/component area: current order new flow (`/orders/new`, services step)
- purpose: one row model across all sources
- implementation size: large

2. Add row details panel/drawer for mode-specific fields.
- area: service row edit action
- purpose: keep main table compact while supporting advanced fields
- implementation size: medium

3. Show backend pricing buckets and row status/flags in table and row details.
- area: row result columns + details section
- purpose: transparency and manual-review handling
- implementation size: medium

4. Add source-aware row creation actions.
- area: toolbar above table (add manual row, import from `.project`, later Excel mapping hook)
- purpose: merge all entries into same table
- implementation size: medium

What should NOT be redesigned now:
- global navigation
- non-service modules
- broad visual theme system
- unrelated dashboard layouts

## 13. File-Level Change Plan
Editor/UI layer:
- `frontend/src/app/orders/new/page.tsx`
  - why: current services step and row editing live here
  - expected change: consolidate editor state and render unified table + row details
  - modify existing
- `frontend/src/services/api.ts`
  - why: row payload typing and API integration
  - expected change: unified row DTO and response typing
  - modify existing

Pricing/backend integration:
- `src/services/service_pricing_phase1.py`
  - why: consume unified row input consistently
  - expected change: normalization adapter for unified row and validation mapping
  - modify existing
- `src/api/main_api.py`
  - why: pricing preview/save endpoints and payload persistence path
  - expected change: accept unified row payload version and return row-level results
  - modify existing

Data/persistence layer:
- `src/models/orders.py` or current order storage schema module (exact file depends on active storage implementation)
  - why: persistent unified rows with schema version and pricing snapshots
  - expected change: additive payload fields
  - modify existing
- optional new mapper file, e.g. `src/services/unified_service_row_mapper.py`
  - why: keep normalization logic modular
  - expected change: new mapping/validation helpers
  - create new file

Import alignment:
- `src/services/constructor_3dc_quote_import_service.py`
  - why: ensure import output maps cleanly to unified row model
  - expected change: mapping metadata for row creation (no parser redesign)
  - modify existing
- `src/api/import_router.py`
  - why: expose import rows in shape compatible with unified editor ingestion
  - expected change: response mapping extension
  - modify existing

## 14. Recommended User Flow
select service mode
→ add/edit rows in one table
→ fill common fields (material, dimensions, qty, texture, sides)
→ fill mode-specific details in row panel
→ attach/import CNC `technology_summary` if available
→ request backend pricing preview for row
→ view price buckets + summary + validation/manual-review flags
→ correct missing fields if needed
→ mark row ready when validation passes
→ save full row list into order/project context

## 15. Validation Rules for Phase 1
- side-based edgebanding: each selected side must have valid edge material (default or per-side)
- front milling + lacquer: requires `front_model_code`, `base_material_id`, `thickness_mm`
- veneer: requires `base_material_id`, `thickness_mm`, veneer side count
- bent elements: requires `base_material_id`, `thickness_mm`, geometry class
- imported rows missing pricing-critical fields remain `manual_review`
- unknown CNC operations must create validation flag and cannot silently finalize
- missing required inputs must block ready/final state

## 16. Test Plan
Minimum coverage:
- manual-only row tests (all core modes)
- imported-row tests (`technology_summary` present)
- mixed-row tests (imported CNC + manual finishing/layers)
- edge side assignment tests (`top/bottom/left/right`)
- row persistence and reload tests
- backend pricing integration tests per row
- manual-review/validation flag behavior tests
- summary text display consistency tests

## 17. Rollout Order
1. Freeze unified row schema + schema version.
2. Add backend row normalizer and validation mapper.
3. Align preview/save endpoints to unified row payload.
4. Add persistence fields for unified row list and row pricing snapshots.
5. Refactor services step to one table-first row editor.
6. Add row details panel for mode-specific fields.
7. Connect imported `.project` rows into same table model.
8. Expose backend bucket/status/summary in UI.
9. Run integration and regression tests.
10. Perform manual acceptance run with real production-like rows.

## 18. Main Risks in Phase 1
- risk: payload bloat in order JSON for large projects.
  - mitigation: keep row schema compact and store only normalized summaries.
- risk: temporary dual-state during migration from old fragments.
  - mitigation: feature-flag unified editor path and keep one conversion layer.
- risk: mode-specific validation confusion for users.
  - mitigation: clear row-level required-field hints and explicit manual-review reasons.
- risk: import mapping mismatches across `.project` variants.
  - mitigation: keep import-to-row mapper isolated and test with known sample sets.

## 19. Definition of Done
Phase 1 is done when:
- one unified table editor is used for service rows
- manual and imported rows coexist in same table
- backend pricing is displayed per row with all buckets
- row-level validation/manual-review status is visible and enforced
- save/reload preserves unified rows, pricing snapshots, and summaries
- core mode rules pass test suite and manual acceptance checklist

## 20. What Must Wait for Phase 2
- full customer portal for direct row uploads
- advanced Excel import wizard with interactive mapping UI
- advanced row templates/presets library
- high-volume bulk operations with spreadsheet-grade tooling
- CAD/CNC visualization/drawing previews in editor
- OCR/scan intake from paper service sheets

## 21. Plain-Language Summary for Owner
This phase gives one common table where every service item is entered the same way: one row per real part.

It is better than separate forms because your team will stop jumping between different screens and rules. Manual entries, customer Excel habits, and imported CNC `.project` data all meet in one place.

That means clearer work, fewer mistakes, and stable backend pricing for each row before saving orders.
