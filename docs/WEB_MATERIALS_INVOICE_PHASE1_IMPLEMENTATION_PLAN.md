# WEB MATERIALS & INVOICE PHASE 1 IMPLEMENTATION PLAN

## 1. Phase 1 Goal
Phase 1 must make the web invoice workflow safe and usable for daily operations without redesigning the whole system.

Business pain to solve now:
- the same invoice can be saved multiple times,
- web invoices have mostly header totals (no reliable line items),
- there is no review/verification gate before writing stock,
- arrivals are not linked to invoice evidence,
- price observations are not written as history,
- stronger existing desktop parsing is not reused in web flow.

## 2. Exact Scope
In scope:
- A. invoice deduplication in web,
- B. web upload/import endpoint reusing existing desktop parsing services,
- C. persistent storage for invoice line items,
- D. minimal invoice review page in web,
- E. write price history on every confirmed price observation,
- F. link arrivals to invoice and invoice line-item records.

Out of scope:
- fuzzy matching,
- alias management UI,
- supplier SKU mapping,
- full supplier master rollout,
- advanced OCR settings UI,
- OpenAI/LLM controls in web UI,
- supplier comparison dashboards,
- advanced warehouse analytics,
- warehouse UI redesign.

Execution rules locked for Phase 1:
1. Do not create any new material record automatically during invoice import.
2. Reuse the existing desktop/shared invoice parsing pipeline through an adapter layer; do not duplicate parser logic into a second implementation.
3. The confirm/export action must be transactional and idempotent:
   - no duplicate arrivals,
   - no duplicate `price_history` entries,
   - no double status transition.
4. `price_history` stores price observations only; it must not silently overwrite canonical material identity.
5. Any low-confidence, unmatched, unit-mismatched, or ambiguous line must stay in manual review state.
6. Keep the existing warehouse UI largely intact in Phase 1; add only the minimal invoice upload/review flow.
7. Manual verification on real sample PDFs is mandatory before Phase 1 is considered done.

## 3. Target Outcome After Phase 1
Target user workflow after Phase 1:
1. User uploads invoice PDF in web.
2. Backend parses it with existing stronger pipeline (`invoice_pdf_import_service` + current OCR/template logic, optional AI fallback as already implemented in shared service).
3. Backend computes dedupe signature/hash and stores invoice header + all parsed line items in SQL tables.
4. If duplicate is detected, API returns duplicate status and existing invoice reference instead of creating a new business document.
5. User opens minimal review screen with parsed line items and statuses.
6. User confirms selected lines manually (safe exact match only) or marks lines for manual later handling.
7. Confirm action creates arrivals linked to invoice and line-item IDs.
8. Each confirmed line writes a price observation into `price_history`.
9. Invoice status changes from `draft/imported` to `reviewed`/`confirmed` (or `partial`).

## 4. Current Starting Point
What already exists:
- Web materials + arrivals management in `frontend/src/app/database/warehouse/page.tsx`.
- Web API for materials, arrivals, simple invoice scan and invoice header save in `src/api/main_api.py` + `src/api/data_manager.py`.
- Strong desktop/shared parsing services exist in `src/services/invoice_pdf_import_service.py`, `src/services/invoice_ai_fallback_service.py`, `src/services/invoice_workflow_service.py`.
- JSON invoice store has dedupe logic (`InvoiceStoreJson.upsert_invoice`) and tests (`src/tests/test_invoice_import.py`).

What is broken for web business flow:
- web scan endpoint (`/db/scan-invoices`) extracts only basic header-like data via simple regex,
- no SQL storage of invoice line items,
- no review gate before stock operations,
- arrivals table has no invoice FK,
- no price-history writes in current web SQL path.

What will be reused:
- parser/OCR/template stack from `invoice_pdf_import_service`,
- normalization helpers and fallback behavior already in shared service,
- dedupe/signature approach from `InvoiceStoreJson` (ported to SQL-backed web path).

Codebase contradiction vs prior audit:
- `price_history` table exists in `src/storage/sqlite_db.py`, but web runtime path in `main_api.py` currently uses `src/api/data_manager.py` schema (`database/tech_modul.db`) where `price_history` is not created. So for web, price history is effectively missing and must be added.

