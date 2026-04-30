# SERVICE PRICING PHASE 1 IMPLEMENTATION PLAN

## 1. Phase 1 Goal
Phase 1 must deliver a reliable, explainable service-pricing engine that calculates one stable net breakdown per item by combining:
- imported `.project` CNC technology parameters (`technology_summary`),
- manual service inputs,
- base material and thickness,
- extra material layers,
- front model and side-based edgebanding rules.

Business problem solved:
- today pricing is partly hardcoded in web UI and not consistently reusable,
- imported CNC details are not yet operationally converted into pricing buckets,
- required-input validation is not strict enough for production-safe quotations.

## 2. Exact Scope
In scope:
- unified service item schema (imported + manual)
- tariff/config model outside UI code
- CNC bucket pricing from `technology_summary`
- manual mode calculators for current modes
- combination logic (CNC + manual finishing/layers)
- summary text generation
- validation/manual-review rules
- focused backend/frontend test coverage

Out of scope:
- exact machine-time simulation
- CAM optimization
- workstation scheduling
- AI estimation
- advanced discount engine
- full external customer portal
- full UI redesign
- advanced analytics
- supplier/warehouse redesign
- production planning

## 3. Target Outcome After Phase 1
After Phase 1, the flow should work like this:
1. User creates a service item manually or imports from `.project`.
2. Item is normalized to one unified service item structure.
3. Base material and base thickness are attached (mandatory for required modes).
4. Extra layers are attached as explicit structured rows.
5. Imported CNC summary is attached when available.
6. Engine calculates:
- `material_cost`
- `cnc_service_cost`
- `finishing_cost`
- `extra_cost`
- `net_total`
7. Engine generates short technology/pricing summary text.
8. Engine assigns status:
- `ready` if all required inputs exist,
- `manual_review` if pricing-critical fields are missing or uncertain.
9. API returns full breakdown + flags to UI.

## 4. Current Starting Point
What already exists:
- `.project` import enrichment in [constructor_3dc_quote_import_service.py](C:\PythonProject\TECH_modul\src\services\constructor_3dc_quote_import_service.py) with `technology_summary`.
- import endpoint returning rows via [import_router.py](C:\PythonProject\TECH_modul\src\api\import_router.py).
- frontend type support for imported tech summary in [api.ts](C:\PythonProject\TECH_modul\frontend\src\services\api.ts).

What is partially built:
- service modes and estimator UI exist in [orders/new/page.tsx](C:\PythonProject\TECH_modul\frontend\src\app\orders\new\page.tsx).
- pricing is currently hardcoded in frontend `useMemo` (static rates), not tariff-driven backend logic.

What will be reused:
- current `.project` parser enrichment,
- current order persistence using `spec_json` in `POST /orders` (from [main_api.py](C:\PythonProject\TECH_modul\src\api\main_api.py)).

Codebase contradiction to pricing spec:
- spec requires strict mandatory rules (for example front model/material/thickness), while current UI estimator still allows fallback-like behavior and local-only calculation.

## 5. Required Data Model Changes
1. Unified service item schema (new, additive)
- why: one structure for manual and imported items.
- change: add normalized item payload under order `spec_json` (Phase 1) and optionally dedicated store later.
- additive/breaking: additive.
- migration risk: low.

2. CNC technology summary attachment (existing + formalized)
- why: pricing must read imported CNC metrics directly.
- change: preserve `technology_summary` per item in normalized item payload.
- additive/breaking: additive.
- migration risk: low.

3. Base material fields (required in selected modes)
- fields: `base_material_id`, `base_material_name`, `base_thickness_mm`.
- why: mandatory for front milling+lacquer, veneer, bent elements.
- additive/breaking: additive.
- migration risk: low.

4. Extra layer fields (new structured list)
- fields per layer: `material_id`, `role`, `thickness_mm`, `coverage_mode`, `quantity_factor`, `notes`.
- why: production-real extra material costing and transparency.
- additive/breaking: additive.
- migration risk: low.

