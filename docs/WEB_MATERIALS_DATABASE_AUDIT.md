# WEB MATERIALS DATABASE AUDIT

**Date:** 2026-04-22  
**Codebase:** C:\PythonProject\TECH_modul  
**Auditor:** Claude Sonnet 4.6 (automated codebase inspection)

---

## 1. Executive Summary

The web version has a functional, well-built material warehouse UI and a working purchase-arrival system. The desktop has a complete, production-tested invoice import pipeline with real OCR, AI fallback, supplier templates, and a rich JSON-based invoice store.

These two systems **do not talk to each other.** The web's invoice scanning uses a separate, minimal regex parser that was self-labeled in the source code as `Prosty "AI" parser (RegEx)` and stores only header-level totals. The desktop's full parsed invoice data (line items, OCR text, supplier codes, confidence scores) lives in `data/invoices.json` and is invisible to the web.

The material database itself is solid for manual use but is missing: supplier codes, aliases, a price history table that is actually written to, and any connection between imported invoice line items and normalized material records. The `price_history` SQLite table and `supplier_item_links` table exist in the schema but are never read or written by any code.

---

## 2. Scope of This Audit

**Included:**
- Material database / catalog — SQLite schema, API endpoints, web UI
- Supplier / wholesaler fields in material records
- Invoice import — web scanner, desktop pipeline, all parsing steps
- Invoice line-item extraction and storage
- Mapping of invoice items to material records
- Price history and purchase history
- Alias, supplier code, and matching logic
- AI / OCR / PDF parsing

**Intentionally excluded:**
- Project estimation / wycena (covered in WEB_SERVICES_ESTIMATION_AUDIT.md)
- Production module, kiosk, RCP
- Finance tax summaries beyond where they touch invoices
- Client and order databases

---

## 3. Relevant Web Structure

### Pages

| Route | File | Purpose |
|---|---|---|
| `/database/warehouse` | `frontend/src/app/database/warehouse/page.tsx` | Main material warehouse — full desktop-style table, arrival form, low-stock alerts, inline editing |
| `/database` | `frontend/src/app/database/page.tsx` | Database hub — links to all DB sub-pages |
| `/database/clients` | `frontend/src/app/database/clients/page.tsx` | Client records |
| `/database/shopping` | `frontend/src/app/database/shopping/page.tsx` | Shopping list (low-stock items — "mark as bought" is a local-only mock) |
| `/database/library` | `frontend/src/app/database/library/page.tsx` | Material library |
| `/finance/global` | `frontend/src/app/finance/global/page.tsx` | Finance dashboard — includes invoice scan results and tax summary |

**No dedicated invoice import page exists in the web.** Invoice scanning is embedded in the finance dashboard.

### Key Components

| Component / File | Purpose |
|---|---|
| `warehouse/page.tsx` | Full material list, arrival form, per-group tabs, inline edit, column picker, drag-reorder |
| `frontend/src/services/api.ts` | `TechModulAPI` — `getMaterials`, `createMaterial`, `updateMaterial`, `getArrivals`, `createArrival`, `updateArrival`, `scanInvoices`, `getInvoices`, `createInvoice`, `getLowStockMaterials` |

### API endpoints used by web

| Endpoint | Method | Web uses it |
|---|---|---|
| `/db/materials` | GET | Yes — loads full material list |
| `/db/materials` | POST | Yes — creates new material record |
| `/db/materials/{id}` | PATCH | Yes — edits existing material |
| `/api/db/materials/low-stock` | GET | Yes — drives low-stock alerts |
| `/api/db/arrivals` | GET | Yes — full arrival/purchase history |
| `/api/db/arrivals` | POST | Yes — records new delivery |
| `/api/db/arrivals/{id}` | PATCH | Yes — updates existing arrival |
| `/db/scan-invoices` | GET | Yes — scans PDFs with regex parser |
| `/db/invoices` | GET | Yes — reads saved invoice headers |
| `/db/invoices` | POST | Yes — saves selected invoice header |
| `/db/tax-summary` | GET | Yes — VAT summary |

---

## 4. Desktop Reference Structure

Used only as comparison. The desktop has a much more complete invoice and material pipeline.

| File | Role |
|---|---|
| `src/services/invoice_pdf_import_service.py` | Main PDF parsing: pypdf text extraction, Tesseract OCR, supplier template matching, line-item parsing, multi-invoice splitting |
| `src/services/invoice_ai_fallback_service.py` | OpenAI GPT-4o-mini fallback for invoice parsing (disabled by default) |
| `src/services/invoice_workflow_service.py` | Orchestrates the full import pipeline: source → parse → store → export to material → Telegram notify |
| `src/storage/invoice_store_json.py` | `InvoiceStoreJson` — rich JSON store for full parsed invoice data (`data/invoices.json`) |
| `src/storage/material_store_json.py` | `MaterialStoreJson` — desktop material JSON store (`data/baza_materialu.json`) |
| `src/storage/supplier_price_store_json.py` | `SupplierPriceStoreJson` — supplier price comparison store (orphaned — no API or UI) |
| `src/storage/sqlite_db.py` | Defines SQLite schema including `price_history` and `supplier_item_links` tables |
| `src/services/material_advanced_service.py` | `compare_prices()` — reads price history from JSON baza_materialu (exact name match only) |
| `src/widgets/invoice_import_dialog.py` | Desktop Qt dialog — shows parsed line items with discount control and price comparison |
| `data/invoices.json` | Live rich invoice data store (desktop) |
| `data/baza_materialu.json` | Desktop material records (separate from SQLite) |
| `data/supplier_prices.json` | Supplier price comparison data (orphaned) |

