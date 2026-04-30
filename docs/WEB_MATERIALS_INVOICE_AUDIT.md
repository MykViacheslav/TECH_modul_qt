# WEB MATERIALS & INVOICE AUDIT

**Date:** 2026-04-22  
**Codebase:** C:\PythonProject\TECH_modul  
**Auditor:** Claude Sonnet 4.6 (automated inspection)

---

## 1. Executive Summary

The web version has a working, well-built material warehouse — you can view materials, record deliveries, see low-stock alerts, and edit records inline. This part works.

The invoice import does not work as a connected pipeline. The web scanner reads only five numbers from each PDF (invoice number, date, NIP, net total, gross total) using basic regex patterns. It extracts **no line items, no quantities, no unit prices, no product names.** After scanning, there is a manual gap: the user must open the warehouse page and enter every delivery by hand.

At the same time, the desktop application has a complete, tested invoice pipeline — with real OCR, ten known supplier templates, optional AI (GPT-4o-mini), and proper line-item extraction. But this pipeline stores its data in a separate JSON file that the web cannot read. The two systems share a hard disk but do not share data.

The material record structure has a `price_history` table defined in the database schema and a `supplier_item_links` table — but neither is ever written to by any code in the project. They are dead schema.

The practical result: every PLN spent on materials is re-entered by hand. Invoice data and material records are structurally disconnected, and the gap between them is real and costly.

---

## 2. Scope of This Audit

**Included:**
- Material database — SQLite schema, API endpoints, web warehouse page
- Supplier and wholesaler fields in material records
- Invoice scanning, parsing, and import — web flow and desktop flow
- Invoice line-item extraction and storage
- Mapping of invoice items to material catalog
- Aliases, supplier codes, product code handling
- Price history and purchase/arrival history
- AI, OCR, and PDF parsing

**Excluded:**
- Project estimation and quotation (covered in WEB_SERVICES_ESTIMATION_AUDIT.md)
- Production terminals, kiosk, RCP timekeeping
- Client and order management
- Finance tax summaries, except where they directly touch invoice records

---

## 3. Relevant Web Structure

### Pages / Routes

| Route | File | Relevance |
|---|---|---|
| `/database/warehouse` | `frontend/src/app/database/warehouse/page.tsx` | Main material warehouse — full desktop-style table, arrival entry form, low-stock panel, inline editing |
| `/database` | `frontend/src/app/database/page.tsx` | Hub page linking to all database sub-sections |
| `/database/shopping` | `frontend/src/app/database/shopping/page.tsx` | Low-stock shopping list — "mark as bought" is local-only mock (no API call) |
| `/database/library` | `frontend/src/app/database/library/page.tsx` | Material library (read-only catalog view) |
| `/finance/global` | `frontend/src/app/finance/global/page.tsx` | Finance dashboard — includes invoice scan trigger and tax summary display |

**No dedicated invoice import page exists in the web.** Invoice scanning is a secondary feature embedded in the finance dashboard. There is no web page for reviewing parsed invoice line items.

### Key Components

| File | Purpose |
|---|---|
| `warehouse/page.tsx` | 1523-line component: material list (grouped, filterable, resizable columns), delivery entry form, low-stock alerts, per-group tab navigation, per-tab column preferences saved to `localStorage`, inline position editing |
| `frontend/src/services/api.ts` | `TechModulAPI` — typed API client. Relevant methods: `getMaterials`, `createMaterial`, `updateMaterial`, `getArrivals`, `createArrival`, `updateArrival`, `getLowStockMaterials`, `scanInvoices`, `getInvoices`, `createInvoice` |

### Backend API Endpoints

| Endpoint | Method | Used by web |
|---|---|---|
| `/db/materials` | GET | Yes — loads material catalog |
| `/db/materials` | POST | Yes — creates new material record |
| `/db/materials/{id}` | PATCH | Yes — updates material fields |
| `/api/db/materials/low-stock` | GET | Yes — powers low-stock panel |
| `/api/db/arrivals` | GET | Yes — full purchase/delivery history |
| `/api/db/arrivals` | POST | Yes — records new delivery |
| `/api/db/arrivals/{id}` | PATCH | Yes — corrects existing delivery record |
| `/db/scan-invoices` | GET | Yes — scans hardcoded local folders for PDFs |
| `/db/invoices` | GET | Yes — reads saved invoice headers |
| `/db/invoices` | POST | Yes — saves selected invoice header to SQLite |
| `/db/tax-summary` | GET | Yes — VAT balance for finance dashboard |

---

## 4. Desktop Reference Structure

Used only as a direct comparison for the invoice pipeline.

| File | Role |
|---|---|
| `src/services/invoice_pdf_import_service.py` | PDF text extraction, Tesseract OCR fallback, 10 supplier templates, line-item regex parsing, multi-invoice splitting |
| `src/services/invoice_ai_fallback_service.py` | OpenAI GPT-4o-mini fallback for invoice parsing — disabled by default, requires env vars |
| `src/services/invoice_workflow_service.py` | Full pipeline orchestration: source → OCR → parse → store → export to material store → Telegram notify |
| `src/storage/invoice_store_json.py` | `InvoiceStoreJson` — rich JSON store for parsed invoices (`data/invoices.json`) |
| `src/storage/material_store_json.py` | `MaterialStoreJson` — desktop material store (`data/baza_materialu.json`) — **separate from SQLite** |
| `src/storage/supplier_price_store_json.py` | `SupplierPriceStoreJson` — supplier price comparison store — no API, no UI, completely orphaned |
| `src/storage/sqlite_db.py` | Defines SQLite schema including `price_history` and `supplier_item_links` — both exist only as schema, never written to |
| `src/services/material_advanced_service.py` | `compare_prices()` — reads price history from JSON material store using exact name match |
| `src/widgets/invoice_import_dialog.py` | Desktop Qt dialog — shows parsed line items, discount controls, price comparison for manual review |