## 5. Required Database Changes
1. Add dedup fields to `invoices` table (web SQL schema in `data_manager.py`)
- Proposed fields: `payload_hash`, `invoice_signature`, `supplier_name_norm`, `invoice_number_norm`, `invoice_date_norm`, `total_gross_norm`, `currency`, `parse_method`, `parse_confidence`, `parse_status`, `duplicate_of_invoice_id`, `source_filename`.
- Why: deterministic dedupe and import traceability.
- Type: additive.
- Migration risk: low.

2. Add `invoice_line_items` table
- Core fields: `id`, `invoice_id` (FK), `line_no`, `raw_line`, `name_raw`, `name_norm`, `quantity`, `unit`, `unit_price_net`, `unit_price_gross`, `total_net`, `total_gross`, `vat_rate`, `material_type`, `thickness_mm`, `parse_source`, `confidence`, `review_status`, `selected_material_id`, timestamps.
- Why: persistent parsed lines + review state.
- Type: additive.
- Migration risk: low.

3. Add FK links in `arrivals`
- Add columns: `invoice_id` (FK to invoices.id), `invoice_line_item_id` (FK to invoice_line_items.id, nullable).
- Why: trace every stock movement to accounting source.
- Type: additive.
- Migration risk: low.

4. Add `price_history` table in web SQL schema (or activate equivalent if already present in this DB)
- Minimal fields for Phase 1: `id`, `material_id`, `supplier`, `invoice_id`, `invoice_line_item_id`, `purchase_date`, `unit`, `net_price`, `gross_price`, `currency`, `notes`, `created_at`.
- Why: do not overwrite material identity; keep time-series observations.
- Type: additive.
- Migration risk: medium (new write path, integrity rules).

5. Add indexes/constraints
- Unique index suggestions: `(payload_hash)`, and conservative composite dedupe index on normalized signature fields (nullable-safe).
- Indexes for `invoice_line_items(invoice_id)`, `arrivals(invoice_id)`, `price_history(material_id, purchase_date)`.
- Why: dedupe speed + relational queries.
- Type: additive.
- Migration risk: low.

## 6. Required Backend/API Changes
1. `POST /api/db/invoices/import`
- Purpose: upload PDF and parse using existing strong parser.
- Request: multipart form (`file` + optional metadata).
- Response (high-level): `invoice`, `line_items`, `is_duplicate`, `duplicate_invoice_id`, `needs_review`.
- Reuse: call `parse_invoice_pdf_bytes` and related helpers from existing services.
- Risk: medium (integration of desktop parser into web SQL persistence).

2. `GET /api/db/invoices` and `GET /api/db/invoices/{id}` (extend)
- Purpose: list invoices with parse/review/dedupe status.
- Response: header info + summary counts (`line_items_total`, `line_items_reviewed`, `arrivals_created`).
- Reuse: existing `/db/invoices` shape can be expanded or versioned.
- Risk: low.

3. `GET /api/db/invoices/{id}/line-items`
- Purpose: retrieve parsed lines for review UI.
- Response: list with parser fields + review flags.
- Reuse: new SQL read model, parser output format already available.
- Risk: low.

4. `PATCH /api/db/invoices/{id}/line-items/{line_id}`
- Purpose: manual review decisions (confirm, skip, set material, adjust qty/unit/price if needed).
- Request: minimal editable fields + review status.
- Response: updated line.
- Reuse: existing arrival edit patterns as style reference.
- Risk: medium (validation).

5. `POST /api/db/invoices/{id}/confirm`
- Purpose: transactional confirm/export of selected lines.
- Behavior: create arrivals with invoice links, write price history per confirmed line, update invoice status.
- Response: summary (`arrivals_created`, `price_history_written`, `skipped_lines`).
- Reuse: existing `add_arrival` logic + parser-normalized units.
- Risk: high (must be atomic and idempotent).

6. Deduplicated invoice save behavior
- Purpose: prevent duplicate business records.
- Behavior: on import, compare payload hash first, then strict signature fallback (similar to `InvoiceStoreJson._is_same_invoice_signature`).
- Response: explicit duplicate status (no silent overwrite).
- Reuse: port logic from `InvoiceStoreJson` to SQL layer in `data_manager.py`.
- Risk: medium.