---

## 5. Current Material Record Structure

### SQLite `materials` table — the source of truth for web

```sql
id               INTEGER PRIMARY KEY AUTOINCREMENT
name             TEXT UNIQUE NOT NULL        -- material name (only unique key — no alias, no code)
price_per_m2     REAL                        -- base price per unit (exposed as "price" in API)
thickness        INTEGER                     -- mm
material_code    TEXT DEFAULT ''             -- free-text code, no lookup table
category         TEXT DEFAULT 'boards'       -- boards | hardware | finishes | other
material_kind    TEXT DEFAULT 'other'        -- hdf | mdf | plyta | okleina | lakier | okucie | inne
unit             TEXT DEFAULT 'm2'           -- m2 | szt | mb
is_library       BOOLEAN DEFAULT 1
stock_quantity   REAL DEFAULT 0.0
min_stock        REAL DEFAULT 0.0
purchase_type    TEXT DEFAULT 'nothing'      -- invoice | cash | nothing
supplier         TEXT DEFAULT ''             -- free text, no FK to supplier table
wholesaler       TEXT DEFAULT ''             -- free text, no FK
format_length_mm REAL DEFAULT 0.0
format_width_mm  REAL DEFAULT 0.0
pack_size        REAL DEFAULT 0.0
parameter_json   TEXT DEFAULT '{}'           -- arbitrary extra params as JSON blob
texture_url      TEXT DEFAULT ''
color_hex        TEXT DEFAULT '#ffffff'
```

### SQLite `arrivals` table — purchase/delivery history per material