---

## 5. Current Material Record Structure

### SQLite `materials` table (the web source of truth)

```
id               INTEGER PK AUTOINCREMENT
name             TEXT UNIQUE NOT NULL      ← only identity key; no alias, no code
price_per_m2     REAL                      ← single price field, no history
thickness        INTEGER
material_code    TEXT DEFAULT ''           ← free text, no lookup table, not validated
category         TEXT DEFAULT 'boards'     ← boards | hardware | finishes | other
material_kind    TEXT DEFAULT 'other'      ← hdf | mdf | plyta | okleina | lakier | okucie | inne
unit             TEXT DEFAULT 'm2'         ← m2 | szt | mb
is_library       BOOLEAN DEFAULT 1
stock_quantity   REAL DEFAULT 0.0          ← updated manually via arrivals
min_stock        REAL DEFAULT 0.0
purchase_type    TEXT DEFAULT 'nothing'    ← invoice | cash | nothing
supplier         TEXT DEFAULT ''           ← free text, no FK to supplier table
wholesaler       TEXT DEFAULT ''           ← free text, no FK
format_length_mm REAL DEFAULT 0.0
format_width_mm  REAL DEFAULT 0.0
pack_size        REAL DEFAULT 0.0
parameter_json   TEXT DEFAULT '{}'         ← arbitrary extra parameters as JSON string
texture_url      TEXT DEFAULT ''
color_hex        TEXT DEFAULT '#ffffff'
```

### SQLite `arrivals` table (purchase/delivery history)

```
id               INTEGER PK AUTOINCREMENT
material_id      INTEGER FK → materials.id
order_id         INTEGER FK → orders.id, nullable
quantity         REAL
unit             TEXT
purchase_type    TEXT
document_nr      TEXT                      ← free text invoice number, no FK to invoices table
supplier         TEXT                      ← free text
wholesaler       TEXT
unit_price_net   REAL
unit_price_gross REAL
price_total      REAL
date             TEXT
created_at       TIMESTAMP
```

### SQLite `invoices` table (minimal web invoice store)

```
id           INTEGER PK AUTOINCREMENT
invoice_nr   TEXT
date         TEXT
nip          TEXT
net_amount   REAL
vat_amount   REAL
gross_amount REAL
folder       TEXT
status       TEXT DEFAULT 'DRAFT'
created_at   TIMESTAMP
```

### Is this sufficient for production?

**For manual stock management: yes.** The two-table design (materials + arrivals) handles a real warehouse with pricing, low-stock thresholds, and delivery tracking. The warehouse UI is genuinely solid.

**For an automated invoice-to-material pipeline: no.** The following are structurally absent:

- **No alias table.** `name UNIQUE` is the only identity. A spelling variant on an invoice creates a silent duplicate.
- **No supplier master table.** Supplier is a plain text field duplicated across materials, arrivals, and invoices with no normalization.
- **No supplier item code.** The `material_code` field is unstructured free text. There is no `supplier_sku` field and no mapping table.
- **`price_history` table exists in `sqlite_db.py` schema but no code ever writes to it.** Dead schema.
- **`supplier_item_links` table exists in schema but is never queried.** Also dead schema.
- **No `needs_review`, `source_invoice_id`, or `match_confidence` field** on material records — no traceability from material back to the invoice that created it.
- **No FK between `arrivals.document_nr` and `invoices.id`** — the link is a free-text string the user types by hand.

---

## 6. Current Invoice Import Flow

### Web path (what a user actually experiences)

**Step 1 — Trigger scan**

User opens the finance dashboard. The page calls `GET /db/scan-invoices`.

**Step 2 — Backend scans two hardcoded folders**

`main_api.py` line 861–925 scans:
- `C:\pythonproject\tech_modul\faktury`
- `~\Downloads`

Up to 20 PDF files per folder. If neither folder exists, the endpoint returns an empty array.

**Step 3 — Regex parsing (no OCR, no AI)**

For each PDF, `pypdf.PdfReader` extracts embedded text from up to 2 pages. Five regex patterns run:

```python
# Source comment in main_api.py line 888:
# Prosty "AI" parser (RegEx)   ← the developer's own label

invoice_nr: r"(?:Nr|Faktura nr|Numer)[:\s]*([/\w\-\(\)]+)"
date:       r"(\d{4}-\d{2}-\d{2})"
nip:        r"NIP[:\s]*(\d{3}-\d{3}-\d{2}-\d{2})"
net:        r"(?:Netto|Wartość netto)[:\s]*([\d\s,]+\.\d{2})"
gross:      r"(?:Razem do zapłaty|Kwota brutto|...)[:\s]*([\d\s,]+\.\d{2})"
```

