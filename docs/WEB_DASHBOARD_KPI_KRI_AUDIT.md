# WEB DASHBOARD KPI KRI AUDIT

## 1. Executive Summary
A practical Dashboard V1 can already be built from real web/backend data, mainly around: order/project throughput, service-pricing quality flags, production/task load, kiosk/time activity, low-stock risk, and invoice-review pipeline health. The strongest real sources are operations, invoice line review/export, materials low-stock, production status, kiosk actions, and service-pricing manual-review flags. The weakest area is global finance/dashboard polish, where some aggregates are still partial or placeholder-driven.

## 2. Scope of This Audit
Included:
- Current web frontend pages/components that already show summary/overview/status patterns.
- Current backend/API endpoints and persisted data that can feed KPI/KRI.
- Practical metrics derivable from current data model and flow behavior.

Excluded:
- Future/Phase-2 concepts not implemented in code.
- Full desktop feature parity planning.
- UI redesign work.
- Invented executive metrics without real data lineage.

## 3. Existing Web Overview / Dashboard-Like Screens
1. Route: `/dashboard` | File: `C:\PythonProject\TECH_modul\frontend\src\app\dashboard\page.tsx`
- Shows: central hub, project count, materials count, AI advice, readiness summary context.
- Data quality: PARTIAL (real API calls exist, but this page is still more hub/navigation than operational KPI board).

2. Route: `/workspace` | File: `C:\PythonProject\TECH_modul\frontend\src\app\workspace\page.tsx`
- Shows: project workspace summary, wall summary, MVP readiness, warning blocks.
- Data quality: REAL/PARTIAL (real backend-driven project summaries; readiness is checklist-style signal, not full operational KPI model).

3. Route: `/operations` | File: `C:\PythonProject\TECH_modul\frontend\src\app\operations\page.tsx`
- Shows: operation issues summary, overdue/critical counts, route recommendations, issue actions.
- Data quality: REAL (uses backend summary/issues/recommendation endpoints).

4. Route: `/cri` | File: `C:\PythonProject\TECH_modul\frontend\src\app\cri\page.tsx`
- Shows: issue/risk candidate listing and value-oriented aggregates from issues.
- Data quality: PARTIAL (real issue data, but derived value display is frontend-calculated and depends on issue completeness).

5. Route: `/production` | File: `C:\PythonProject\TECH_modul\frontend\src\app\production\page.tsx`
- Shows: workstation load/progress, production stats, activity timeline; 10s refresh.
- Data quality: REAL/PARTIAL (real endpoint and formula, quality depends on task/state attribution completeness).

6. Route: `/time-tracking` and `/time-tracking/scan` | Files:
- `C:\PythonProject\TECH_modul\frontend\src\app\time-tracking\page.tsx`
- `C:\PythonProject\TECH_modul\frontend\src\app\time-tracking\scan\page.tsx`
- Shows: timesheets, kiosk worker scan/actions, optional project/order/workstation linkage.
- Data quality: REAL/PARTIAL (real persistence and actions; optional linkage fields reduce completeness for some KPI).

7. Route: `/database/warehouse` | File: `C:\PythonProject\TECH_modul\frontend\src\app\database\warehouse\page.tsx`
- Shows: materials table, low-stock alerts, arrivals context.
- Data quality: REAL.

8. Route: `/database/invoices` | File: `C:\PythonProject\TECH_modul\frontend\src\app\database\invoices\page.tsx`
- Shows: import/review/linked deliveries/price-history tabs, line-item review states, confidence, confirm/export.
- Data quality: REAL (with explicit Phase-1 limitations for source checks).

9. Route: `/cashboxes` | File: `C:\PythonProject\TECH_modul\frontend\src\app\cashboxes\page.tsx`
- Shows: four cash boxes + cash movement table.
- Data quality: PARTIAL (mixes backend orders with local draft payments from `localStorage`).

10. Route: `/finance` and `/finance/global` | Files:
- `C:\PythonProject\TECH_modul\frontend\src\app\finance\page.tsx`
- `C:\PythonProject\TECH_modul\frontend\src\app\finance\global\page.tsx`
- Shows: project/global finance summaries.
- Data quality: PARTIAL (real endpoint exists, but backend global production block includes placeholders; some cash logic marked placeholder).

11. Route: `/database` | File: `C:\PythonProject\TECH_modul\frontend\src\app\database\page.tsx`
- Shows: database hub cards with static-looking counters.
- Data quality: PARTIAL/MOCKED for KPI purposes (not reliable source of truth dashboard metrics).