```sql
id               INTEGER PRIMARY KEY AUTOINCREMENT
material_id      INTEGER  -- FK → materials.id
order_id         INTEGER  -- FK → orders.id, nullable
quantity         REAL DEFAULT 0
unit             TEXT DEFAULT 'm2'
purchase_type    TEXT DEFAULT 'nothing'
document_nr      TEXT                        -- invoice number, free text
supplier         TEXT DEFAULT ''             -- free text
wholesaler       TEXT DEFAULT ''
unit_price_net   REAL DEFAULT 0.0
unit_price_gross REAL DEFAULT 0.0
price_total      REAL DEFAULT 0
date             TEXT                        -- ISO date string
created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

### SQLite `invoices` table — minimal invoice header (used by web)

```sql
id           INTEGER PRIMARY KEY AUTOINCREMENT
invoice_nr   TEXT
date         TEXT
nip          TEXT                            -- supplier tax ID
net_amount   REAL DEFAULT 0
vat_amount   REAL DEFAULT 0
gross_amount REAL DEFAULT 0
folder       TEXT
status       TEXT DEFAULT 'DRAFT'
created_at   TIMESTAMP
```

### Is the data model sufficient?

**For manual stock management: yes.** The `materials` + `arrivals` two-table design supports:
- Named material catalog with pricing
- Per-delivery history with net/gross prices and document reference
- Low-stock alerting
- Supplier and wholesaler attribution per delivery

**For a reliable invoice-to-material pipeline: no.** Critical missing pieces:
- No alias table — `name UNIQUE` is the only identity key. If an invoice spells a material differently (e.g., "PB 18" vs "PB18"), a new duplicate record is silently created.
- No supplier item code — there is no field like `supplier_code` or `supplier_sku`. The `material_code` field is a free-text field with no lookup.
- No `supplier_id` FK — `supplier` is a plain text field. Two records can name the same supplier differently with no way to detect it.
- The `price_history` table defined in `sqlite_db.py` exists in the schema but **is never written to by any code in the project.**
- The `supplier_item_links` table defined in `sqlite_db.py` exists in the schema but **is never queried anywhere.**
- No confidence or review flag — there is no `needs_review`, `source_invoice_id`, or `ai_confidence` field on the material record.

---

## 6. Current Invoice Import Flow

### Web invoice flow (what users can do in the browser)

**Step 1 — Scan**

User opens the finance dashboard. The page calls `GET /db/scan-invoices`.

The backend (`main_api.py` line 861) scans two hardcoded local folders:
- `C:\pythonproject\tech_modul\faktury`
- `~\Downloads`

For each PDF (up to 20 files per folder):
1. Opens with `pypdf.PdfReader`, reads up to 2 pages of text
2. Applies 5 regex patterns:
   - Invoice number: `(?:Nr|Faktura nr|Numer)[:\s]*([/\w\-\(\)]+)`
   - Date: `(\d{4}-\d{2}-\d{2})`
   - NIP: `NIP[:\s]*(\d{3}-\d{3}-\d{2}-\d{2})`
   - Net amount: `(?:Netto|Wartość netto)[:\s]*([\d\s,]+\.\d{2})`
   - Gross: `(?:Razem do zapłaty|Kwota brutto|...)`
3. Returns: `{filename, folder, nr, date, nip, net, vat, total, status:"DRAFT", raw_text (first 500 chars)}`

**No line items are extracted. No materials are identified. No quantities are parsed.**

**Step 2 — Save**

User reviews the list and clicks to save selected invoices. Frontend calls `POST /db/invoices` for each selected item.

Backend saves to the SQLite `invoices` table: `{invoice_nr, date, nip, net_amount, vat_amount, gross_amount, folder}`.

**Step 3 — Tax summary**

`GET /db/tax-summary` sums the `vat_amount` from the `invoices` table to compute VAT balance. Sales VAT is estimated as `orders.budget * 0.23`.

**This is where the web invoice flow ends.** There is no line-item review, no material matching, no stock update from invoices.

**To update stock from an invoice, a user must:**
1. Open `/database/warehouse`
2. Manually fill in the "Przyjecia Towaru" form on the left sidebar: select material from dropdown, enter quantity, price, document number, supplier
3. Submit — creates one `arrivals` row

This is fully manual and completely disconnected from the invoice scanner.

---

### Desktop invoice flow (reference — not accessible from web)

**Step 1 — Source**  
Either: `import_invoice_pdf_file_multi(path)` (manual file pick) or `sync_invoices_from_mail()` (Gmail OAuth auto-pull).

**Step 2 — PDF text extraction**  
`invoice_pdf_import_service.py`: try pypdf embedded text first. If text is too short (under 300 chars), fall back to Tesseract OCR at `C:\Program Files\Tesseract-OCR\tesseract.exe` (Polish + English, PSM 6, OEM 3). If still short, render page with PyMuPDF at 2× resolution and OCR the render. Tracks `extraction_method` and `ocr_confidence`.

**Step 3 — Supplier detection**  
`_detect_supplier_template()` matches known token strings in the OCR text against `_SUPPLIER_TEMPLATES` dict: 10 known suppliers (Pakdrew, Wurth, Tabal, Artex, ITA, ICA, GOR-PAK, Mielec Serwis, ADLER, plus a default). Sets `supplier_template` on the invoice.

**Step 4 — Line-item parsing**  
For known suppliers: use supplier-specific template parser (`_parse_line_item_template`).  
For unknown: generic money/quantity/unit regex fallback (`_parse_line_item`).  
Each line item includes: `name, quantity, unit, parse_source, unit_price, total_price, unit_price_net, unit_price_gross, vat_amount, vat_rate, price_basis, material_type, thickness_mm, raw_line`.  
Deduplication: removes lines with identical `(name, quantity, total_price)` tuple.

**Step 5 — AI fallback** (optional, disabled by default)  
Activates only if `OPENAI_API_KEY` and `TECH_MODUL_INVOICE_AI_FALLBACK=1` env vars are set.  
Calls `gpt-4o-mini` with full OCR text (up to 22,000 chars) and a structured JSON schema prompt.  
Has circuit-breaker: after HTTP 429, AI is disabled for the session.  
Base regex result wins for non-empty fields; AI fills gaps.

**Step 6 — Multi-invoice splitting**  
Splits multi-page PDFs into separate invoice records by invoice number + supplier+date+amount signature.

**Step 7 — Storage**  
Written to `data/invoices.json` via `InvoiceStoreJson.upsert_invoice()`.  
Deduplication on `payload_hash` OR `attachment_key` OR `(invoice_number, supplier, date, total_gross)` signature.  
Flags: `needs_review`, `ai_fallback_used`, `exported_to_material`, `exported_at`.

**Step 8 — Export to material store**  
`export_invoice_to_material_store()`: copies each line item from `invoices.json` to `data/baza_materialu.json`.  
Matching: exact lowercase string match on `nazwa`. If match found → updates `cena_zl` and `ilosc`. If no match → creates new entry.  
Preserves link fields: `source_invoice_id`, `source_invoice_number`, `source_invoice_date`.

**Step 9 — Telegram notification**  
Sends alert for unreviewed invoices with `needs_review=True`.

---

## 7. Raw Invoice Data vs Normalized Material Data

### Are these layers separated?

**In the desktop: yes, but only partially.**

Three stores exist:
1. `data/invoices.json` — raw parsed invoice with all metadata, OCR confidence, line items with `raw_line`
2. `data/baza_materialu.json` — flattened material records with invoice provenance fields (`source_invoice_id`)
3. `data/tech_modul.db` → `materials` table — normalized records used by the web API

The link between layers 1 and 2 is `source_invoice_id`. The link between layers 2 and 3 does not exist — these are two entirely separate stores that are not synchronized.

**In the web: no separation at all.**

The web `/db/scan-invoices` returns header-only data. There are no line items, no raw invoice store, no invoice-to-material mapping step. When a user manually fills in the "Przyjecia Towaru" form, the `document_nr` field is a free-text invoice number — there is no FK to an invoice record in the arrivals table.

### Summary diagram

```
DESKTOP ONLY:
PDF file → invoice_pdf_import_service → invoices.json (rich)
                                               ↓
                                         baza_materialu.json (flat, invoice-linked)

WEB API:
PDF file → /db/scan-invoices (regex only) → invoices (SQLite, header only)
                                                    ↑
                                   (no connection to the above)