Returns: `{filename, folder, nr, date, nip, net, vat, total, status:"DRAFT", raw_text (first 500 chars only)}`

**What is not extracted:** material names, quantities, unit prices, product codes, supplier name, any line items at all.

**Step 4 — User selects and saves invoice headers**

User reviews the list on the finance page. For each invoice they want to keep, frontend calls `POST /db/invoices`. This saves `{invoice_nr, date, nip, net_amount, vat_amount, gross_amount, folder}` to the SQLite `invoices` table.

No deduplication check exists. Saving the same invoice twice inserts two rows.

**Step 5 — Tax summary**

`GET /db/tax-summary` reads the sum of `vat_amount` from the `invoices` table and subtracts it from estimated sales VAT (`orders.budget * 0.23`). This is the only downstream use of the saved invoice data.

**Step 6 — Manual stock update (completely disconnected)**

To update stock from an invoice, a user must independently:
1. Open `/database/warehouse`
2. Fill in the "Przyjecia Towaru" sidebar form: select material from dropdown, enter quantity, date, price, document number, supplier
3. Click "Zapisz Przyjęcie"

One form submission = one arrival row for one material. A 30-line invoice requires 30 manual form submissions.

There is no connection between Step 4 (saving invoice header) and Step 6 (recording arrival). The `document_nr` field in the arrival form is a free-text field where the user can optionally type the same invoice number — but this creates no FK relationship.

---

### Desktop path (for comparison — not accessible from web)

The desktop has a full pipeline in `invoice_workflow_service.py`:

1. **Source:** Local PDF file (`import_invoice_pdf_file_multi`) or Gmail OAuth email attachment (`sync_invoices_from_mail`)
2. **Text extraction:** `pypdf` embedded text first; if under 300 chars, Tesseract OCR (`C:\Program Files\Tesseract-OCR\tesseract.exe`, Polish+English, PSM 6) with PIL/Pillow image extraction and optional PyMuPDF 2× render
3. **Supplier detection:** `_detect_supplier_template()` — token substring match against 10 known supplier profiles (Pakdrew, Wurth, Tabal, Artex, ITA, ICA, GOR-PAK, Mielec Serwis, ADLER, default)
4. **Line-item parsing:** Supplier-specific template parser for known suppliers; generic regex fallback for unknown; deduplication by `(name, quantity, total_price)` tuple
5. **AI fallback** (disabled by default): `gpt-4o-mini` via OpenAI API — requires `OPENAI_API_KEY` + `TECH_MODUL_INVOICE_AI_FALLBACK=1` env vars; circuit-breaks on HTTP 429
6. **Multi-invoice splitting:** Detects invoice number boundaries in multi-page PDFs
7. **Storage:** `data/invoices.json` via `InvoiceStoreJson` — deduplication on payload hash; rich payload including OCR confidence, all line items with `raw_line`, `parse_source`, `ai_fallback_used`, `needs_review`
8. **Material export:** `export_invoice_to_material_store()` copies each line item to `data/baza_materialu.json` using exact lowercase name match — creates new entry if name not found, updates `cena_zl` if found
9. **Review UI:** `InvoiceImportDialog` (PyQt6) shows parsed items with discount control and price comparison before user confirms

**The `data/invoices.json` and `data/baza_materialu.json` files are completely invisible to the web API.** No web endpoint reads them.

---

## 7. Raw Invoice Data vs Normalized Material Data

### Are these layers separated?

**In the web: No. They are collapsed into one.**

The web flow is:
```
PDF text → regex → invoice header numbers
                         ↓
                   invoices (SQLite) — header only, no items
                         ↓ (no automated connection)
                   arrivals (SQLite) — manually entered per delivery
                         ↓ (no automated connection)
                   materials (SQLite) — manually edited catalog
```

There is no extracted invoice line item layer in the web. Raw invoice data (the PDF) and normalized material data (the warehouse) are separated only by the user's memory and manual re-entry.

**In the desktop: Yes, but with one gap.**

```
PDF → invoices.json (raw + parsed, full line items)
             ↓ (exact name match)
      baza_materialu.json (flat material entries, invoice-linked)
             ↓ (no synchronization)
      tech_modul.db → materials (SQLite, used by web)
```

Three layers exist in the desktop:
1. **Source document** — `invoices.json` preserves raw OCR text, confidence, all line items with `raw_line`
2. **Material entries** — `baza_materialu.json` with invoice provenance fields (`source_invoice_id`, `source_invoice_number`)
3. **Normalized catalog** — SQLite `materials` (web)

The link between layer 2 and layer 3 **does not exist.** Desktop material exports go to `baza_materialu.json`. Web material records live in SQLite. They have no synchronization mechanism and will diverge permanently once both sides have been used.

---

## 8. Matching Logic and Alias Handling

### Supplier codes

No supplier code system exists anywhere in the web or its SQLite schema. The `material_code` field on `materials` is a free-text string. No validation, no lookup table, no reference to any supplier catalog. The field is searchable but meaningless for automated matching.

### Aliases

No alias table exists. The `materials.name` field is `UNIQUE` and is the sole identity key. If an invoice contains "Płyta PB Kronospan 18mm Biały" and the catalog has "PB18 Biały", no match is found and a new record is created. This is silent — no warning is shown.

### Fuzzy matching