## 4. Available Data Domains for Dashboarding
1. Orders/projects
- Sources: projects/orders endpoints, workspace summary, MVP readiness, project-level summaries.
- Availability: READY/PARTIAL (core counts/statuses are real; some business-state depth still uneven by module).

2. Service pricing
- Sources: backend service pricing payload (`servicePricing`, `serviceEstimatedNet`, `serviceSummary`, schema version), validation flags/manual review reasons.
- Availability: READY for quality/risk metrics.

3. Imported CNC/project rows
- Sources: `.project` import enriched `technology_summary` (drilling/groove/milling/tool/complexity and unknown-op signal).
- Availability: READY/PARTIAL (usable now; confidence depends on import coverage by item type).

4. Production/tasks/handoff
- Sources: operations store, production status endpoint, operation issues/recommendations.
- Availability: READY/PARTIAL (real data flow; attribution/state discipline affects KPI stability).

5. Time tracking / kiosk
- Sources: work_time endpoints, kiosk scan/action endpoints.
- Availability: READY/PARTIAL (events are real; optional project/order/workstation fields can reduce attribution quality).

6. Warehouse/materials/low stock
- Sources: materials, low-stock endpoint, arrivals.
- Availability: READY.

7. Invoices / review states
- Sources: invoices, invoice_line_items, confirm/export pipeline, dedup, arrivals linkage, price_history write-on-confirm.
- Availability: READY.

8. Validation/manual_review states
- Sources: service-pricing validation and invoice line review logic.
- Availability: READY.

9. Finance-like totals
- Sources: project/global finance summaries, cashboxes page.
- Availability: PARTIAL (global endpoint has placeholder segments; cashboxes include local draft rows).

## 5. KPI That Can Be Calculated Right Now
### Sales / Orders
1. KPI: Active projects count
- Business meaning: current workload volume.
- Data sources: `/system/summary`, project lists.
- Confidence: READY.

2. KPI: Orders by status (draft/in progress/completed where stored)
- Business meaning: throughput stage distribution.
- Data sources: orders in backend (`data_manager` + orders endpoints).
- Confidence: PARTIAL (depends on consistent status usage across flows).

3. KPI: MVP readiness distribution (project data-completeness readiness)
- Business meaning: how many projects are execution-ready.
- Data sources: `/projects/mvp-readiness-summary`.
- Confidence: READY (as readiness KPI, not revenue KPI).

### Pricing / Quotation
4. KPI: Service items `ready` vs `manual_review`
- Business meaning: pricing process quality and blocking load.
- Data sources: service pricing payload fields persisted in order/service rows.
- Confidence: READY.

5. KPI: Average estimated net per service item
- Business meaning: commercial value per service workload unit.
- Data sources: `serviceEstimatedNet` from backend pricing snapshots.
- Confidence: READY/PARTIAL (depends on adoption of unified rows across all entries).

6. KPI: Count of missing mandatory pricing inputs
- Business meaning: data capture discipline.
- Data sources: validation flags and `manual_review_reasons`.
- Confidence: READY.

### Production
7. KPI: Workstation load split (idle/in_progress/done task mix)
- Business meaning: bottlenecks and balancing.
- Data sources: `/api/production/status`.
- Confidence: READY/PARTIAL (real formula, quality depends on route/task updates).

8. KPI: Open critical issues and overdue issues
- Business meaning: operational risk pressure.
- Data sources: `/api/operations/summary`, `/api/operations/issues`.
- Confidence: READY.

9. KPI: Route recommendation queue size / estimated unlock value
- Business meaning: immediate optimization opportunities.
- Data sources: operations recommend endpoint.
- Confidence: PARTIAL (depends on recommendation data quality and usage).

### Labor / Time
10. KPI: Logged hours total (period-based)
- Business meaning: labor effort consumption.
- Data sources: `/api/work_time` sheets.
- Confidence: READY.

11. KPI: Active kiosk sessions count
- Business meaning: real-time workforce activity.
- Data sources: kiosk state/worker lists.
- Confidence: READY/PARTIAL (attribution fields optional).

### Materials / Invoices
12. KPI: Low-stock items count
- Business meaning: replenishment urgency.
- Data sources: `/api/db/materials/low-stock`.
- Confidence: READY.