WEB MANUAL:
User form → /api/db/arrivals → arrivals (SQLite) → material (SQLite)
                     ↑
                (document_nr is free text, no FK to invoices table)
```

---

## 8. Matching and Alias Handling

### Supplier codes

No supplier code system exists in the web or the SQLite schema. The `material_code` field is a free-text string with no lookup table. Two entries for the same physical product from the same supplier can have different `material_code` values with no way to detect a match.

### Aliases

There is no alias table anywhere in the codebase. The `materials` table has `name TEXT UNIQUE` — the material name is the only identity. If an invoice line item spells a material name differently from the stored name, a new duplicate record will be created silently.

### Matching logic

**Web:** No matching logic exists. `get_material_by_name()` (`data_manager.py`) is the only lookup method, and it uses exact SQL: `WHERE name = ?`. Case-sensitive exact string.

**Desktop:** `_material_line_exists()` in `invoice_workflow_service.py` uses exact lowercase string match: compares `row_name != name_norm`. `compare_prices()` in `material_advanced_service.py` also uses `.lower().strip()` equality.

**Neither the web nor the desktop has:** fuzzy matching, Levenshtein distance, substring matching, phonetic matching, or embedding-based similarity.

### Confidence scoring

No confidence scoring exists for material matching. The desktop invoice parser does record `ai_confidence` and `ocr_confidence` on the invoice itself, but these scores are never propagated to material records and have no effect on whether a match is accepted or rejected.

### Manual verification

**Web:** There is no review step between scanning and saving. A user clicks "save" on the scanned invoice header — no line items are shown, no matching is proposed, no confirmation of material assignment is requested.

**Desktop:** The `InvoiceImportDialog` (Qt widget) shows parsed line items with discount controls and price comparison — this is a real review step. There is no equivalent in the web.

### Duplicate prevention

**Material creation:** The `name UNIQUE` constraint prevents exact duplicate names, but a slightly different spelling creates a new record without warning. No similarity check is performed before `INSERT`.

**Invoice saving:** The desktop `InvoiceStoreJson` deduplicates on payload hash. The web `/db/invoices` has no deduplication — calling `POST /db/invoices` twice for the same invoice creates two rows.

---

## 9. Price History / Purchase History

### Last price

**Supported (partially).** The `arrivals` table stores `unit_price_net` and `unit_price_gross` per delivery. The warehouse page (`warehouse/page.tsx`) calls `latestArrivalByMaterial` — a memo that finds the most recent arrival per `material_id` and displays its prices as "Netto/j." and "Brutto/j." in the table. This is a functional "last price" display.

### Average price

**Not supported in web.** The desktop's `compare_prices()` (`material_advanced_service.py` line 45) reads all entries for a material name from `baza_materialu.json` and computes both last price and average price. This logic is not exposed via any API endpoint and has no web equivalent.

### Supplier-specific pricing

**Not supported.** There is no data model for "this material costs X from supplier A and Y from supplier B." The `arrivals` table has `supplier` (text) and `unit_price_gross`, so historically different supplier prices are recorded as separate arrivals, but there is no query or UI to compare them.

`SupplierPriceStoreJson` (`data/supplier_prices.json`) was designed for this purpose — it has fields `{offer_id, material_id, material_name, supplier, unit, unit_price, price_basis, source, note, updated_at}` — but it has **no API endpoint and no frontend page.** It is completely orphaned.

### Invoice-linked history

**Partially.** The `arrivals` table has `document_nr` (free text). When the user manually records a delivery and types the invoice number, a link exists — but it is a text label, not a FK to the `invoices` table. If the invoice record changes, the arrival record is not updated.

### Price updates without overwriting material identity

**Supported in web.** `PATCH /db/materials/{id}` updates `price_per_m2` on the material record. Separately, `POST /api/db/arrivals` records a delivery with a price without modifying the material record's `price_per_m2`. So it is possible to keep arrival history without overwriting the base price — but the behavior depends on which fields the user chooses to send.

### `price_history` SQLite table

Defined in `src/storage/sqlite_db.py` with fields: `catalog_item_id, supplier_id, variant_id, net_price, vat_rate, gross_price, currency, price_unit, valid_from, document_ref, notes`. **This table is never written to by any code in the project.** It is schema-only dead weight.

---

## 10. AI / OCR / Parsing Support

### What actually exists

**Tesseract OCR — real, but conditionally available (desktop only)**

Located in `src/services/invoice_pdf_import_service.py`. Uses Tesseract at the hardcoded path `C:\Program Files\Tesseract-OCR\tesseract.exe`. Requires PIL/Pillow (image handling) and optionally PyMuPDF (fitz) for page rendering. If Tesseract is not installed, OCR returns empty string silently. The desktop pipeline uses OCR as a fallback when embedded PDF text is too short. Not exposed to the web at all.

**OpenAI GPT-4o-mini fallback — real, but disabled by default (desktop only)**

`src/services/invoice_ai_fallback_service.py`. Sends full OCR text (up to 22,000 chars) to `gpt-4o-mini` with a structured JSON schema prompt for invoice parsing. Requires two environment variables: `OPENAI_API_KEY` and `TECH_MODUL_INVOICE_AI_FALLBACK=1`. Has circuit-breaker on HTTP 429. Tracks `ai_fallback_used`, `ai_model`, `ai_confidence`, `ai_error` on the invoice object. Result is merged with the base regex parse (regex wins for non-empty fields). This is the only real AI in the codebase — and it is disabled by default and inaccessible from the web.

**Supplier template matching — real, desktop only**

`_SUPPLIER_TEMPLATES` dict with 10 known suppliers. Token substring search in OCR text. Enables supplier-specific line-item parsing rules for known format variants. Not exposed to web.

**The web `/db/scan-invoices` scanner — regex only, NOT AI**

The source code comment on `main_api.py` line 888 literally says `# Prosty "AI" parser (RegEx)`. This is 5 regex patterns applied to embedded pypdf text (no OCR, no GPT). It extracts only: invoice number, date, NIP, net total, gross total. No line items. No material identification. No supplier classification.