No fuzzy matching exists anywhere. The only lookup method is `data_manager.get_material_by_name(name)` which executes `WHERE name = ?` — exact, case-sensitive SQL match. The desktop's `_material_line_exists()` uses `.lower().strip()` equality — still exact.

No Levenshtein distance, no substring search, no token overlap, no embedding similarity exists in any code in this project.

### Confidence scoring

No confidence score exists for material matching. The desktop records `ocr_confidence` and `ai_confidence` on the invoice document, but these scores are not propagated to material records and have no effect on matching behavior.

### Manual verification

**Web:** None. The only review step is the user looking at the invoice header list (invoice number + total) before clicking "save." There is no display of extracted items to review.

**Desktop:** `InvoiceImportDialog` shows parsed items one by one with discount editing and price comparison. This is a real review step that is absent from the web entirely.

### Duplicate prevention

**Materials:** `name UNIQUE` in SQLite prevents exact-name duplicates. Any spelling variation creates a new record without warning. No similarity check before INSERT.

**Invoices:** No deduplication. `POST /db/invoices` always inserts a new row. Submitting the same invoice twice doubles its VAT amount in the tax summary.

**Arrivals:** No deduplication. Multiple arrivals with the same material_id, date, and document_nr can coexist freely.

### Unit conversion

No unit conversion exists. The `unit` field on `materials` (m2 / szt / mb) and the `unit` field on `arrivals` are plain text strings. If an invoice records a delivery in "kpl" (set) and the material catalog uses "szt" (piece), the mismatch is stored as-is with no conversion, no flag, no warning.

---

## 9. Price History / Purchase History

### Last price

**Supported.** The `arrivals` table stores `unit_price_net` and `unit_price_gross` per delivery. The warehouse page computes `latestArrivalByMaterial` — the most recent arrival per `material_id` — and shows its net/gross price in the table. This works as a "last purchase price" display.

### Average price

**Not supported in web.** The desktop's `compare_prices()` (`material_advanced_service.py`) reads all historical entries from `baza_materialu.json` and computes both last and average price by exact name match. No equivalent API endpoint exists for the web. The warehouse table shows only the latest arrival price.

### Invoice-linked history

**Partially.** The `arrivals.document_nr` field is a free-text invoice number. When a user manually types the invoice number when recording a delivery, a human-readable link exists. But it is not a FK to the `invoices` table — it is just a string. Querying "all deliveries from invoice FV/2026/123" requires string matching, and any spelling difference breaks the link.

### Supplier-specific prices

**Not supported.** There is no way in the web to ask "what did Pakdrew charge for PB18 last quarter?" The arrival history contains supplier name (text) and price, but no query or UI aggregates this. `SupplierPriceStoreJson` (`data/supplier_prices.json`) was designed for this purpose but has no API endpoint and no frontend — it is completely orphaned.

### Updating price without overwriting material identity

**Supported, but ambiguous.** `PATCH /db/materials/{id}` can update `price_per_m2` on the material record independently of arrivals. But the field is a single value — no previous price is logged before the update. The `price_history` SQLite table (defined in `sqlite_db.py`) exists for exactly this purpose but **is never written to by any code in the project.** Every `PATCH` to `price_per_m2` silently discards the old value.

---

## 10. Data Loss / Mismatch Risks

### Risk 1 — All invoice line-item data is discarded (CRITICAL)
The web scanner returns only five fields per invoice. Every individual line item — product name, quantity, unit price, product code — is thrown away before it reaches any storage. There is no pathway from a scanned invoice to a stock update without complete manual re-entry.

### Risk 2 — Duplicate materials from name variations (HIGH)
A single material can exist as "PB18", "PB 18", "Płyta PB 18mm", "Kronospan PB 18" — each as a separate `materials` row. The `name UNIQUE` constraint prevents exact duplicates but allows all variations. Every invoice import that uses automated matching will create duplicates for any slightly different spelling. Once duplicated, the stock is split across phantom records.

### Risk 3 — Invoice saved twice corrupts VAT summary (HIGH)
`POST /db/invoices` has no deduplication. If a user triggers the scanner twice, or if the finance page reloads and re-saves, the same invoice's VAT amount is double-counted in `GET /db/tax-summary`. The tax balance shown on the finance dashboard can be wrong by a significant amount with no indication to the user.

### Risk 4 — `price_per_m2` update silently overwrites history (MEDIUM)
When a user edits a material's price via the inline edit form, `PATCH /db/materials/{id}` replaces `price_per_m2` with no archive. The previous price is not logged anywhere. The `price_history` table exists in the schema but has never been written to.

### Risk 5 — No FK between `arrivals.document_nr` and `invoices.id` (MEDIUM)
If an invoice is saved to the `invoices` table and the user also records arrivals with that invoice number in `arrivals.document_nr`, these two records are not linked by a FK. If the invoice record is deleted or its `invoice_nr` corrected, the arrival records keep their original text. Queries joining invoices to arrivals via the document number string will break on any spelling difference.

### Risk 6 — Two material stores diverge permanently (MEDIUM)
The desktop writes to `data/baza_materialu.json`. The web writes to SQLite `materials`. These are not synchronized. Any material created from a desktop invoice import is invisible to the web. Any material created from the web form is invisible to desktop invoice matching. Both sides will accumulate independent records for the same physical products.

