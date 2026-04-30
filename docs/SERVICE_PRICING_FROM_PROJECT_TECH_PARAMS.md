# SERVICE PRICING FROM PROJECT TECH PARAMS

## 1. Goal
This pricing layer must convert real machining data from imported `.project` files into stable, explainable service prices, and combine it with manual business context (finishing, overlays, service mode, commercial options).  
`technology_summary` matters because it replaces guesswork with measurable CNC signals (holes, grooves, path lengths, tools, complexity).

## 2. Scope
In scope:
- pricing logic for CNC operations from `rows[].technology_summary`
- pricing logic for manual service modes (cutting, edgebanding, front milling + lacquer, veneer, bent elements)
- unified item-level pricing model and breakdown buckets
- combination rules for imported CNC + manual finishing/material layers
- tariff structure proposal for future external configuration

Out of scope:
- machine-time simulation and CAM-level cycle optimization
- G-code generation and workstation scheduling
- full UI redesign
- advanced discount engine and AI pricing decisions

## 3. Current Inputs
Pricing must handle two input families.

1. Imported `.project` technology_summary:
- geometry: `length_mm`, `width_mm`, `thickness_mm`, `quantity`, part identity
- drilling: counts, diameter groups, depths
- grooves: count, total groove length, tool widths, depths
- milling: path counts, total/estimated path length, line/arc counts, tool diameters, depths
- tools: unique tool names/diameters and unique tool count
- complexity: operation totals, type counts, `cnc_complexity_score`, boolean operation flags

2. Manual service parameters:
- service mode and subtype selected by user
- commercial details: payment/doc context if needed by business rules
- finishing details: lacquer type/coats, veneer sides, edgebanding sides/type
- material context: base material, extra glued/decorative layers, overlays
- manual overrides for non-imported or incomplete items

## 4. Pricing Principle
Main rule:
- `.project` data is the source of **CNC technology quantities**.
- Manual forms are the source of **commercial and finishing/material context**.

They work together as follows:
- CNC costs are computed from measurable imported technology values.
- Finishing/material/service-layer costs are computed from manual selections.
- Final net price is a transparent sum of pricing buckets.
- If imported CNC data is missing or partial, only available CNC components are priced; missing parts must be explicit (no silent assumptions).

## 5. Target Unified Service Item Model
Each priced service item should support one common structure for both imported and manual flows.

Conceptual layers:
- Base dimensions: length, width, thickness, area, perimeter where needed
- Quantity: item count / multiplier
- Base material: primary board/front/material and base material cost
- Extra materials/layers: overlays, glued layers, decorative layers, side/layer metadata
- Service mode: high-level mode (cutting, cutting+edgebanding, front milling+lacquer, veneer, bent)
- Subtype: concrete commercial/technology variant within mode
- CNC technology summary: imported normalized CNC metrics (or empty for manual-only)
- Finishing parameters: lacquer, veneer, edge type, side selection, coats, etc.
- Price breakdown: bucketed net values
- Technology summary text: short human-readable line for quotation/table/export

Mandatory material/thickness rule:
- For `front milling + lacquer`, `veneer`, and `bent elements`, base material and base thickness are mandatory pricing inputs.
- Thickness classes such as MDF 19 / 22 / 28 must be treated as materially different technology and price cases, not as minor variants.

## 6. Pricing Buckets
Every priced item should expose these buckets.

- `material_cost`: base material and mandatory base consumption (including quantity/area factors)
- `cnc_service_cost`: drilling, grooves, milling, tool-change and complexity-based machining charges
- `finishing_cost`: lacquer, veneer, edge finishing, surface treatment and finishing-specific labor
- `extra_cost`: overlays/layers, special handling, setup surcharges, manual extras
- `net_total`: sum of all buckets before VAT and global discounts

Rule: no hidden pricing outside these buckets.

## 7. Pricing Rules for Imported CNC Parameters
Recommended bases (practical and explainable):

Drilling:
- base: price per hole
- add diameter-group surcharge (small/medium/large diameters)
- optional depth surcharge bands (shallow/standard/deep)
- formula idea: `(holes * base_per_hole) + diameter_band_surcharge + depth_band_surcharge`