### What is not implemented

- No OCR in the web API path
- No line-item extraction in the web path
- No material matching from invoice data in the web path
- No AI model calls from the web (no API keys configured in web context)
- No PDF upload endpoint for invoice import (scan-invoices scans a hardcoded local folder)
- No review UI for parsed invoice line items in the web

---

## 11. What Is Already Done in Web

- Full material catalog — view, search, filter by type, group by category
- Per-category tab navigation (plyta, okleina, hdf, mdf, lakier, okucie, inne, etc.)
- Desktop-style resizable, drag-reorderable, column-togglable table (`warehouse/page.tsx`)
- Per-column text filters on the warehouse table
- Low-stock alerts (materials below `min_stock`)
- Manual delivery/arrival recording (quantity, net/gross price, document nr, supplier, wholesaler, date)
- Display of "last arrival" price and supplier next to each material row
- Inline editing of material properties and arrival data simultaneously
- Material CRUD: create, read, update
- Invoice header scanning from local PDF folders
- Invoice header saving to SQLite
- Tax summary (VAT balance from saved invoice headers)
- Per-tab column/form visibility preferences persisted to `localStorage`
- Low-stock Telegram notification capability (via API)

---

## 12. What Is Partially Done in Web

| Feature | What works | What is missing |
|---|---|---|
| Invoice scanning | Finds PDFs, extracts header totals | No line items, no OCR, no material identification |
| Invoice saving | Saves to SQLite `invoices` table | No deduplication, no link to arrivals or materials |
| Price display | Shows last arrival price per material | No average price, no supplier-specific price, no history chart |
| Arrival record | Stores document_nr as free text | Not linked to `invoices` table by FK |
| Material code | `material_code` field exists and is editable | No validation, no lookup table, not used for matching |
| Supplier field | Text field on material and on arrival | No supplier master table, no FK, no normalization |

---

## 13. What Is Missing

### Foundations for a reliable material database

- **Alias table** — a separate table linking alternative names/spellings to canonical material records. Without this, every invoice spelling variant creates a duplicate.
- **Supplier master table** — a separate table for known suppliers with a stable ID. Currently supplier names are free text duplicated across `materials.supplier`, `arrivals.supplier`, `invoices.supplier`. Spelling inconsistency is undetectable.
- **Supplier item codes** — a table mapping `(supplier_id, supplier_sku)` → `material_id`. This is the correct way to match invoice line items to catalog entries without relying on name matching.
- **`price_history` being written to** — the schema table exists but no code writes to it. A real price history requires writing a row on every new price observation from any source.
- **Deduplication on invoice save** — the web `POST /db/invoices` creates a new row every call. No hash or signature check prevents double-saving the same invoice.

### Invoice import pipeline for web

- **No PDF upload endpoint** — the web scanner reads from hardcoded local folders. A user working on a remote or tablet cannot point to their own invoice folder.
- **No line-item extraction** — the scan result has no line items. This is the most critical gap: without line items, no material matching is possible.
- **No invoice → arrival automation** — there is no flow where a scanned invoice automatically proposes arrivals to confirm.
- **No review/confirmation UI** — the desktop has `InvoiceImportDialog` showing parsed items with discount control and price comparison. The web has nothing equivalent.
- **No connection between `invoices` table and `arrivals` table** — the `document_nr` text in arrivals is the only link, and it is manually typed.

### Matching and deduplication

- **No fuzzy matching** — no Levenshtein, no substring, no phonetic matching for material name lookup
- **No alias system** — names must match exactly
- **No supplier code lookup** — `material_code` is unstructured free text
- **No confidence threshold** — no concept of "low confidence match → send to review queue"

### Price history

- **`price_history` table never written** — dead schema
- **`SupplierPriceStoreJson` orphaned** — no API, no UI, no writes
- **No average price in web** — only last arrival price is displayed
- **No supplier price comparison** — cannot see "Pakdrew quoted 85 PLN, Tabal quoted 80 PLN for the same board"

---

## 14. Main Data-Loss or Mismatch Risks

### Risk 1 — Duplicate material creation from name variation
**Severity: HIGH**  
The `materials` table uses `name UNIQUE`. If an invoice contains "PB Kronospan 18mm" and the catalog has "PB18", the lookup fails and a new duplicate material is created. The desktop's `InvoiceImportDialog` partially mitigates this through manual review, but the web has no review step at all.

