# Checkpoint — Nowe Zamowienie (after Step 20)

Date: 2026-04-11
Status: STABLE BASELINE

---

## Accepted state

### Top navigation
- 5-tab QTabWidget is the primary navigation: Klient / Zamowienie / Pozycje do wyceny / Zalaczniki / Podsumowanie
- Tab bar is always visible (not hidden via CSS)
- Primary CollapsibleBlock toggle headers are hidden inside each page (no duplicate section titles)

### N1 — Klient
- Client identity + address in a two-panel horizontal splitter
- No rogue inner tab widget

### N2 — Zamowienie
- 7 milestone date fields in a 3-column QGridLayout:
  Wycena | Projekt | Probki materialow
  Zakup materialow | Produkcja | Montaz
  Poprawki
- "Historia statusow" uses lightweight inline disclosure style (no heavy beige box)
- Status history table, filter, and calendar button logic unchanged

### N3 — Pozycje do wyceny
- Quote items table + entry panel + actions panel
- Walls section below
- No changes in this checkpoint cycle

### N4 — Zalaczniki (changed in Steps 18-19)
- Top add-controls strip (full width): file picker, type, description, add/remove
- Horizontal QSplitter workspace:
  - Left (35%): attachment table (tbl_architect_attachments)
  - Right (65%): page thumbnail list + crop canvas + fragment controls
- No nested _make_work_panel bordered box around preview area
- All fragment controls present: target kind, target name, description, save, clear

### N5 — Podsumowanie
- Summary block + local action buttons
- No changes in this checkpoint cycle

---

## Regression protection

Script: `_regression_check.py` (project root)
Checks: 54 / 54

Categories protected:
- Tab bar structure and labels
- CollapsibleBlock header visibility
- N1-N5 hint label visibility
- No legacy hero/subtitle labels
- No rogue internal QTabWidget
- N2: exactly 7 QDateEdit milestone fields, named and typed
- N2: "Terminy projektu" section header label present
- Step pages registered (client/order/quote/attachments/summary)
- N4: QSplitter(Horizontal) present in step_attachments_page
- N4: splitter has 2 panels
- N4: left panel contains tbl_architect_attachments
- N4: right panel contains lst_architect_pages and architect_crop_preview
- N4: preview widgets NOT direct children of grp_architect (old vertical-stack guard)
- N4: all 5 fragment control attributes present

### Run regression check
```
cd C:\PythonProject\TECH_modul
.venv\Scripts\python.exe _regression_check.py
```
Exit 0 = all pass. Screenshots saved to `_regression_screenshots\`.

### Launch app
```
cd C:\PythonProject\TECH_modul
.venv\Scripts\python.exe src\app\main.py
```

---

## Working file

`src\tabs\zamowienie\tab_nowe_zamowienie.py`

Do not introduce large collapsible bars, nested work panels, or single-column
vertical stacks in the attachments area without updating the regression script.