### Risk 7 — Hardcoded scan folders fail on any other machine (LOW)
The scanner reads `C:\pythonproject\tech_modul\faktury` and `~\Downloads`. On a different computer, on a tablet, or on a network share, both paths do not exist. The scan returns an empty list with no error message to the user.

### Risk 8 — OCR not available in web path (LOW for now)
Image-based PDFs (scanned paper invoices) produce empty text via `pypdf`. The regex finds nothing. The invoice is returned with "Nieznany" / "Brak daty" / 0.00 values. No error or warning distinguishes this from a successfully parsed invoice. The user sees the same card either way.

---

## 11. AI / OCR / Parsing Support

### Web — what is actually there

**pypdf text extraction:** Real. Extracts embedded text from PDF pages when the PDF contains embedded text (i.e., it was not scanned from paper). Works for most supplier-generated PDFs.

**Regex parser labeled "AI":** The developer comment in `main_api.py` line 888 reads `# Prosty "AI" parser (RegEx)`. This is 5 regex patterns. It is not AI by any definition. It extracts header totals only.

**OCR:** Not present in the web path. `pypdf` is the only extraction method. No Tesseract, no other OCR library is called by any web API endpoint.

**AI-assisted matching or extraction:** Not present in the web path. No call to OpenAI, no embedding lookup, no LLM of any kind is invoked from any web-facing API endpoint.

### Desktop — what is actually there

**Tesseract OCR:** Real, in `invoice_pdf_import_service.py`. Used as a fallback when embedded text is too short (under ~300 characters). Requires Tesseract installed at the hardcoded path `C:\Program Files\Tesseract-OCR\tesseract.exe`. If not installed, OCR fails silently and the invoice gets empty line items. Optional dependency: PIL/Pillow (image extraction), PyMuPDF/fitz (2× page render for better OCR input).

**Supplier template matching:** Real. 10 named supplier profiles with token substring detection. Enables supplier-specific line-item parsing rules for Pakdrew, Wurth, Tabal, Artex, ITA, ICA, GOR-PAK, Mielec Serwis, ADLER. Falls back to generic regex for unknown suppliers.

**OpenAI GPT-4o-mini fallback:** Real, in `invoice_ai_fallback_service.py`. Sends full OCR text (up to 22,000 chars) to `gpt-4o-mini` with a structured JSON schema prompt. **Disabled by default** — requires both `OPENAI_API_KEY` and `TECH_MODUL_INVOICE_AI_FALLBACK=1` environment variables to be set. Has circuit-breaker on HTTP 429 (rate limit). When active, its result is merged with the base regex parse — regex wins for non-empty fields; AI fills gaps.

Tracks: `ai_fallback_used`, `ai_model` (configurable via `TECH_MODUL_INVOICE_AI_MODEL`, defaults to `gpt-4o-mini`), `ai_confidence`, `ai_error`.

**Bottom line:** The desktop AI/OCR pipeline is real and production-capable. The web has no AI, no OCR, and a regex scanner that extracts five fields.

---

## 12. What Is Already Done in Web

- Full material catalog view with search, per-category tab navigation, and grouping by material type
- Desktop-style warehouse table: resizable columns, drag-reorder, per-column filters, column visibility toggle
- Column and form field preferences saved per material-type tab to `localStorage`
- Manual delivery/arrival recording (quantity, net/gross price, document number, supplier, wholesaler, date)
- "Last arrival" price displayed next to each material in the table
- Inline editing of material properties and the latest arrival record simultaneously
- Low-stock alert panel (materials below `min_stock`, with missing quantity shown)
- Material CRUD via API: create, read, update
- Invoice header scanning from local PDF folders (invoice number, date, NIP, totals only)
- Invoice header saving to SQLite `invoices` table
- VAT balance calculation from saved invoice headers
- Low-stock Telegram notification (via API endpoint)
- Warehouse table "Edytuj" button opens inline form prefilled from the row

---

## 13. What Is Partially Done in Web

| Feature | What works | What is missing |
|---|---|---|
| Invoice import | PDF scan, header regex extraction, save to SQLite | No line items, no OCR, no material matching, no arrival automation |
| Price display | Last arrival price per material row | No average price, no history chart, no supplier comparison |
| Invoice → arrival link | `document_nr` text field | Not a FK; no join possible; deduplication absent |
| Material code | Field exists, editable | Not validated, not used for lookup, no supplier mapping |
| Supplier field | Text field on material and arrival | No supplier table, no normalization, free text only |
| Shopping list | Low-stock items listed | "Mark as bought" calls `alert()` and removes local state only — no API call |
| Price history | `price_history` table defined in SQLite schema | Never written to by any code |
| Supplier item links | `supplier_item_links` table defined in schema | Never queried by any code |

---

## 14. What Is Missing

### For reliable invoice import

- **PDF upload endpoint with line-item extraction** — the web has no endpoint to upload a PDF and receive back parsed line items. This is the foundational missing piece.
- **Invoice line-item storage layer** — no table or model for extracted invoice rows (product name, quantity, unit, price) separate from the material catalog.
- **Invoice-to-arrival automation** — no flow converts extracted invoice line items into arrival records, even after manual review.
- **Invoice review page** — no web page displays parsed line items for user confirmation before any data is written.
- **Invoice deduplication** — `POST /db/invoices` inserts blindly; no hash or signature check exists.

### For reliable material matching

