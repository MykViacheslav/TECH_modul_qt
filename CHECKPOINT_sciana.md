# Checkpoint — Sciana (after Step 28)

Date: 2026-04-11
Status: STABLE BASELINE

---

## Accepted runtime

- **Live class**: `TabScianaLayout` (in `src/tabs/sciana/tab_sciana_layout.py`)
- Registry wires "sciana" to `TabScianaLayout`; the old `TabSciana` fallback is bypassed
- No import errors; `WallMeasurementDef` is present in `src/domain/wall_models.py`

---

## Left zone

Split from one monolithic `blk_main` (24-row QFormLayout) into two lighter blocks:

| Block | Title | Content | Startup |
|---|---|---|---|
| `blk_identity` | "Sciana: Podstawowe" | Nazwa, Klient, Zamowienie, ID, Pracownik, Typ ukladu, Widok z przodu, Wyspa | **open** |
| `blk_dims` | "Wymiary i offsets" | Sciana A/B/C, Wysokosc, Glebokosc, Cokol, Odstep, 4 offsets, 4 island fields | **collapsed** |

Followed by:
- `blk_store` — "Zapis i przejscie": Zapisz / Wczytaj / Nadpisz + nav buttons (open)
- `blk_obstacles` — "Przeszkody": obstacle form + table (open)
- `blk_photos` — "Zdjecia miejsca": photo path + table (collapsed)
- `blk_measurements` — "Pomiary (MVP)": measurement form + table (open)
- `blk_notes` — "Notatki": QTextEdit (collapsed)

`_layout_form` points to the QFormLayout inside `blk_dims` (used by `_set_form_row_visible` for wall_b / wall_c / island row visibility).

---

## Center zone

- Two canvas views stacked in a vertical splitter (front view top, top view bottom)
- Quick-actions bar above the canvases, split into **2 rows**:
  - Row 1: Zapisz | Nadpisz | Wczytaj | Nowa sciana
  - Row 2: Focusuj nazwe | Zamowienie | Dalej → | Skroty
- Buttons 32px height

---

## Right zone

Reduced from 5 same-weight CollapsibleBlocks to 3 blocks + 1 flat note:

| Element | Kind | Content | Startup |
|---|---|---|---|
| `blk_summary` | CollapsibleBlock | `lab_summary` (wall text) + divider + "Pomieszczenie" sub-header + `lab_room_info` | **open** |
| `blk_collisions` | CollapsibleBlock | `lab_collisions` (warnings, 11px) | **open** |
| `blk_obstacle_details` | CollapsibleBlock | `lab_obstacle_details` | **collapsed** |
| flat hint | QFrame + QLabel | "Dalsze parametry" static text (muted gray, 11px) | always visible |

`blk_room` is `None` (merged into `blk_summary`).
`blk_suggestions` is `None` (replaced with flat `QFrame` hint; `lab_suggestions` attribute kept).

---

## Debug zone labels

Technical labels ("PARAMETRY", "SCIANA KONSTRUKTORSKA", "PODSUMOWANIE") were removed in Step 23. Not re-introduced.

---

## Regression protection

Script: `_regression_check.py` (project root)
Checks: **84 / 84**

Sections protected:
1. Tab bar structure and labels (Nowe Zamowienie)
2. CollapsibleBlock header visibility
3. N1-N5 hint label visibility
4. No legacy hero/subtitle labels
5. No rogue internal QTabWidget
6. N2: exactly 7 QDateEdit milestone fields
7. Step pages registered
8. N4: horizontal split (list left | preview+crop right)
9. Sciana runtime resolves to TabScianaLayout + domain model integrity
10. Sciana left-zone split (blk_identity open, blk_dims collapsed, _layout_form in dims)
11. Sciana right-zone cleanup (blk_summary+room merged, blk_collisions open, blk_obstacle_details collapsed, blk_suggestions flat)

### Run regression check
```
cd C:\PythonProject\TECH_modul
.venv\Scripts\python.exe _regression_check.py
```
Exit 0 = all pass. Screenshots saved to `_regression_screenshots\`.

### Launch app
```
cd C:\PythonProject\TECH_modul
.\.venv\Scripts\python.exe src\app\main.py
```

---

## Working file

`src\tabs\sciana\tab_sciana_layout.py`

Do not re-introduce `blk_main`, `blk_room`, or `blk_suggestions` as CollapsibleBlocks without
updating the regression script. Do not collapse blk_identity or expand blk_dims by default.