5. Front model fields (mandatory for front milling + lacquer)
- fields: `front_model_code`, `front_model_name`.
- why: commercial model/pattern logic must drive pricing.
- additive/breaking: additive.
- migration risk: low.

6. Side-based edge configuration
- fields: `edge_mode` (`default` or `per_side`), `edge_default_material_id`, `edge_top_material_id`, `edge_bottom_material_id`, `edge_left_material_id`, `edge_right_material_id`.
- why: practical edge assignment by side.
- additive/breaking: additive.
- migration risk: medium (validation complexity).

7. Price breakdown buckets
- fields: `material_cost`, `cnc_service_cost`, `finishing_cost`, `extra_cost`, `net_total`.
- why: stable transparent output contract.
- additive/breaking: additive.
- migration risk: low.

8. Summary and validation fields
- fields: `summary_text`, `pricing_status`, `validation_flags[]`, `manual_review_reason[]`, `estimated_flags`.
- why: prevent silent pricing failures.
- additive/breaking: additive.
- migration risk: low.

## 6. Required Tariff/Configuration Changes
Tariffs must move outside UI code and start in backend-managed config.

Recommended Phase 1 storage choice:
- JSON-backed config in backend repository (fast, safe rollout), with clear schema for later DB migration.

1. Drilling tariffs
- fields: `base_per_hole`, diameter bands, depth modifiers, min charge.
- storage: JSON in backend.
- risk: low.

2. Groove tariffs
- fields: `setup_per_groove`, `per_meter`, depth/width factors.
- storage: JSON.
- risk: low.

3. Milling tariffs
- fields: `setup_per_path`, `per_meter`, arc surcharge, estimated-length factor.
- storage: JSON.
- risk: medium (geometry uncertainty handling).

4. Lacquer tariffs
- fields: lacquer class, coats, side count, prep factor by thickness/material class.
- storage: JSON.
- risk: medium.

5. Veneer tariffs
- fields: veneer class, side count factor, glue/prep surcharge, optional lacquer add-on.
- storage: JSON.
- risk: low.

6. Bent-element tariffs
- fields: shape class, complexity class, radius bands, setup + per unit/meter.
- storage: JSON.
- risk: medium.

7. Complexity multipliers
- fields: score bands (`low/medium/high/very_high`) and multiplier/surcharge.
- storage: JSON.
- risk: low.

8. Extra-layer surcharges
- fields: role-based surcharge map (`overlay`, `decorative_layer`, `reinforcement`, `glued_mdf`, `veneer_layer`, `substrate_addition`).
- storage: JSON.
- risk: low.

## 7. Required Backend/API Changes
1. New service pricing domain/calculator layer
- purpose: compute all pricing buckets from normalized item + tariffs.
- request/response impact: new pricing payload under order spec and/or dedicated preview endpoint response.
- reuse/new: reuse existing quote-pricing patterns conceptually, build new service-specific calculators.
- risk: medium.

2. Combination logic service (imported + manual)
- purpose: merge `technology_summary` and manual finishing/layer context.
- impact: enriched item output with buckets and flags.
- reuse/new: mostly new.
- risk: medium.

3. Validation rules engine
- purpose: enforce required fields and manual-review status.
- impact: response includes `pricing_status`, `validation_flags`, `manual_review_reason`.
- reuse/new: new.
- risk: low.

4. Endpoint adjustments
- purpose: expose backend-calculated pricing results to web instead of frontend-only hardcoded formula.
- impact (high level):
  - adjust order create/update payload handling to accept normalized service item data,
  - optionally add pricing preview endpoint for item-level recalculation.
- reuse/new: reuse existing `/orders` persistence path (`spec_json`) first.
- risk: medium.

5. Summary generation in backend
- purpose: consistent quote-table string independent of UI.
- impact: summary text in item payload.
- reuse/new: new helper.
- risk: low.