- **Alias table** — no alternate-name lookup; any spelling variant creates a duplicate material.
- **Supplier master table** — supplier names are free text; "Kronospan" and "Kronospan Sp. z o.o." are unrelated strings.
- **Supplier item code / SKU mapping** — no way to say "Kronospan code K001 = material ID 47."
- **Fuzzy matching** — no approximate name lookup of any kind.
- **Duplicate detection before INSERT** — `name UNIQUE` blocks exact duplicates but allows all variations silently.

### For reliable price history

- **`price_history` must be written to** — the table exists; it just needs INSERT calls on every price-bearing event (arrival, manual edit, invoice import).
- **Average price query** — computable from `arrivals` already; just needs an API endpoint and UI display.
- **Supplier-specific price query** — `arrivals` has supplier text and price; needs aggregation query and UI.

### For production reliability

- **FK between `arrivals.document_nr` and `invoices.id`** — replace free-text link with a real FK column (`invoice_id INTEGER REFERENCES invoices(id)`).
- **Material store unification** — desktop and web must write to the same store, or a sync mechanism must exist.
- **Configurable scan folder** — replace hardcoded `C:\pythonproject\tech_modul\faktury` with a setting.

---

## 15. Recommended Target Data Model

### Entity 1 — `suppliers` (new)

```sql
id         INTEGER PK
name       TEXT UNIQUE NOT NULL   -- canonical name
nip        TEXT
address    TEXT
phone      TEXT
email      TEXT
notes      TEXT
created_at TIMESTAMP
```

### Entity 2 — `materials` (extend current, remove redundant fields)

```sql
id               INTEGER PK
name             TEXT UNIQUE NOT NULL   -- canonical name
canonical_unit   TEXT                   -- m2 | szt | mb  (rename from unit)
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
-- REMOVE: price_per_m2   → move to price_history
-- REMOVE: supplier, wholesaler  → move to supplier_material_links
-- REMOVE: stock_quantity  → derive from arrivals SUM
-- REMOVE: purchase_type   → per-arrival field, not per-material
```

### Entity 3 — `material_aliases` (new)

```sql
id          INTEGER PK
material_id INTEGER FK → materials.id
alias       TEXT NOT NULL
source      TEXT   -- "invoice", "manual", "import_3d"
created_at  TIMESTAMP
UNIQUE(material_id, alias)
```

### Entity 4 — `supplier_material_links` (replace orphaned `supplier_item_links`)

```sql
id              INTEGER PK
material_id     INTEGER FK → materials.id
supplier_id     INTEGER FK → suppliers.id
supplier_sku    TEXT            -- supplier's own product code
supplier_name   TEXT            -- supplier's label for this item
unit            TEXT            -- supplier's unit (may differ from canonical)
unit_conversion REAL DEFAULT 1  -- factor: supplier unit → canonical unit
is_preferred    BOOLEAN DEFAULT 0
notes           TEXT
created_at      TIMESTAMP
UNIQUE(supplier_id, supplier_sku)
```

### Entity 5 — `invoice_documents` (replace and extend current `invoices` table)

```sql
id                INTEGER PK
invoice_nr        TEXT NOT NULL
date              TEXT
supplier_id       INTEGER FK → suppliers.id   -- nullable until matched
nip               TEXT
net_amount        REAL
vat_amount        REAL
gross_amount      REAL
folder            TEXT
source            TEXT    -- "scan_web" | "upload_web" | "desktop_import" | "email"
file_path         TEXT
raw_text          TEXT    -- full extracted text (not just 500 chars)
ocr_used          BOOLEAN DEFAULT 0
ocr_confidence    REAL
ai_used           BOOLEAN DEFAULT 0
ai_confidence     REAL
extraction_method TEXT
needs_review      BOOLEAN DEFAULT 1
status            TEXT DEFAULT 'DRAFT'   -- DRAFT | REVIEWED | EXPORTED | REJECTED
payload_hash      TEXT UNIQUE            -- SHA256 of raw content for dedup
created_at        TIMESTAMP
UNIQUE(invoice_nr, nip, date)            -- business-level dedup key
```

### Entity 6 — `invoice_line_items` (new)

```sql
id                INTEGER PK
invoice_id        INTEGER FK → invoice_documents.id
line_index        INTEGER     -- order in invoice
raw_line          TEXT        -- original text from PDF
name_raw          TEXT        -- as appeared in invoice
quantity          REAL
unit_raw          TEXT        -- as appeared in invoice
unit_price_net    REAL
unit_price_gross  REAL
vat_rate          REAL
total_price_net   REAL
total_price_gross REAL
thickness_mm      REAL
parse_source      TEXT        -- "template_pakdrew" | "regex" | "ai" | "manual"
-- match result (filled during review):
material_id       INTEGER FK → materials.id   -- nullable until matched
match_confidence  REAL
match_method      TEXT    -- "exact" | "alias" | "sku" | "fuzzy" | "manual"
match_reviewed    BOOLEAN DEFAULT 0
reviewed_by       TEXT
reviewed_at       TIMESTAMP
```

### Entity 7 — `price_history` (activate the dead schema table, redefine)

