# Checkpoint — Flow: Nowe zamówienie → Ściana → Komplet

Date: 2026-04-12
Status: STABLE BASELINE

---

## Runtime files / classes

| Tab | Class | File |
|---|---|---|
| Nowe zamówienie | `TabNoweZamowienie` | `src/tabs/zamowienie/tab_nowe_zamowienie.py` |
| Ściana | `TabScianaLayout` | `src/tabs/sciana/tab_sciana_layout.py` |
| Komplet | `TabSciana` | `src/tabs/sciana/tab_sciana.py` |
| Cross-tab wiring | `wire_cross_tab_signals` | `src/app/main_window_wiring.py` |
| Dispatch | `_open_new_wall`, `_open_new_assembly` | `src/app/main_window.py` |

Domain models: `WallLayoutDef` (`src/domain/wall_models.py`), `FurnitureAssemblyDef` (`src/domain/assembly_models.py`), `OrderDef` (`src/domain/order_models.py`)

---

## Accepted handoff path

### Nowe zamówienie → Ściana

```
_on_go_to_sciana()
  sig_open_sciana_requested.emit(current_order_context())
    MainWindow._open_new_wall(context)
      TabScianaLayout.start_new_wall_from_order_context(context)

_open_selected_quote_item("sciana")          # from a selected quote item
  sig_open_sciana_requested.emit(payload)    # payload = order_context + quote_item fields
```

**Context dict keys:** `client_name`, `order_id`, `order_name`, `worker_name`, `order_status`,
`order_notes`, `site_address`, `site_*`, `quote_item_name`, `quote_item_kind`,
`quote_item_description`, `quote_item_quantity`

**Written into `WallLayoutDef`:** `name` (from quote_item_name), `client_name`, `order_name`,
`worker_name`, `quote_item_name/kind/reference`, `notes` (built from order context), `photos`
(loaded from order architect attachments)

**Not written to wall:** dimensions (always start at defaults); `order_id` is transient in
`self._order_id_context` only — re-derived from order store via `order_name` on every refresh

### Ściana → Komplet

```
_on_go_to_komplet()          # wall must be saved first
  sig_open_komplet_requested.emit(_context_payload_from_wall(wall))
    MainWindow._open_new_assembly(context)
      TabSciana.start_new_assembly_from_wall_context(context)
```

**Context dict keys (from `_context_payload_from_wall`):** `wall_name`, `client_name`,
`order_name`, `order_id` (live lookup), `worker_name`, `order_status`, `site_address`,
`quote_item_name/kind/reference`, `measurements_count`, `measurements_linear_total_mm`,
`width_mm`, `height_mm`, `depth_mm`

**Written into `FurnitureAssemblyDef`:** `name`, `wall_name`, `client_name`, `order_name`,
`worker_name`, `width_mm`, `height_mm`, `depth_mm`

**Wall link:** Komplet canvas calls `_linked_wall_for_assembly()` to re-read the saved wall at
draw time — plinth guides, clearance zones, obstacle overlays all resolved live from the wall store

---

## Confirmed correct propagation

| Field | Path | Status |
|---|---|---|
| `client_name` | NZ → Ściana → Komplet | solid |
| `order_name` | NZ → Ściana → Komplet | solid |
| `worker_name` | NZ → Ściana → Komplet | solid |
| `quote_item_name` → display name | NZ → Ściana → Komplet | solid |
| `width_mm` | Ściana → Komplet (front side) | solid |
| `height_mm` | Ściana → Komplet (room height) | solid |
| `depth_mm` | Ściana → Komplet (base depth) | solid — key present in payload (Step 37) |
| `wall_name` link | Ściana → Komplet | solid — wall must be saved first |
| `order_id` in shopping list export | via order store lookup at export time | fixed (Step 39) |

---

## Existing protections

| Protection | File | What it covers |
|---|---|---|
| `CHECKPOINT_nowe_zamowienie.md` | project root | Nowe zamówienie UI baseline |
| `CHECKPOINT_sciana.md` | project root | Ściana UI baseline (TabScianaLayout) |
| `CHECKPOINT_komplet.md` | project root | Komplet UI baseline (TabSciana) |
| `_regression_check.py` (124/124) | project root | All three tabs: structure, visibility, identity attrs, signals |
| `tests/test_komplet_shopping_list_order_id.py` | tests/ | order_id lookup logic: happy path + 3 edge cases |

---

## Intentionally not addressed

- `order_id` is not persisted on `WallLayoutDef` or `FurnitureAssemblyDef` — by design;
  `order_name` is the stable join key and `order_id` is re-derived from the order store as needed
- Direct Nowe zamówienie → Komplet path (skipping Ściana): assembly starts with default dims
  (3000×2500×560) — acceptable; no wall link exists until the user selects one
- No dimension pre-fill from order context into Ściana: wall always starts at defaults
  (4000×2600×2600 mm); user sets actual measurements in the Ściana tab
- No automated test for the full Qt-level tab-switch handoff; existing regression check covers
  structural integrity offscreen; a full E2E test would require a live order + wall + assembly chain