13. KPI: Invoice import dedup rate
- Business meaning: import hygiene and duplicate prevention efficiency.
- Data sources: invoice dedup by payload hash/signature.
- Confidence: READY.

14. KPI: Invoice line review throughput (reviewed/confirmed/exported ratio)
- Business meaning: AP processing flow performance.
- Data sources: invoice line items + invoice statuses.
- Confidence: READY.

15. KPI: Price-history observations written from invoice confirm
- Business meaning: purchasing intelligence growth.
- Data sources: `price_history_written` in confirm flow and `price_history` table.
- Confidence: READY.

## 6. KRI / Risk Indicators That Can Be Calculated Right Now
1. KRI: Service pricing items in `manual_review`
- Risk meaning: non-finalizable offers and pricing uncertainty.
- Data sources: service pricing status/flags/reasons.
- Confidence: READY.

2. KRI: Unknown CNC operations in imported items
- Risk meaning: underpriced/incorrectly priced machining.
- Data sources: `technology_summary.unknown_operation_count` + validation output.
- Confidence: READY.

3. KRI: Missing mandatory front-milling inputs
- Risk meaning: invalid front pricing (model/material/thickness missing).
- Data sources: service pricing validation reasons.
- Confidence: READY.

4. KRI: Incomplete edge-side configuration for cut+edgebanding
- Risk meaning: finishing cost leakage and wrong quotation.
- Data sources: edge-side validation flags.
- Confidence: READY.

5. KRI: Low-stock materials below minimum
- Risk meaning: production interruption or emergency purchasing.
- Data sources: low-stock endpoint.
- Confidence: READY.

6. KRI: Invoice lines unresolved (missing selected material/unit/low confidence)
- Risk meaning: wrong arrivals/price history and accounting delays.
- Data sources: invoice line statuses, confidence, selected_material_id, review rules.
- Confidence: READY.

7. KRI: Invoice source monitoring blind spots (Telegram/WhatsApp)
- Risk meaning: delayed capture of supplier invoices.
- Data sources: check-sources warnings (`not implemented yet`).
- Confidence: READY (as a system capability risk signal).

8. KRI: Active kiosk sessions lacking project/order/workstation linkage
- Risk meaning: labor cost attribution gaps.
- Data sources: kiosk action payload fields.
- Confidence: PARTIAL (fields are optional; requires additional aggregate endpoint/query).

9. KRI: Overdue/critical operations issues
- Risk meaning: delivery and production execution risk.
- Data sources: operations summary/issues.
- Confidence: READY.

10. KRI: Cash movement dependence on drafts (not only persisted records)
- Risk meaning: financial dashboard mismatch vs accounting truth.
- Data sources: cashboxes page local draft merge.
- Confidence: READY (risk exists in current logic).

## 7. Metrics That Look Possible But Are Not Yet Reliable
1. "True company cash in hand" as a final executive KPI
- Why unreliable: global finance uses placeholder approach for cash integration; cashboxes include local drafts.

2. "End-to-end production efficiency" as one number
- Why unreliable: production progress is real but depends on completeness/discipline of route and task-state updates.

3. "Full profitability by project" as trusted board KPI
- Why unreliable: finance/global blocks are partial, and cost capture consistency is not fully unified across all flows.

4. "Labor productivity per order" as final KPI
- Why unreliable: kiosk linkage fields can be optional, so attribution can be incomplete.

5. "Invoice source coverage KPI (email + telegram + whatsapp)"
- Why unreliable: Telegram/WhatsApp source checks are explicitly not implemented in current Phase-1 endpoint.

6. "Universal dashboard from `/database` hub counters"
- Why unreliable: hub contains static/showcase counters not guaranteed backend-truth.

## 8. Current Data Quality / Consistency Gaps
1. Mixed real + draft financial movement paths (cashboxes) can skew totals.
2. Global finance endpoint contains explicit placeholder/zero sections (production block).
3. Optional kiosk linkage (`project_code`, `order_id`, `workstation`) weakens labor attribution quality.
4. Some summary UIs derive values frontend-side from partial payloads, not dedicated backend aggregates.
5. Capability gaps in source ingestion checks (Telegram/WhatsApp not implemented for invoice check endpoint).
6. Readiness and status semantics differ by module (useful, but not yet harmonized for one executive board).
7. Some hub-level pages remain navigation-heavy with partial/static status visuals.