```sql
id               INTEGER PK
material_id      INTEGER FK → materials.id
supplier_id      INTEGER FK → suppliers.id   -- nullable
invoice_id       INTEGER FK → invoice_documents.id  -- nullable
line_item_id     INTEGER FK → invoice_line_items.id -- nullable
arrival_id       INTEGER FK → arrivals.id           -- nullable
unit_price_net   REAL
unit_price_gross REAL
vat_rate         REAL
quantity         REAL
unit             TEXT
document_nr      TEXT
date             TEXT
source           TEXT    -- "arrival_manual" | "invoice_import" | "price_offer"
created_at       TIMESTAMP
```

### Entity 8 — `arrivals` (keep current, add FKs)

```sql
-- keep all current fields
-- add:
invoice_id    INTEGER FK → invoice_documents.id   -- nullable
line_item_id  INTEGER FK → invoice_line_items.id  -- nullable
```

---

## 16. Recommended Import Review Workflow

This is the practical workflow a user should experience after uploading an invoice:

### Step 1 — Upload / Scan

User either:
- Uploads a PDF file via a browser file picker (new endpoint: `POST /invoices/upload`)
- Or triggers a folder scan as today (but with OCR fallback)

Backend extracts text (pypdf first, Tesseract OCR fallback), detects supplier, parses all line items, stores to `invoice_documents` + `invoice_line_items`, sets `status = DRAFT`, `needs_review = true`.

### Step 2 — Invoice Header Review

User sees the parsed invoice header: supplier, invoice number, date, NIP, total net/gross. They can correct any field. A confidence badge shows whether OCR or AI was used.

### Step 3 — Line Item Review Table

A table shows every extracted line item with columns:

| Raw name from PDF | Quantity | Unit | Net price | Matched catalog entry | Confidence | Action |
|---|---|---|---|---|---|---|
| Płyta PB 18mm Biały | 5.00 | m2 | 85.00 | PB18 Biały (exact) | ✓ 100% | Confirm |
| ABS 0.8 Biały Mb | 25.00 | mb | 12.40 | ABS 0.8 Biały (alias) | ⚠ 87% | Confirm / Edit |
| Zawiasy Blum 110° | 10.00 | szt | 4.20 | — no match — | ✗ | Create new / Pick |

Statuses:
- **Green (exact/alias match, high confidence):** pre-confirmed, user can bulk-approve all
- **Yellow (fuzzy match or alias match with lower confidence):** requires individual confirmation
- **Red (no match):** user must either pick an existing material from a dropdown or create a new one

For "create new": a minimal inline form prefills from the parsed line (name, unit, price, supplier). Submitting creates the material record and the alias simultaneously.

### Step 4 — Bulk Confirm

User clicks "Zatwierdź wszystkie dopasowania" to confirm green matches. Yellow items require individual clicks. Red items must be resolved first.

### Step 5 — Save as Arrivals

Once all items are confirmed, "Eksportuj do magazynu" creates `arrivals` rows for all confirmed matches, linked to the invoice by `invoice_id` FK. Stock quantities update automatically as the sum of arrivals.

### Step 6 — Price History Update

On each confirmed arrival, the system writes a `price_history` row: material, supplier, invoice, price, date, source = "invoice_import".

### Step 7 — Invoice Status → EXPORTED

The invoice is marked `status = EXPORTED`. Any future scan of the same PDF detects the payload hash match and skips it.

---

## 17. Recommended Build Order

### Priority 1 — Must build now

**1a. PDF upload endpoint with line-item extraction**  
What: `POST /invoices/upload` — accepts PDF file, calls existing `invoice_pdf_import_service.parse_invoice()`, stores result to `invoice_documents` + `invoice_line_items`.  
Why: Without this, no automated invoice flow is possible. The existing Python service already does the parsing; this is mostly wiring.  
Complexity: **low** (the parsing code exists; connect it to a new FastAPI route)

**1b. Invoice deduplication on `POST /db/invoices`**  
What: Add `payload_hash` column + `ON CONFLICT DO NOTHING` or pre-check before INSERT.  
Why: The current code silently doubles VAT amounts in the tax summary if an invoice is saved twice.  
Complexity: **low** (one migration + one SQL change)

**1c. `invoice_line_items` table and API**  
What: New SQLite table + `GET /invoices/{id}/line-items` endpoint.  
Why: Without stored line items, the review UI cannot be built and the invoice-to-material flow has nothing to display.  
Complexity: **medium** (schema migration, migration script for existing data, new endpoint)

**1d. Invoice line-item review page**  
What: New web page at `/invoices/{id}/review` — shows line items with match status and confirm/edit/create actions.  
Why: Without review, any auto-match is applied blindly. Mistakes cannot be caught before stock is updated.  
Complexity: **medium** (new route, review table component, match status display)

---

### Priority 2 — Should build next

**2a. `suppliers` master table + API**  
What: New table + CRUD endpoints + dropdown in material/arrival forms.  
Why: Without a supplier table, supplier attribution is unreliable free text across three separate tables.  
Complexity: **low**

**2b. `material_aliases` table + alias matching in lookup**  
What: New table + update `get_material_by_name` to check aliases before returning "no match".  
Why: Prevents the primary cause of duplicate material creation from invoice import.  
Complexity: **medium** (table + updated query + UI to add/view aliases)

**2c. Activate `price_history` — write on every price event**  
What: Add INSERT to `price_history` in `createArrival`, `updateMaterial` (price field), and invoice import handler.  
Why: The table is designed and ready. It just needs writes. Enables all price-trend features downstream.  
Complexity: **low** (add 3–4 INSERT statements in existing handlers)