### Risk 2 — Invoice scan loses all line-item data
**Severity: HIGH**  
The web scanner extracts only the invoice total. All line items — individual materials, quantities, unit prices — are discarded. A user who relies on the web scanner for stock management will never get stock updates from invoices automatically.

### Risk 3 — Price overwrite silently replaces history
**Severity: MEDIUM**  
When `PATCH /db/materials/{id}` sends `price_per_m2`, the single price field is overwritten. There is no previous price logged anywhere before the overwrite. If `price_history` were written to on every update, this would be safe — but it is not.

### Risk 4 — No invoice deduplication in web
**Severity: MEDIUM**  
`POST /db/invoices` has no hash or signature check. If a user clicks "save" twice, or if the finance page is loaded again after scanning, the same invoices can be inserted multiple times. The tax summary (`SUM(vat_amount)` from `invoices`) will then be wrong.

### Risk 5 — Arrivals not linked to invoice records by FK
**Severity: MEDIUM**  
`arrivals.document_nr` is free text. If a user types "FV/2026/001" in the arrival form and the actual invoice record in `invoices` has `invoice_nr = "FV 2026/001"`, there is no way to detect they are the same invoice. VAT deduction may be counted twice (once in tax summary from `invoices`, once when counting costs).

### Risk 6 — Two disconnected material stores
**Severity: MEDIUM** (only relevant when using both desktop and web)  
Desktop uses `data/baza_materialu.json` (via `MaterialStoreJson`). Web uses `data/tech_modul.db → materials`. These stores are not synchronized. Any material record created or updated from the desktop is not visible to the web, and vice versa.

### Risk 7 — OCR not available in web
**Severity: LOW** (for now, while using manual entry)  
Image-based or poorly embedded PDFs will fail silently in the web scanner (pypdf returns empty text, the regex finds nothing, the invoice shows "Nieznany" / "Brak daty"). No error is shown to the user — the file simply returns zeroes.

### Risk 8 — Hardcoded scan folders
**Severity: LOW**  
The scanner reads `C:\pythonproject\tech_modul\faktury` and `~\Downloads`. On any machine where these folders do not exist, the scan returns an empty list. A user on a different computer or working with a shared network drive will see nothing.

---

## 15. Recommended Target Data Model

The following entities and their relationships form a clean, auditable material database and invoice pipeline.

### Entity 1 — `suppliers` (new table)
```
id           INTEGER PK
name         TEXT UNIQUE NOT NULL     -- canonical supplier name
nip          TEXT                     -- tax ID
address      TEXT
phone        TEXT
email        TEXT
notes        TEXT
created_at   TIMESTAMP
```

### Entity 2 — `materials` (extend current)
```
id               INTEGER PK
name             TEXT UNIQUE NOT NULL -- canonical name
canonical_unit   TEXT                 -- m2 | szt | mb
category         TEXT
material_kind    TEXT
thickness        INTEGER
format_length_mm REAL
format_width_mm  REAL
pack_size        REAL
min_stock        REAL
parameter_json   TEXT
texture_url      TEXT
color_hex        TEXT
created_at       TIMESTAMP
-- REMOVE: price_per_m2 (move to price_history)
-- REMOVE: supplier, wholesaler (move to supplier_material_links)
-- REMOVE: purchase_type, stock_quantity (stock managed via arrivals)
```

### Entity 3 — `material_aliases` (new table)
```
id           INTEGER PK
material_id  INTEGER FK → materials.id
alias        TEXT NOT NULL            -- alternate name or spelling
source       TEXT                     -- "invoice", "manual", "import_3d"
created_at   TIMESTAMP
UNIQUE(material_id, alias)
```

### Entity 4 — `supplier_material_links` (new table — replaces orphaned `supplier_item_links`)
```
id              INTEGER PK
material_id     INTEGER FK → materials.id
supplier_id     INTEGER FK → suppliers.id
supplier_sku    TEXT                  -- supplier's own item code
supplier_name   TEXT                  -- supplier's name for this item (may differ from canonical)
unit            TEXT                  -- supplier's unit (may differ from canonical)
unit_conversion REAL DEFAULT 1.0     -- factor: supplier unit → canonical unit
notes           TEXT
is_preferred    BOOLEAN DEFAULT 0
created_at      TIMESTAMP
UNIQUE(supplier_id, supplier_sku)
```

### Entity 5 — `invoice_documents` (replaces current `invoices` table, extends it)
```
id              INTEGER PK
invoice_nr      TEXT NOT NULL
date            TEXT
supplier_id     INTEGER FK → suppliers.id  -- nullable until matched
nip             TEXT
net_amount      REAL
vat_amount      REAL
gross_amount    REAL
folder          TEXT
source          TEXT                       -- "scan_web", "import_desktop", "email"
file_path       TEXT
raw_text        TEXT                       -- full extracted text
ocr_used        BOOLEAN DEFAULT 0
ocr_confidence  REAL
ai_used         BOOLEAN DEFAULT 0
ai_confidence   REAL
extraction_method TEXT
needs_review    BOOLEAN DEFAULT 1
status          TEXT DEFAULT 'DRAFT'       -- DRAFT | REVIEWED | EXPORTED | REJECTED
payload_hash    TEXT UNIQUE               -- for deduplication
created_at      TIMESTAMP
UNIQUE(invoice_nr, nip, date)             -- business dedup key
```

