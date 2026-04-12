# Checkpoint — Komplet (after Step 35)

Date: 2026-04-11
Status: STABLE BASELINE

---

## Accepted runtime

- **Live class**: `TabSciana` (in `src/tabs/sciana/tab_sciana.py`)
- Registry wires "Komplet" to `TabSciana`; separate from the "Sciana" path (TabScianaLayout)
- No import errors on instantiation

---

## Left zone

Old monolithic `box_setup` (QGroupBox with all fields in one form) replaced with lighter structure:

| Element | Kind | Content | Startup |
|---|---|---|---|
| `blk_identity` | CollapsibleBlock | Nazwa, Powiazana sciana + refresh, Klient, Zamowienie, Pracownik | **open** |
| `_store_frame` | flat QFrame | Zapisz / Wczytaj / Nadpisz + Wróc do zamówienia + lab_store_status | always visible |
| `block_materials` | CollapsibleBlock | material selection (unchanged) | per its own default |
| `block_store` | CollapsibleBlock | saved layout library (unchanged) | per its own default |

`box_setup = None` — the old QGroupBox is gone; attribute kept as `None` for compat.

6 advanced field widgets (sp_width, sp_height, sp_depth, sp_gap, cb_profile, chk_force_hardware)
kept as hidden `self.*` attributes (`.hide()`) for signal connections; not shown in any form.

---

## Center zone

Quick-actions bar (`self.quick_actions_bar`) is a QWidget with a QVBoxLayout containing 2 rows:

- **Row 1**: Zapisz | Nadpisz | Wczytaj | Nowy + stretch
- **Row 2**: Szukaj | Duplikuj | Snap | Skroty | (Więcej — hidden) + stretch

All buttons: `setMinimumHeight(32)`, `setMaximumHeight(32)`.

---

## Right zone

Module action buttons split from a single overloaded QHBoxLayout into 2 rows:

- **Row 1**: W lewo (btn_move_up) | W prawo (btn_move_down) | Duplikuj + stretch
- **Row 2**: Wyr. lewo | Wyr. prawo | Wyr. góra | Wyr. dół | Dystryb. | Usuń + stretch

`tbl_items` (QTableWidget) present above the button rows.

---

## Regression protection

Script: `_regression_check.py` (project root)
Checks: **124 / 124**

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
12. Komplet: TabSciana instantiation, box_setup=None, blk_identity, identity/store/advanced attrs, quick_actions_bar, 8 quick-action buttons, tbl_items, 9 module action buttons, block_materials, block_store

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

`src\tabs\sciana\tab_sciana.py`

Do not re-introduce `box_setup` as a QGroupBox or restore the monolithic form layout
without updating the regression script. Do not remove the 6 hidden advanced field attrs
(sp_width, sp_height, sp_depth, sp_gap, cb_profile, chk_force_hardware) — they have signal connections.