**2d. FK between `arrivals` and `invoice_documents`**  
What: Add `invoice_id` column to `arrivals` table; wire it during invoice review confirmation step.  
Why: Creates a real audit trail from invoice → line item → arrival → stock change.  
Complexity: **medium** (schema migration + update arrival creation in review flow)

**2e. Average price and supplier price endpoints**  
What: `GET /materials/{id}/price-history` returning all `price_history` rows for a material; warehouse UI column showing average.  
Why: Average price by supplier is a core business metric that is currently computable but unexposed.  
Complexity: **low** (query already possible from `arrivals` or `price_history` once 2c is done)

---

### Priority 3 — Later improvements

**3a. `supplier_material_links` table (SKU mapping)**  
What: New table mapping `(supplier_id, supplier_sku)` → `material_id`. Update matching logic to check SKU before name.  
Why: The correct long-term solution. Eliminates name matching entirely for known suppliers and their product codes.  
Complexity: **high** (new table, UI for entering SKU mappings, update matching pipeline)

**3b. Fuzzy name matching with confidence score**  
What: Add `rapidfuzz` or similar library; during invoice review, compute similarity between raw line name and all material names; show top matches with score.  
Why: Alias table handles known variants; fuzzy matching catches new ones before they become duplicates.  
Complexity: **medium**

**3c. OCR in web path (connect Tesseract to upload endpoint)**  
What: Make Tesseract path configurable via env var; call it from `POST /invoices/upload` when pypdf text is too short.  
Why: Paper-scanned invoices currently return empty results with no error.  
Complexity: **medium** (Tesseract must be on server path; add env var config)

**3d. Enable GPT-4o-mini via settings**  
What: Add `OPENAI_API_KEY` and `TECH_MODUL_INVOICE_AI_FALLBACK` to the settings UI; expose toggle to enable/disable.  
Why: The AI fallback already works in desktop code; exposing it improves parsing quality for unknown supplier formats with no new development.  
Complexity: **low** (env var + toggle in a settings page)

**3e. Unify desktop and web material stores**  
What: Migrate `MaterialStoreJson` (desktop) to use SQLite `materials` table directly, or build a sync script.  
Why: As long as both stores exist independently, any desktop invoice import creates data that the web cannot see.  
Complexity: **high** (requires testing all desktop material logic with SQLite backend)

---

## 18. Open Questions

1. **Who uploads invoices — the owner at a desk, or an assistant on a tablet?** This determines whether the upload should be a browser file picker, a folder watcher, or an email integration trigger.

2. **Should the review step be optional or mandatory?** For high-confidence matches (exact name, known supplier SKU), skipping review is reasonable. For low-confidence matches, review is essential. A configurable threshold would serve both cases.

3. **What is the authoritative price for a material?** Is it the last invoice price? The average? A manually set catalog price? The system needs a clear answer to know what `price_per_m2` means and when to update it.

4. **Should the desktop and web share the same SQLite database going forward?** If yes, the desktop material store (`baza_materialu.json`) must be migrated. If no, a sync mechanism must be defined, which adds ongoing maintenance.

5. **Are there suppliers whose PDFs are consistently in image format (scanned paper)?** If yes, Tesseract OCR (Priority 3c) should be moved to Priority 1 for those suppliers.

6. **Should "create new material" during invoice review be allowed freely, or should it require approval?** Allowing free creation risks proliferating duplicates. An approval queue would slow down the flow.

---

## 19. Plain-language Summary for Owner

### What we already have

The web warehouse page works well for daily use. You can see all your materials in a table, check which ones are running low, record when goods arrive (with price and invoice number), and edit any material's details directly in the browser. This part is solid.

### Why invoice data differs from clean material records

When you scan invoices on the web, the system reads only five things from each PDF: the invoice number, the date, the supplier tax ID, the net total, and the gross total. It reads nothing else — not which boards, not how many, not at what price per sheet.

So after the scan, you know the invoice total but you have no line items. To update your stock, you must open the warehouse page and type in every delivery by hand — material by material, quantity by quantity. This manual re-entry is where data gets lost or entered differently from how it appears in the invoice.

On top of this, your desktop computer has a much smarter import system that actually reads line items (with OCR and optional AI). But the data it creates is stored in a separate file that the web cannot see. The desktop and the web each keep their own version of your material catalog, and the two versions slowly diverge.

There is also a design gap: the database has a price history table already built — it just has never been connected to anything. Every time a price changes, the old price disappears without being recorded.

### What to fix first

**The most urgent fix is adding real line-item extraction to the web.** Right now the scanner reads totals. It needs to read the lines. The code to do this already exists in the desktop — it just needs to be connected to the web. This single change unlocks everything else: automatic stock updates, price tracking, and the ability to review and confirm matches before anything is written.

**Second most urgent is fixing the double-save bug.** If the same invoice gets saved twice, the VAT balance on your finance dashboard becomes wrong. This is a one-day fix.

**Third is building the review page.** After the system extracts line items, you need a screen where you see each line, confirm what material it matches, and approve before any stock is updated. This protects you from extraction errors.

With these three changes, the invoice import will work end to end — from PDF to updated stock — with a human review step in between. Everything else (aliases, supplier codes, AI improvements) builds on top of this foundation.