## 7. Required Frontend/Web Changes
1. New upload/review area in web database section
- Route/page/component: recommended new route `frontend/src/app/database/invoices/page.tsx`.
- Purpose: upload invoice PDF + open review list.
- Size: medium.

2. Minimal invoice review UI
- Route/page/component: same page (or `.../invoices/[id]/page.tsx` for detail).
- Purpose: show parsed line items, line status, manual confirm/skip/material selection.
- Size: large.

3. Confirm/export action UI
- Route/page/component: review page action bar.
- Purpose: confirm selected lines -> create arrivals + price history writes.
- Size: medium.

4. Reuse from existing UI
- Reuse warehouse patterns: table filters, sticky headers, inline controls from `database/warehouse/page.tsx`.
- Do not redesign existing warehouse left panel/column customization in this phase.
- Size: small (reuse decision), large (if violated).

5. Minimal visibility in existing pages
- Route/component: add simple navigation entry/link from `/database` hub to new invoices page.
- Purpose: discoverability.
- Size: small.

## 8. File-Level Change Plan
Backend/API:
- `src/api/main_api.py`
  - Why: register new invoice import/review/confirm endpoints.
  - Change: modify existing file (add routes + request models).
- `src/api/data_manager.py`
  - Why: web SQL schema + CRUD + dedupe + transactional confirm logic.
  - Change: modify existing file (table migrations + methods).
- `src/services/invoice_pdf_import_service.py`
  - Why: parser reused directly.
  - Change: modify only if adapter helpers needed; otherwise reuse as-is.
- `src/services/invoice_workflow_service.py`
  - Why: source of reusable dedupe/signature and payload-building ideas.
  - Change: likely no direct modification in Phase 1; reuse functions/patterns.
- `src/services/material_transactions.py` (optional)
  - Why: if needed to keep stock movement consistency.
  - Change: small integration or none.

Database/storage:
- `database/tech_modul.db` (runtime)
  - Why: new SQL tables/columns.
  - Change: additive migrations via `data_manager.init_db()`.
- `src/storage/sqlite_db.py`
  - Why: currently has `price_history` but not necessarily web runtime DB.
  - Change: no mandatory change for Phase 1 web path; document divergence.

Frontend:
- `frontend/src/services/api.ts`
  - Why: add methods for import, line-items, review patch, confirm.
  - Change: modify existing file.
- `frontend/src/app/database/page.tsx`
  - Why: link to invoice review module.
  - Change: small modify.
- `frontend/src/app/database/invoices/page.tsx` (new)
  - Why: upload + invoice list + minimal review state.
  - Change: create new file.
- `frontend/src/app/database/invoices/[id]/page.tsx` (optional new)
  - Why: focused line-item review view.
  - Change: create new file (if split view preferred).

## 9. Recommended Data Flow
Phase 1 intended flow:
1. Upload PDF in web.
2. Backend parses with existing stronger parser (`invoice_pdf_import_service`).
3. Backend normalizes invoice header + computes dedupe hash/signature.
4. Backend stores invoice header (`invoices`) and line items (`invoice_line_items`) with status `imported`.
5. Web review UI loads invoice and lines.
6. User manually marks each line: confirm with material, or skip/defer.
7. User clicks confirm export.
8. Backend transaction:
   - validate selected lines,
   - create `arrivals` rows with `invoice_id` + `invoice_line_item_id`,
   - write `price_history` observation per confirmed line,
   - update line statuses and invoice status (`confirmed`/`partial`).
9. UI shows summary and linked arrivals created.

## 10. Minimal Matching Strategy for Phase 1
Allowed matching in Phase 1:
- exact match by internal material ID selected by user,
- optional exact match by normalized name + same unit only when confidence is explicit and user confirms.

Must always go to manual review:
- missing exact material match,
- unit mismatch,
- ambiguous material candidates,
- parsed lines with low confidence/unknown unit.

Avoid silent duplicate material creation:
- no auto-create material records during import,
- if no safe match: line remains `unmatched` and cannot create arrival until user selects material manually.

When no safe match exists:
- keep line persisted,
- set review status `needs_manual_mapping`,
- allow user to continue partial confirm for other lines.