## 9. Best Candidate Dashboard V1
Most realistic V1 should be an operational dashboard (not executive vanity board) with 6 blocks:
1. Order/Pipeline Health
- Active projects, orders by state, MVP readiness distribution.

2. Pricing Quality
- Service items: ready vs manual_review, top validation blockers.

3. Production Risk
- Workstation load snapshot, overdue issues, critical issues, top recommended route actions.

4. Time/Kiosk Activity
- Active sessions, last actions, unattributed session count (missing project/order/workstation).

5. Materials & Procurement
- Low-stock count + top critical items, arrivals in period.

6. Invoice Processing Control
- Imported invoices, duplicates prevented, unresolved line items, confirmed/exported lines, price-history writes.

Safe to show now:
- Counts, statuses, queues, warnings from already-real endpoints.

Should be excluded for now:
- "final" profitability/cashboard totals presented as accounting truth.

Should be warning-style (not polished KPI):
- unknown CNC ops, manual_review backlog, incomplete attribution, source-check gaps.

## 10. Recommended KPI/KRI Groups for Phase 1
Small practical set:
1. KPI group: Pipeline
- Active projects, orders by state, readiness %.

2. KPI group: Pricing integrity
- Ready vs manual_review items, missing-required-input count.

3. KPI group: Production execution
- Critical issues, overdue issues, in-progress stations.

4. KPI group: Procurement/inventory
- Low-stock count, arrivals count, unresolved invoice lines.

5. KRI group: Data/risk warnings
- Unknown CNC operations, unlinked kiosk actions, source-check limitations, draft-dependent cash entries.

## 11. Required Backend/API Additions for a Good Dashboard V1
Minimal, realistic additions:
1. Add one consolidated operational-summary endpoint (read-only aggregator)
- Why: reduces frontend joins and inconsistent calculations.

2. Add aggregate for service pricing quality
- Counts by `status`, by `manual_review_reason`, by service mode.

3. Add aggregate for invoice review pipeline
- unresolved/confirmed/exported counts, low-confidence counts, missing-material counts.

4. Add aggregate for kiosk attribution quality
- active sessions missing project/order/workstation linkage.

5. Add explicit reliability flags in finance/global summary response
- e.g., fields marked `placeholder` or `derived_from_drafts` to avoid false trust.

## 12. Required Frontend Changes for Dashboard V1
Minimal UI work (no global redesign):
1. Build one dedicated dashboard page sectioned into the 6 operational blocks.
2. Consume backend aggregate endpoints instead of local ad-hoc merges where possible.
3. Render KPI vs KRI visually distinct (KRI as warnings/alerts).
4. Add confidence badges per widget (`READY`, `PARTIAL`) for transparency.
5. Link each widget to its operational source screen (operations, invoices, warehouse, pricing, kiosk).

## 13. Main Risks / Technical Debt
1. Risk: KPI trust erosion from mixed-quality metrics.
- Why it matters: users stop trusting dashboard quickly.
- Mitigation: label confidence and show only ready metrics as primary KPIs.

2. Risk: frontend-calculated aggregates diverge from backend truth.
- Why it matters: inconsistent numbers across pages.
- Mitigation: move dashboard aggregates to backend endpoints.

3. Risk: financial misinterpretation.
- Why it matters: wrong business decisions.
- Mitigation: keep finance block "operational preview" until placeholder fields are replaced.

4. Risk: attribution gaps in labor/production.
- Why it matters: poor accountability and distorted labor metrics.
- Mitigation: add explicit unattributed-session KRI and tighten required fields later.

5. Risk: hidden import/review bottlenecks.
- Why it matters: delays in procurement and stock updates.
- Mitigation: dashboard unresolved invoice lines + manual_review backlog as top alerts.

## 14. Recommended Next Step
Build a Dashboard V1 plan immediately, but only with metrics marked READY or clearly labeled PARTIAL.
Parallel quick win before implementation: add 3-5 small aggregate backend endpoints (service pricing quality, invoice review pipeline, kiosk attribution quality, unified operational summary) to remove frontend ambiguity.

## 15. Plain-Language Summary for Owner
We can already build a useful dashboard now, but it should focus on real operations: project flow, pricing quality, production issues, low stock, and invoice review status. Those numbers are mostly trustworthy today. Some "big finance" numbers are still risky because part of that data is placeholder or mixed with drafts. The best first step is to launch a practical operations dashboard with clear warnings, then tighten missing data links so later financial/executive metrics become fully reliable.