Grooves:
- base: price per groove operation + per running meter
- depth/tool-width modifiers by tariff bands
- formula idea: `(groove_count * setup_per_groove) + (groove_total_length_m * price_per_meter) * depth_width_factor`

Milling paths:
- base: price per milling path setup + per path meter
- arc ratio surcharge if arc-heavy geometry
- if only estimated length exists, use estimated tariff path and mark as estimated
- formula idea: `(milling_count * setup_per_path) + (path_length_m * price_per_meter) + arc_surcharge`

Tool usage / tool changes:
- base: price per unique tool group or per additional tool above baseline
- supports wear/setup costs
- formula idea: `max(0, tool_count_unique - baseline_tools) * per_tool_change`

Complexity surcharge:
- map `cnc_complexity_score` to transparent bands (low/medium/high/very high)
- apply multiplier or fixed surcharge to `cnc_service_cost`
- keep band thresholds configurable in tariff table

## 8. Pricing Rules for Manual Service Modes
Cutting:
- primarily by panel area, cut length, and quantity
- optional minimum setup per item/order

Cutting + edgebanding:
- cutting base + edge operations per side/edge type
- include edge material class and thickness/quality multipliers
- side count directly drives cost
- side-level assignment is required with explicit sides: `top`, `bottom`, `left`, `right`
- supported assignment modes:
  - one default edge material for all selected sides
  - per-side edge material (each side can have different edge material/spec)

Front milling + lacquer:
- front model/pattern setup + milling complexity + lacquer layer pricing
- lacquer affected by color system, gloss/matte, number of coats, sanding/prep steps
- mandatory inputs: `front_model_code`, `base_material_id`, `base_thickness_mm`
- if any mandatory field is missing, pricing must remain in manual-review state (no final auto-price)
- MDF 19 / 22 / 28 must map to distinct tariff branches (setup, tooling behavior, lacquer prep factor)

Veneer:
- area-based veneer application (one side/two sides)
- veneer type/class multiplier + glue/prep surcharge
- optional post-veneer finishing surcharge
- base material and base thickness are mandatory inputs
- MDF 19 / 22 / 28 must be priced as separate technology classes where veneer behavior differs

Bent elements:
- geometry complexity class (radius, type) + material thickness class
- setup surcharge + per-unit or per-meter bent processing
- optional post-process finishing bucket contributions
- one base material is required, and one or more additional layers/materials may be added before finishing/drawing preview
- base material + thickness remain mandatory pricing inputs

## 9. How Imported CNC and Manual Finishing Combine
Combination rules:
- Imported CNC defines machining base (`cnc_service_cost`).
- Manual finishing/layers define finishing and extras (`finishing_cost`, `extra_cost`).
- Base material always computed from selected base material and quantity.

Examples:
- Imported front with milling paths + manual lacquer: CNC from imported milling; lacquer from manual finishing.
- Imported board with CNC + manual veneer: CNC from import; veneer as finishing layer (1 or 2 sides).
- Imported item + MDF overlay: base material in `material_cost`, overlay in `extra_cost`, optional extra machining in `cnc_service_cost` if applicable.
- Manual-only item: CNC bucket may be zero; service/finishing/material still priced from manual parameters.

## 10. Front Pattern / Front Model Integration
Front milling should be commercialized by **front model/pattern**, not only tool diameter.

Rules:
- user selects model from catalog/library (pattern defines expected machining profile class)
- model contributes base setup + complexity coefficient
- imported `.project` milling summary refines cost with actual path/arc/tool signals
- lacquer combines with model and base thickness (thicker or complex fronts can carry additional prep coefficient)
- strict validation for `front milling + lacquer` mode:
  - `front_model_code` is required
  - `base_material_id` is required
  - `base_thickness_mm` is required
  - without all three fields, item cannot be finalized for pricing

Coexistence:
- catalog model = commercial definition
- `.project` = technology verification and real machining intensity

## 11. Base Material and Extra Material Layers
Pricing rules:
- Base material:
  - one canonical base layer per item
  - priced by area/volume/class depending on material type
- Extra layers:
  - each layer stored as explicit line using at least:
    - `material_id`
    - `role`
    - `thickness_mm`
    - `coverage_mode`
    - `quantity_factor`
    - `notes`
  - priced independently and added to `extra_cost`
  - optional handling/glue/press surcharge per extra layer or per side