### Entity 6 — `invoice_line_items` (new table)
```
id              INTEGER PK
invoice_id      INTEGER FK → invoice_documents.id
raw_line        TEXT                      -- original text from PDF
name            TEXT                      -- as appeared in invoice
quantity        REAL
unit            TEXT
unit_price_net  REAL
unit_price_gross REAL
vat_rate        REAL
total_price_net REAL
total_price_gross REAL
thickness_mm    REAL
material_type   TEXT
parse_source    TEXT                      -- "template_pakdrew" | "regex" | "ai"
-- match result:
material_id     INTEGER FK → materials.id  -- nullable until matched
match_confidence REAL
match_method    TEXT                      -- "exact" | "alias" | "sku" | "fuzzy" | "manual"
needs_review    BOOLEAN DEFAULT 1
reviewed_by     TEXT
reviewed_at     TIMESTAMP
```

### Entity 7 — `price_history` (activate the orphaned table, redefine)
```
id              INTEGER PK
material_id     INTEGER FK → materials.id
supplier_id     INTEGER FK → suppliers.id   -- nullable
invoice_id      INTEGER FK → invoice_documents.id  -- nullable
line_item_id    INTEGER FK → invoice_line_items.id  -- nullable
unit_price_net  REAL
unit_price_gross REAL
vat_rate        REAL
quantity        REAL
unit            TEXT
document_nr     TEXT
date            TEXT
source          TEXT                        -- "arrival_manual", "invoice_import", "price_offer"
created_at      TIMESTAMP
```

### Entity 8 — `arrivals` (keep current, add FKs)
```
-- keep existing fields
-- add:
invoice_id      INTEGER FK → invoice_documents.id  -- nullable
line_item_id    INTEGER FK → invoice_line_items.id  -- nullable
```

---

## 16. Recommended Build Order

### Priority 1 — Must build now

**1a. Expose existing pipeline to web: `POST /import-3d/invoice/upload`**  
Why: The real OCR+AI invoice pipeline already exists in the desktop code. The web needs an upload endpoint that calls `invoice_pdf_import_service` instead of the regex scanner.  
Dependency: None new — calls existing service code.  
Complexity: **low** (wire up existing Python service to a new FastAPI route)

**1b. Add invoice deduplication to `POST /db/invoices`**  
Why: Every web save currently creates duplicate rows, corrupting the tax summary.  
Dependency: None.  
Complexity: **low** (add `payload_hash` column + `ON CONFLICT DO NOTHING`)

**1c. Add `invoice_line_items` table and line-item extraction endpoint**  
Why: Without stored line items, the invoice-to-material flow cannot exist.  
Dependency: 1a (upload endpoint must call the parser and store items).  
Complexity: **medium** (schema migration + new API response shape)

**1d. Invoice review page in web**  
Why: Without review, all auto-matches are applied blindly — mistakes go undetected.  
Dependency: 1c (needs line items to display).  
Complexity: **medium** (new page: table of line items with match status, confirm/edit buttons)

### Priority 2 — Should build next

**2a. `suppliers` master table + API**  
Why: Makes supplier attribution consistent and queryable.  
Dependency: None.  
Complexity: **low** (new table, CRUD endpoints)

**2b. `material_aliases` table + alias matching in `get_material_by_name`**  
Why: Prevents duplicate material creation from invoice spelling variants.  
Dependency: 2a (supplier identity helps anchor alias creation).  
Complexity: **medium** (new table, update lookup query to check aliases, UI to add aliases)

**2c. Link `arrivals` to `invoice_documents` and `invoice_line_items` by FK**  
Why: Creates a full audit trail from invoice → line item → arrival → stock change.  
Dependency: 1c, 2a.  
Complexity: **medium** (schema migration + update `createArrival` logic)

**2d. Write to `price_history` on every price observation**  
Why: The table exists, is well-designed, and is never written to. This is a one-day fix that enables price trending.  
Dependency: 2a, 2b.  
Complexity: **low** (add INSERT to `price_history` in `createArrival` and invoice import handlers)

**2e. Average price and supplier price comparison in warehouse UI**  
Why: The owner cannot currently see whether prices have gone up or which supplier is cheapest.  
Dependency: 2d.  
Complexity: **low** (new query + UI column)

### Priority 3 — Later improvements

**3a. `supplier_material_links` table (supplier SKU mapping)**  
Why: The correct long-term solution for matching. Eliminates name-matching entirely for known suppliers.  
Dependency: 2a, 2b.  
Complexity: **high** (new table, UI for mapping, update matching logic to check SKU first)

**3b. Fuzzy matching on material name during invoice review**  
Why: Alias table catches known variants; fuzzy matching catches new ones before they become duplicates.  
Dependency: 2b.  
Complexity: **medium** (add `rapidfuzz` or similar, add `match_confidence` display to review UI)