## 11. Test Plan
Backend tests:
- import endpoint stores header + lines,
- dedupe by payload hash,
- dedupe by strict signature fallback,
- duplicate import returns reference, not extra invoice.

Migration/schema tests:
- `invoice_line_items`, new `arrivals` FK columns, and `price_history` creation in web SQL DB,
- migration on existing DB with data (non-breaking).

Line-item persistence tests:
- parsed rows saved with expected normalized fields,
- review status transitions.

Arrival linkage tests:
- confirmed lines create arrivals linked to invoice and line item,
- no confirm without valid material mapping.

Price-history write tests:
- every confirmed line creates one history observation,
- values match confirmed unit/price/date/supplier.

Frontend smoke tests:
- upload -> invoice appears,
- line-item review visible,
- confirm triggers summary and status refresh,
- duplicate upload message shown correctly.

## 12. Rollout Order
1. Add additive DB migrations in `data_manager` (new columns/tables/indexes).
2. Add low-level persistence methods in `data_manager` for invoices + line items + linked arrivals + price history.
3. Implement import endpoint reusing strong parser services.
4. Implement read endpoints for invoice list/detail/line-items.
5. Implement review update endpoint for line-item status/material selection.
6. Implement confirm/export endpoint with transaction + idempotency safeguards.
7. Add frontend API methods.
8. Build minimal web invoice page (upload + list + review + confirm).
9. Add link from database hub to invoice page.
10. Add tests (backend + migrations + frontend smoke) and run manual verification on real sample PDFs.

## 13. Main Risks in Phase 1
1. Desktop/web integration mismatch
- Why: parser currently used mainly by JSON workflow, web uses SQL path.
- Mitigation: isolate parser adapter layer and keep parser unchanged.

2. Migration on existing DB
- Why: adding constraints/columns on production-like file DB may fail on inconsistent state.
- Mitigation: additive `ALTER TABLE` guards + startup migration logging + backup before deploy.

3. False dedupe or missed dedupe
- Why: invoice signature can be imperfect with OCR errors.
- Mitigation: two-stage dedupe (hash first, strict signature second), return explicit duplicate reason for user review.

4. Wrong arrivals from incorrect review mapping
- Why: confirm action writes stock.
- Mitigation: require explicit material_id for each confirmed line; transaction with validation.

5. Price-history quality issues
- Why: net/gross ambiguity and unit inconsistencies.
- Mitigation: persist both net and gross where available; store unit and source refs; never overwrite material master price silently.

6. Parser inconsistency across suppliers
- Why: OCR/template variance.
- Mitigation: keep `needs_review` default for uncertain lines; no auto-stock for low confidence.

## 14. Definition of Done
Phase 1 is done only if all below are true:
- web can upload invoice PDF and parse line items using existing stronger parser stack,
- duplicate invoices are blocked/flagged deterministically,
- invoice line items are stored persistently in SQL,
- web has a minimal review UI where user can confirm/skip lines,
- confirm action creates arrivals linked to invoice and line-item IDs,
- confirm action writes `price_history` observations for confirmed lines,
- no automatic material creation on uncertain lines,
- tests for dedupe, persistence, linkage, and price-history writes pass.

## 15. What Must Wait for Phase 2
Deferred intentionally:
- aliases and alias UI,
- supplier master rollout,
- supplier SKU mapping,
- fuzzy matching,
- advanced OCR/AI runtime controls in web,
- supplier comparison analytics,
- advanced warehouse analytics and broader UX redesign.

## 16. Plain-Language Summary for Owner
Phase 1 will make faktury in web practical and safer:
- one faktura will not be saved many times,
- each faktura will have real parsed line items,
- before anything goes to stock, a person confirms what is correct,
- every confirmed stock entry will be linked to faktura evidence,
- every confirmed price will be saved in price history.

What Phase 1 will not solve yet:
- smart fuzzy auto-matching,
- full alias/supplier code automation,
- advanced supplier analytics.

Why this is the right first step:
- it removes the highest business risk now (wrong or duplicated invoice data in stock and prices),
- it reuses the stronger parser you already have,
- it gives controlled manual verification instead of unsafe automation.