## 8. Required Frontend/Web Changes
1. Service item editor in [orders/new/page.tsx](C:\PythonProject\TECH_modul\frontend\src\app\orders\new\page.tsx)
- purpose: send normalized fields (including mandatory pricing inputs), stop relying only on local formula.
- size: medium.

2. Imported `technology_summary` visibility (minimal)
- area: service/import-related item blocks in `orders/new` flow.
- purpose: show key CNC indicators used for price (counts/lengths/complexity).
- size: small.

3. Price bucket display (minimal)
- area: position row details / service summary area.
- purpose: show `material_cost`, `cnc_service_cost`, `finishing_cost`, `extra_cost`, `net_total`.
- size: medium.

4. Manual-review/validation state display (minimal)
- area: per item row/state badges.
- purpose: make blocked items visible before final save.
- size: small.

Explicitly not redesigned now:
- global navigation layout,
- full service module UX architecture,
- broader dashboard/reporting UI.

## 9. File-Level Change Plan
Parser/import layer:
- [constructor_3dc_quote_import_service.py](C:\PythonProject\TECH_modul\src\services\constructor_3dc_quote_import_service.py)
  - why: source of `technology_summary`.
  - change: small hardening only (if needed), no scope expansion.
  - modify existing.
- [import_router.py](C:\PythonProject\TECH_modul\src\api\import_router.py)
  - why: parse response contract.
  - change: ensure stable pass-through to pricing flow.
  - modify existing.

Pricing/domain/backend:
- [service_models.py](C:\PythonProject\TECH_modul\src\domain\service_models.py)
  - why: currently too legacy/simple for unified pricing item.
  - change: add Phase 1 unified service item dataclasses/serializers.
  - modify existing.
- [quote_pricing_service.py](C:\PythonProject\TECH_modul\src\services\quote_pricing_service.py)
  - why: existing pricing service is generic and insufficient for service-tech model.
  - change: either extend carefully or create dedicated service pricing service and keep this stable.
  - likely create new file + minimal reuse.
- [main_api.py](C:\PythonProject\TECH_modul\src\api\main_api.py)
  - why: order persistence and potential pricing preview endpoints.
  - change: payload validation, optional preview/update endpoints.
  - modify existing.

Config/tariffs:
- [quote_pricing_store_json.py](C:\PythonProject\TECH_modul\src\storage\quote_pricing_store_json.py)
  - why: existing pricing config storage pattern.
  - change: keep separate or add sibling store for service tariffs.
  - prefer create new file for clean scope.
- New file proposed: `src/storage/service_pricing_tariff_store_json.py`
  - why: dedicated tariff groups for service pricing.
  - change: new file.

Frontend:
- [api.ts](C:\PythonProject\TECH_modul\frontend\src\services\api.ts)
  - why: new request/response contracts for pricing preview and normalized item save.
  - change: add/extend types and API methods.
  - modify existing.
- [orders/new/page.tsx](C:\PythonProject\TECH_modul\frontend\src\app\orders\new\page.tsx)
  - why: current hardcoded frontend estimator must call backend-calculated pricing.
  - change: replace/limit local formula, wire validation and bucket rendering.
  - modify existing.
- [services/page.tsx](C:\PythonProject\TECH_modul\frontend\src\app\services\page.tsx)
  - why: wrapper over orders/new route.
  - change: minimal, only if route-level behavior flags needed.
  - likely no or tiny change.

## 10. Recommended Calculation Flow
manual item or imported item
→ normalize into unified service item
→ attach base material and extra layers
→ attach imported CNC summary if present
→ calculate `material_cost`
→ calculate `cnc_service_cost`
→ calculate `finishing_cost`
→ calculate `extra_cost`
→ calculate `net_total`
→ generate technology/pricing summary
→ mark item `ready` or `manual_review`

Operational details:
- if imported CNC exists, CNC bucket uses tariff groups directly from `technology_summary`.
- if item is manual-only, CNC bucket can be zero while other buckets still compute.
- if required inputs are missing for the selected mode, engine must return partial pricing + blocking flags (not silent finalization).