**3c. PDF upload endpoint with OCR for web (connect to Tesseract)**  
Why: Currently the web scanner cannot process image-based PDFs.  
Dependency: Tesseract must be installed on the server; 1a gives a non-OCR version first.  
Complexity: **medium** (expose Tesseract path via env var, make it optional with graceful fallback)

**3d. Enable OpenAI AI fallback via web configuration**  
Why: GPT-4o-mini already works in desktop code. Exposing it via a settings page would improve parsing quality for unknown supplier formats.  
Dependency: 3c, `OPENAI_API_KEY` env var.  
Complexity: **low** (add env var check + feature flag toggle in UI)

---

## 17. Suggested UX for Material Import Review

After an invoice is uploaded and parsed, the user should see a **three-column review screen**:

### Column 1 — Invoice metadata (read-only)
- Supplier name (detected), invoice number, date, NIP
- Total net / VAT / gross
- Extraction method badge: "PDF text" / "OCR" / "AI-assisted"
- Confidence score if OCR or AI was used
- Status: DRAFT / REVIEWED / EXPORTED

### Column 2 — Parsed line items (main review area)
Each line item row shows:
- Raw line text (from PDF) — collapsed by default, expandable
- Detected name, quantity, unit, unit price net/gross, VAT rate
- **Match result badge:**
  - Green "MATCH: PB Egger 18mm" — exact or alias match found
  - Yellow "LOW CONFIDENCE: PB18? (72%)" — fuzzy match, needs confirmation
  - Red "NO MATCH — New item" — will create new material
- For matched items: link to the existing material record
- For no-match items: inline form to either (a) create new material or (b) pick existing from dropdown

### Column 3 — Actions
- "Zatwierdź wszystkie dopasowania" — bulk confirm all green matches → creates arrivals
- "Pomiń nierozpoznane" — skip red/yellow items for now
- "Eksportuj do magazynu" — finalize all confirmed matches as arrival records
- "Odrzuć fakturę" — mark invoice as rejected, no arrivals created

### After confirmation
- All confirmed items generate `arrivals` rows linked to the invoice
- `price_history` is updated for all matched materials
- Invoice status → EXPORTED
- Stock quantities are updated automatically

This is equivalent to what the desktop `InvoiceImportDialog` does, adapted for web.

---

## 18. Open Questions

1. **Should the web and desktop share one material database?** Currently they use separate stores (`tech_modul.db` for web, `baza_materialu.json` for desktop). Unifying them on SQLite would eliminate data divergence, but would require migrating the desktop material logic.

2. **Who is the intended user of the web invoice import?** If it is the owner reviewing invoices on a tablet, the review UX in Section 17 is the right target. If it is an accountant doing bulk import, the flow may need batch processing without per-item review.

3. **Where should scanned PDFs live?** The current scanner reads from `C:\pythonproject\tech_modul\faktury`. For a web-accessible system, should PDFs be uploaded via browser, pulled from a shared folder, or fetched from email automatically?

4. **Should the AI fallback be enabled by default once infrastructure is stable?** GPT-4o-mini costs roughly $0.01–0.05 per invoice at current pricing. At the volume of a small furniture workshop, this is negligible — but the business decision is the owner's.

5. **What is the canonical unit for each material type?** Boards (m2), edgebanding (mb), hardware (szt) — but some deliveries mix units (e.g., edgebanding sold by roll = 50mb). Should the system store the purchase unit and convert to canonical unit, or always store in canonical unit?

6. **Should duplicate detection prevent creation outright or just warn?** Blocking duplicates entirely could frustrate users who intentionally have two variants of the same material (e.g., same board from two suppliers at different prices). A warning-with-confirmation is safer than a hard block.

---

## 19. Plain-language Summary for Owner

### What we already have

The web warehouse works well for daily stock management. You can see all your materials in a desktop-style table, check which ones are running low, record a new delivery when goods arrive (with price and supplier), and edit material details. The invoice scanner can find your PDFs in the local folder and extract the total amounts for tax tracking.

### Why invoice data and the material database currently differ

The web's invoice scanner reads only the total amount from each invoice — it does not read the individual lines (which board, how much, what price). The scanner uses basic text patterns, not real document understanding. So when you look at an invoice and say "this has 5 sheets of PB Egger 18mm at 85 PLN each" — the web system sees only "gross total: 2150 PLN." None of that detail reaches your stock records automatically.

On top of this, the desktop computer has a completely separate, much more powerful import system (with real OCR and optional AI) that reads line items properly — but it stores its data in a different place that the web cannot see. The two sides do not talk to each other.

### What to fix first

1. **Add line-item extraction to the web invoice scanner** (roughly 2–3 days of work). This means when you scan an invoice, you see each line item: what material, quantity, price. Without this, nothing else can be automated.

2. **Add a review page** (2–3 days). After scanning, you review the detected items and confirm which ones match your catalog. This one step prevents most mistakes.

3. **Fix invoice deduplication** (half a day). Right now, saving the same invoice twice creates duplicate entries, which makes the tax total wrong.

4. **Build a supplier name table** (1 day). Right now "Kronospan" and "KRONOSPAN Sp. z o.o." are treated as different suppliers because names are just free text. A supplier list fixes this.

After these four steps, the material database will be reliable enough to trust for daily business decisions — stock levels, pricing, and supplier tracking.