Role examples for `role`:
- `overlay`
- `decorative_layer`
- `reinforcement`
- `glued_mdf`
- `veneer_layer`
- `substrate_addition`

No implicit hidden layer costs.

## 12. Suggested Tariff Structure
Tariffs should be externalized (DB/config), not hardcoded in UI.

Recommended groups:
- drilling tariffs: per-hole base, diameter bands, depth modifiers
- groove tariffs: setup per groove, per-meter rates, depth/width modifiers
- milling tariffs: setup per path, per-meter rates, arc surcharge, estimated-length fallback
- lacquer tariffs: base prep, per m2 by lacquer type/coats/finish class
- veneer tariffs: per m2 by veneer class, side count multiplier, glue/prep surcharge
- bent-element tariffs: setup by geometry class, per unit/per meter processing
- complexity multipliers: score bands and multipliers/surcharges
- material-layer surcharges: overlay/layer handling and bonding surcharges

Each tariff row should support:
- code/name
- unit basis
- base rate
- optional min charge
- optional multiplier bands
- validity dates and active flag

## 13. Summary Text / Technology Description
Each item should expose a short generated summary, readable in tables/quotes.

Format recommendation:
- `MODE | BaseMaterial | CNC: drills/grooves/milling/tools/complexity | Finish: ... | Layers: ...`

Examples:
- `Front milling+lacquer | MDF 19 | CNC: D12 G1 M2(3.4m) T3 C=High | Finish: lacquer RAL 9010, 2 coats`
- `Cut+edgeband | Board 18 | CNC: D0 G0 M0 | Finish: edge ABS 1mm (4 sides)`
- `Veneer | Plywood 18 | CNC: D4 M1(0.8m) | Finish: veneer oak, 2 sides | Layers: +MDF 3mm overlay`

## 14. Edge Cases
Imported item with partial CNC data:
- price only available CNC components
- missing components flagged in item summary

Estimated milling path length:
- use estimated tariff path
- mark item as `estimated_milling=true` in pricing metadata

Unknown operation type:
- route to `extra_cost` as manual review surcharge or unresolved bucket
- never silently drop cost signal

Manual item with no CNC data:
- allowed; CNC bucket can be zero

Multiple extra layers:
- each layer priced independently; summed in `extra_cost`

Lacquer without front model:
- not allowed for final pricing in `front milling + lacquer` mode
- item must stay in manual-review state until `front_model_code`, `base_material_id`, and `base_thickness_mm` are complete

Veneer + edgebanding on same part:
- both finishing components apply; no mutual exclusion

## 15. Recommended Build Order
1. Freeze unified service item schema (input + output buckets + metadata).
2. Add tariff dictionary structure (no UI changes yet).
3. Implement CNC bucket calculation from `technology_summary`.
4. Implement manual mode calculators (cutting, edgebanding, front+lacquer, veneer, bent).
5. Implement combination layer (CNC + finishing + layers + extras).
6. Implement summary text generator.
7. Add validation and edge-case flags (estimated/missing/unknown).
8. Add test matrix (imported-only, manual-only, mixed, edge cases).
9. Integrate into existing service pricing flow behind feature flag/config toggle.

## 16. Acceptance Criteria
Model is ready for implementation when:
- one unified item model can represent imported and manual service items
- all five price buckets are always produced
- imported CNC metrics directly affect `cnc_service_cost`
- manual finishing/layers directly affect `finishing_cost`/`extra_cost`
- mixed scenarios (imported CNC + manual finish) are priced predictably
- summary text is generated and readable for quotation tables
- edge cases are flagged, not hidden
- tariff values are configurable outside UI code

## 17. What Must Wait for Later
- exact machine-time simulation
- advanced CAM-level costing
- machine availability/calendar optimization
- workstation-level planning
- AI-driven price estimation adjustments
- advanced customer discount and negotiation logic

## 18. Plain-Language Summary for Owner
This model will let us price services from real production data instead of guesses.  
Imported `.project` files tell us how much drilling, grooving, milling, and tool complexity a part really has.  
Manual selections (lacquer, veneer, layers, service type) add the business context.  
Together, this gives one clear final price per item with transparent breakdown, so sales, production, and cash planning stay consistent.