## 11. Validation Rules for Phase 1
Minimum blocking rules:
- `front milling + lacquer` requires:
  - `front_model_code`
  - `base_material_id`
  - `base_thickness_mm`
- missing any of the above => `manual_review` (not ready).

Additional rules:
- low-confidence or incomplete imported data may still be partially priced but must be flagged.
- missing pricing-critical inputs must keep item in `manual_review`.
- unknown CNC operation types must be explicit flags; no hidden assumptions.
- no silent auto-completion of missing critical fields.
- side-based edging rules:
  - if edge mode is `per_side`, each selected side must have material assignment,
  - if edge mode is `default`, one default edge material is mandatory.
- for required modes (`front milling + lacquer`, `veneer`, `bent elements`) base material and thickness are mandatory.

## 12. Test Plan
1. Imported CNC item tests:
- drilling/groove/milling/tool/complexity bucket contribution correctness.

2. Manual service mode tests:
- cut, cut+edge, front+lacquer, veneer, bent base calculations.

3. Mixed imported + manual finishing tests:
- imported CNC + manual lacquer/veneer/layers combination outputs.

4. Front model validation tests:
- block final pricing when required fields missing.

5. Extra layer pricing tests:
- multiple layers with different roles and quantity factors.

6. Edge-side pricing tests:
- default vs per-side edge material assignment.

7. Summary generation tests:
- stable concise human-readable summary text.

8. Edge-case tests:
- estimated milling length,
- unknown CNC operation,
- partial imported data,
- manual-only item with no CNC.

9. API integration tests:
- order payload preserves normalized service pricing structure.

## 13. Rollout Order
1. Freeze Phase 1 unified schema (domain contract).
2. Add tariff config schema and JSON store.
3. Implement pure pricing calculators (unit-test first).
4. Implement validation/manual-review engine.
5. Implement combination layer (imported CNC + manual context).
6. Add summary text generator.
7. Integrate backend API payload flow (orders + optional preview).
8. Replace frontend hardcoded estimator with backend response usage.
9. Add UI-level flags/buckets display (minimal).
10. Run regression tests and manual sample checks.

## 14. Main Risks in Phase 1
1. Risk: frontend and backend pricing divergence during migration.
- mitigation: single backend source of truth; keep frontend formula only as temporary fallback behind guard.

2. Risk: incomplete imported `.project` data leading to wrong certainty.
- mitigation: partial pricing + explicit `manual_review` flags.

3. Risk: tariff schema drift (hardcoded values reappear in UI).
- mitigation: store tariff lookup only in backend config layer; audit API responses.

4. Risk: overloading existing order `spec_json` without clear schema control.
- mitigation: versioned schema key in payload (for example `service_pricing_schema_version`), strict parser/validator.

5. Risk: thickness/material rules not consistently enforced.
- mitigation: centralized validation engine shared by all endpoints.

## 15. Definition of Done
Phase 1 is complete when:
- unified service item schema is implemented and persisted,
- tariffs are loaded from backend config (not UI constants),
- all five pricing buckets are returned per item,
- imported `technology_summary` changes CNC bucket values,
- manual modes are calculated by backend calculators,
- mandatory rules (front model/material/thickness etc.) are enforced,
- manual-review flags are visible in API results and UI state,
- summary text is generated for each item,
- planned test matrix passes.

## 16. What Must Wait for Phase 2
- exact machine-time simulation
- advanced CAM costing
- customer self-service portal
- advanced pricing automation
- deeper production integration
- advanced reporting
- dynamic machine/calendar coupling

## 17. Plain-Language Summary for Owner
In Phase 1 we will make service pricing dependable and consistent.  
The system will use real CNC data from imported `.project` files, combine it with manual service choices, materials, and layers, and return one clear price breakdown per item.  
This will already remove most pricing chaos, while advanced simulation and automation stay for later phases.
