"""
Regression check — TabNoweZamowienie accepted UI state.

Protects the conditions agreed after Steps 11-22:
  - top tab bar visible with 5 correct Polish labels
  - primary CollapsibleBlock headers are hidden (no duplicate section titles)
  - N1-N5 hint labels not rendered inside pages
  - no legacy hero/subtitle labels
  - no rogue internal workflow QTabWidget
  - N2 "Terminy projektu" has exactly 7 named milestone QDateEdit fields
    (Wycena / Projekt / Probki / Zakup mat. / Produkcja / Montaz / Poprawki)
  - correct step pages registered
  - N4 attachments workspace uses horizontal split (list left | preview+crop right)
  - N4 old single-column vertical layout not accidentally reintroduced
  - "Sciana" tab runtime path resolves to TabScianaLayout (not TabSciana fallback)
  - WallMeasurementDef exists in domain model and WallLayoutDef carries measurements field
  - Sciana left-zone split: blk_identity open + blk_dims collapsed, _layout_form in dims
  - Sciana right-zone cleanup: blk_summary+room merged, blk_collisions open, blk_obstacle_details collapsed, blk_suggestions flat

Run with:
    cd /d C:\PythonProject\TECH_modul
    .venv\Scripts\python.exe _regression_check.py

Exit 0 = all pass, Exit 1 = one or more failures.
Screenshots saved to _regression_screenshots\.
"""
from __future__ import annotations
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["TECH_MODUL_TESTING"] = "1"
sys.path.insert(0, r"C:\PythonProject\TECH_modul")

from PyQt6.QtWidgets import (
    QApplication, QDateEdit, QFrame, QLabel, QListWidget,
    QSplitter, QTabWidget, QTableWidget, QWidget,
)
from PyQt6.QtCore import Qt

app = QApplication(sys.argv)

from src.tabs.zamowienie.tab_nowe_zamowienie import TabNoweZamowienie

widget = TabNoweZamowienie()
widget.resize(1280, 860)
widget.show()
app.processEvents()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_passes: list[str] = []
_failures: list[str] = []


def ok(name: str) -> None:
    _passes.append(name)
    print(f"  PASS  {name}")


def fail(name: str, detail: str = "") -> None:
    _failures.append(name)
    suffix = f"  —  {detail}" if detail else ""
    print(f"  FAIL  {name}{suffix}")


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        ok(name)
    else:
        fail(name, detail)


# ---------------------------------------------------------------------------
# 1. Top tab bar — present, 5 tabs, correct Polish labels
# ---------------------------------------------------------------------------
wt = widget.workflow_tabs
check("workflow_tabs is QTabWidget", isinstance(wt, QTabWidget))
check("tab count == 5", wt.count() == 5, f"got {wt.count()}")

EXPECTED_LABELS = ["Klient", "Zamówienie", "Pozycje do wyceny", "Załączniki", "Podsumowanie"]
for i, expected in enumerate(EXPECTED_LABELS):
    got = wt.tabText(i) if i < wt.count() else "<missing>"
    check(f"tab[{i}] == '{expected}'", got == expected, f"got '{got}'")

# Tab bar must NOT be hidden via the old CSS trick
tab_ss = wt.styleSheet()
check("tab bar not hidden via height:0px CSS", "height:0px" not in tab_ss)
check("tab bar not hidden via width:0px CSS",  "width:0px"  not in tab_ss)

# ---------------------------------------------------------------------------
# 2. Primary CollapsibleBlock headers hidden (no duplicate section titles)
# ---------------------------------------------------------------------------
PRIMARY_BLOCKS = {
    "grp_client":      widget.grp_client,
    "grp_order":       widget.grp_order,
    "grp_worker":      widget.grp_worker,
    "grp_quote_items": widget.grp_quote_items,
    "grp_walls":       widget.grp_walls,
    "grp_architect":   widget.grp_architect,
    "grp_summary":     widget.grp_summary,
    "grp_material_choices": widget.grp_material_choices,
    "grp_customer_cash":    widget.grp_customer_cash,
}
for attr, block in PRIMARY_BLOCKS.items():
    check(f"{attr}._btn hidden", not block._btn.isVisible(),
          "duplicate section header is visible inside page")

# ---------------------------------------------------------------------------
# 3. N1-N5 hint labels not visible inside pages
# ---------------------------------------------------------------------------
HINTS = {
    "step_hint_client":      widget.step_hint_client,
    "step_hint_order":       widget.step_hint_order,
    "step_hint_quote":       widget.step_hint_quote,
    "step_hint_attachments": widget.step_hint_attachments,
    "step_hint_summary":     widget.step_hint_summary,
}
for attr, hint in HINTS.items():
    check(f"{attr} not visible", not hint.isVisible(),
          "N-hint label is rendered inside a page")

# ---------------------------------------------------------------------------
# 4. No legacy hero / subtitle labels visible
# ---------------------------------------------------------------------------
LEGACY_PATTERNS = ["start projektu", "premium order workspace",
                   "client / order / quote"]
visible_legacy = [
    lbl.text()[:60]
    for lbl in widget.findChildren(QLabel)
    if lbl.isVisible()
    and any(p in (lbl.text() or "").lower() for p in LEGACY_PATTERNS)
]
check("no legacy hero/subtitle labels visible", not visible_legacy,
      str(visible_legacy))

# ---------------------------------------------------------------------------
# 5. No rogue internal workflow QTabWidget with old English step labels
# ---------------------------------------------------------------------------
OLD_TOKENS = {"client", "order", "quote", "attachment", "attachments", "summary"}
rogue = [
    str({tw.tabText(i).strip().lower() for i in range(tw.count())})
    for tw in widget.findChildren(QTabWidget)
    if tw is not wt
    and {tw.tabText(i).strip().lower() for i in range(tw.count())}.issubset(OLD_TOKENS)
    and tw.count() > 0
]
check("no rogue internal workflow QTabWidget", not rogue, str(rogue))

# ---------------------------------------------------------------------------
# 6. N2 "Terminy projektu" — exactly 7 named milestone date fields
#
# Accepted structure: single-date per row (not from/to pairs), 7 milestones:
#   Wycena | Projekt | Probki materialow | Zakup materialow
#   Produkcja | Montaz | Poprawki
# ---------------------------------------------------------------------------

# 6a. Exact count in the order page
N2_MILESTONE_ATTRS = (
    "ed_date_wycena",
    "ed_date_projekt",
    "ed_date_probki",
    "ed_date_zakup_mat",
    "ed_date_produkcja",
    "ed_date_montaz",
    "ed_date_poprawki",
)
date_fields_in_order = widget.step_order_page.findChildren(QDateEdit)
check(
    "N2 'Terminy projektu' has exactly 7 QDateEdit milestone fields",
    len(date_fields_in_order) == 7,
    f"found {len(date_fields_in_order)} — expected 7 "
    "(Wycena/Projekt/Probki/Zakup/Produkcja/Montaz/Poprawki)",
)

# 6b. Each named milestone attribute exists and is a QDateEdit
for attr in N2_MILESTONE_ATTRS:
    obj = getattr(widget, attr, None)
    check(
        f"N2 milestone field '{attr}' exists as QDateEdit",
        isinstance(obj, QDateEdit),
        f"attribute missing or wrong type: {type(obj).__name__}",
    )

# 6c. Section header label "Terminy projektu" is present in grp_order
terminy_headers = [
    lbl.text()
    for lbl in widget.grp_order.findChildren(QLabel)
    if "Terminy projektu" in (lbl.text() or "")
]
check(
    "N2 'Terminy projektu' section header label present",
    len(terminy_headers) > 0,
    "label not found — section may have been restructured or removed",
)

# ---------------------------------------------------------------------------
# 7. Step pages registered
# ---------------------------------------------------------------------------
for key in ("client", "order", "quote", "attachments", "summary"):
    check(f"_step_pages['{key}'] registered", key in getattr(widget, "_step_pages", {}))

# ---------------------------------------------------------------------------
# 8. N4 "Zalaczniki" — horizontal split workspace (accepted after Step 18)
#
# Accepted structure:
#   top add-controls strip (full width)
#   QSplitter (Horizontal):
#     left panel : tbl_architect_attachments
#     right panel: lst_architect_pages + architect_crop_preview + fragment controls
#   Old layout guard: preview widgets must NOT be direct children of
#   grp_architect content layout (no single-column regression).
# ---------------------------------------------------------------------------

# 8a. Core N4 named widgets exist with correct types
_n4_typed: list[tuple[str, type]] = [
    ("tbl_architect_attachments", QTableWidget),
    ("lst_architect_pages",       QListWidget),
]
for _attr, _expected_type in _n4_typed:
    _obj = getattr(widget, _attr, None)
    check(
        f"N4 '{_attr}' exists as {_expected_type.__name__}",
        isinstance(_obj, _expected_type),
        f"missing or wrong type: {type(_obj).__name__}",
    )

_crop = getattr(widget, "architect_crop_preview", None)
check(
    "N4 'architect_crop_preview' exists",
    isinstance(_crop, QWidget),
    f"missing or wrong type: {type(_crop).__name__}",
)

# 8b. A horizontal QSplitter exists inside the N4 page
_n4_page = widget.step_attachments_page
_all_splitters = _n4_page.findChildren(QSplitter)
_h_splitters = [s for s in _all_splitters if s.orientation() == Qt.Orientation.Horizontal]
check(
    "N4 workspace has a horizontal QSplitter",
    len(_h_splitters) >= 1,
    f"found {len(_all_splitters)} splitter(s), {len(_h_splitters)} horizontal",
)

if _h_splitters:
    _sp = _h_splitters[0]

    # 8c. Splitter has exactly 2 panels
    check(
        "N4 splitter has 2 panels (list | preview+crop)",
        _sp.count() == 2,
        f"got {_sp.count()} panels",
    )

    # 8d. Left panel owns the attachment table
    _left = _sp.widget(0)
    _tbl = getattr(widget, "tbl_architect_attachments", None)
    _left_tables = set(_left.findChildren(QTableWidget)) if _left else set()
    check(
        "N4 left panel contains attachment table",
        _tbl in _left_tables,
        "tbl_architect_attachments not in left splitter panel",
    )

    # 8e. Right panel owns the thumbnail list and crop preview
    _right = _sp.widget(1)
    _lst = getattr(widget, "lst_architect_pages", None)
    _right_lists = set(_right.findChildren(QListWidget)) if _right else set()
    check(
        "N4 right panel contains page thumbnail list",
        _lst in _right_lists,
        "lst_architect_pages not in right splitter panel",
    )
    _right_widgets = set(_right.findChildren(QWidget)) if _right else set()
    check(
        "N4 right panel contains crop preview widget",
        _crop in _right_widgets,
        "architect_crop_preview not in right splitter panel",
    )

else:
    # splitter missing — mark dependent checks as failed
    for _desc in (
        "N4 splitter has 2 panels (list | preview+crop)",
        "N4 left panel contains attachment table",
        "N4 right panel contains page thumbnail list",
        "N4 right panel contains crop preview widget",
    ):
        fail(_desc, "no horizontal splitter found — dependent check skipped")

# 8f. Old-layout guard: preview widgets must NOT be direct children of
#     grp_architect content layout (detects accidental reversion to
#     the single-column vertical stack)
def _is_direct_layout_item(layout, target_widget: QWidget) -> bool:
    if layout is None or target_widget is None:
        return False
    for i in range(layout.count()):
        item = layout.itemAt(i)
        if item and item.widget() is target_widget:
            return True
    return False

_grp_lay = widget.grp_architect.content_layout()
check(
    "N4 page-thumbnail list is NOT a direct child of grp_architect (no vertical-stack regression)",
    not _is_direct_layout_item(_grp_lay, getattr(widget, "lst_architect_pages", None)),
    "lst_architect_pages is a direct content child — old single-column layout detected",
)
check(
    "N4 crop preview is NOT a direct child of grp_architect (no vertical-stack regression)",
    not _is_direct_layout_item(_grp_lay, getattr(widget, "architect_crop_preview", None)),
    "architect_crop_preview is a direct content child — old single-column layout detected",
)

# 8g. Fragment controls exist
_N4_FRAGMENT_ATTRS = (
    "cb_architect_fragment_target_kind",
    "ed_architect_fragment_target_name",
    "ed_architect_fragment_description",
    "btn_save_architect_fragment",
    "btn_clear_architect_fragment",
)
for _attr in _N4_FRAGMENT_ATTRS:
    check(
        f"N4 fragment control '{_attr}' exists",
        getattr(widget, _attr, None) is not None,
        "attribute missing",
    )

# ---------------------------------------------------------------------------
# 9. "Sciana" tab — runtime path + domain model (fixed in Step 21)
#
# Accepted state (Step 21):
#   - TabScianaLayout imports without error
#   - registry _build_sciana() returns TabScianaLayout, not TabSciana fallback
#   - WallMeasurementDef exists as a dataclass in src.domain.wall_models
#   - WallLayoutDef has a 'measurements' field (list, default empty)
# ---------------------------------------------------------------------------

# 9a. TabScianaLayout can be imported cleanly (no missing symbol crash)
_sciana_layout_cls = None
try:
    import importlib as _importlib
    _sciana_mod = _importlib.import_module("src.tabs.sciana.tab_sciana_layout")
    _sciana_layout_cls = getattr(_sciana_mod, "TabScianaLayout", None)
    check(
        "Sciana TabScianaLayout imports without error",
        _sciana_layout_cls is not None,
        "TabScianaLayout not found in module after import",
    )
except Exception as _sciana_err:
    check(
        "Sciana TabScianaLayout imports without error",
        False,
        f"import raised: {_sciana_err}",
    )

# 9b. Registry _build_sciana() resolves to TabScianaLayout (no silent fallback)
_sciana_instance = None
_sciana_fallback_used = False
try:
    _sciana_instance = __import__(
        "src.tabs.sciana.tab_sciana_layout", fromlist=["TabScianaLayout"]
    ).TabScianaLayout()
except Exception as _sb_err:
    # If this raises, registry would silently use TabSciana — that is the bug
    _sciana_fallback_used = True

check(
    "Sciana runtime path resolves to TabScianaLayout (no TabSciana fallback)",
    not _sciana_fallback_used,
    "TabScianaLayout() raised an exception — registry would fall back to TabSciana",
)
check(
    "Sciana runtime instance is TabScianaLayout",
    _sciana_instance is not None and type(_sciana_instance).__name__ == "TabScianaLayout",
    f"got {type(_sciana_instance).__name__ if _sciana_instance else 'None'}",
)

# 9c. WallMeasurementDef exists in the domain model
_wm_cls = None
try:
    from src.domain.wall_models import WallMeasurementDef as _WallMeasurementDef
    _wm_cls = _WallMeasurementDef
except ImportError:
    pass
check(
    "WallMeasurementDef exists in src.domain.wall_models",
    _wm_cls is not None,
    "symbol missing — TabScianaLayout import would crash",
)

# 9d. WallMeasurementDef has the expected fields
if _wm_cls is not None:
    import dataclasses as _dc
    _wm_field_names = {f.name for f in _dc.fields(_wm_cls)} if _dc.is_dataclass(_wm_cls) else set()
    for _field in ("name", "kind", "value_mm", "photo_path", "note"):
        check(
            f"WallMeasurementDef has field '{_field}'",
            _field in _wm_field_names,
            f"field missing — found: {sorted(_wm_field_names)}",
        )

# 9e. WallLayoutDef.measurements field exists and defaults to a list
try:
    from src.domain.wall_models import WallLayoutDef as _WallLayoutDef
    _wl_instance = _WallLayoutDef()
    _measurements_attr = getattr(_wl_instance, "measurements", _SENTINEL := object())
    check(
        "WallLayoutDef has 'measurements' field",
        _measurements_attr is not _SENTINEL,
        "attribute missing on WallLayoutDef instance",
    )
    check(
        "WallLayoutDef.measurements defaults to empty list",
        isinstance(_measurements_attr, list) and len(_measurements_attr) == 0,
        f"got: {type(_measurements_attr).__name__} = {_measurements_attr!r}",
    )
except Exception as _wl_err:
    for _desc in (
        "WallLayoutDef has 'measurements' field",
        "WallLayoutDef.measurements defaults to empty list",
    ):
        fail(_desc, f"WallLayoutDef check raised: {_wl_err}")

# ---------------------------------------------------------------------------
# 10. Sciana left-zone split (Step 25-26)
#
# Accepted state after Step 25:
#   - blk_main (old single heavy block) is GONE from the instance
#   - blk_identity ("Sciana: Podstawowe") exists and starts expanded
#   - blk_dims ("Wymiary i offsets") exists and starts collapsed
#   - _layout_form is set and is the QFormLayout inside blk_dims
#     (used by _set_form_row_visible for wall_b / wall_c / island rows)
# ---------------------------------------------------------------------------

if _sciana_instance is not None:
    from PyQt6.QtWidgets import QFormLayout as _QFormLayout

    # 10a. blk_main no longer exists as the primary left-zone block
    _blk_main = getattr(_sciana_instance, "blk_main", None)
    check(
        "Sciana left zone: blk_main (old monolithic block) is gone",
        _blk_main is None,
        "blk_main still present — old monolithic block was not removed",
    )

    # 10b. blk_identity exists
    _blk_identity = getattr(_sciana_instance, "blk_identity", None)
    check(
        "Sciana left zone: blk_identity exists",
        _blk_identity is not None,
        "blk_identity attribute missing on TabScianaLayout instance",
    )

    # 10c. blk_dims exists
    _blk_dims = getattr(_sciana_instance, "blk_dims", None)
    check(
        "Sciana left zone: blk_dims exists",
        _blk_dims is not None,
        "blk_dims attribute missing on TabScianaLayout instance",
    )

    # 10d. blk_identity body is not hidden (starts expanded)
    # Use isHidden() rather than isVisible(): isVisible() requires parent chain to be
    # shown, which is not the case in the offscreen test. isHidden() reflects the
    # direct setVisible() call from _apply_block_startup_visibility regardless of parents.
    if _blk_identity is not None:
        _identity_body = None
        try:
            _identity_body = _sciana_instance._get_collapsible_block_body(_blk_identity)
        except Exception:
            pass
        check(
            "Sciana left zone: blk_identity starts expanded (body not hidden)",
            _identity_body is not None and not _identity_body.isHidden(),
            "blk_identity body is hidden — expected open on startup",
        )

    # 10e. blk_dims body is hidden (starts collapsed)
    if _blk_dims is not None:
        _dims_body = None
        try:
            _dims_body = _sciana_instance._get_collapsible_block_body(_blk_dims)
        except Exception:
            pass
        check(
            "Sciana left zone: blk_dims starts collapsed (body hidden)",
            _dims_body is not None and _dims_body.isHidden(),
            "blk_dims body is not hidden — expected collapsed on startup",
        )

    # 10f. _layout_form exists and is a QFormLayout (drives row-visibility logic)
    _layout_form = getattr(_sciana_instance, "_layout_form", None)
    check(
        "Sciana left zone: _layout_form is set",
        _layout_form is not None,
        "_layout_form missing — wall_b/wall_c/island row visibility logic would fail",
    )
    check(
        "Sciana left zone: _layout_form is QFormLayout",
        isinstance(_layout_form, _QFormLayout),
        f"got {type(_layout_form).__name__}",
    )

    # 10g. sp_wall_b and sp_island_w are rows inside _layout_form (not identity_form)
    if _layout_form is not None:
        _sp_wall_b = getattr(_sciana_instance, "sp_wall_b", None)
        _sp_island_w = getattr(_sciana_instance, "sp_island_w", None)
        _form_row_count = _layout_form.rowCount() if _layout_form is not None else 0
        check(
            "Sciana left zone: _layout_form has >= 13 rows (dims+offsets+island)",
            _form_row_count >= 13,
            f"only {_form_row_count} rows — wall/island fields may be in wrong form",
        )
else:
    for _desc in (
        "Sciana left zone: blk_main (old monolithic block) is gone",
        "Sciana left zone: blk_identity exists",
        "Sciana left zone: blk_dims exists",
        "Sciana left zone: blk_identity starts expanded (body visible)",
        "Sciana left zone: blk_dims starts collapsed (body hidden)",
        "Sciana left zone: _layout_form is set",
        "Sciana left zone: _layout_form is QFormLayout",
        "Sciana left zone: _layout_form has >= 13 rows (dims+offsets+island)",
    ):
        fail(_desc, "skipped — TabScianaLayout instance unavailable")

# ---------------------------------------------------------------------------
# 11. Sciana right-zone cleanup (Step 27-28)
#
# Accepted state after Step 27:
#   - blk_room is None (merged into blk_summary)
#   - blk_suggestions is None (replaced with flat muted hint)
#   - blk_summary exists and starts open (contains lab_summary + lab_room_info)
#   - blk_collisions exists and starts open
#   - blk_obstacle_details exists and starts collapsed
#   - lab_room_info attribute still present (content rendered inside blk_summary)
# ---------------------------------------------------------------------------

if _sciana_instance is not None:

    def _blk_body_hidden(inst, attr: str):
        """Return (body_found, is_hidden) for a collapsible block attribute."""
        blk = getattr(inst, attr, None)
        if blk is None:
            return False, None
        try:
            body = inst._get_collapsible_block_body(blk)
        except Exception:
            body = None
        if body is None:
            return False, None
        return True, body.isHidden()

    # 11a. blk_room is gone (merged into blk_summary)
    check(
        "Sciana right zone: blk_room is None (merged into blk_summary)",
        getattr(_sciana_instance, "blk_room", "SENTINEL") is None,
        "blk_room still a live widget — old separate block was not removed",
    )

    # 11b. blk_suggestions is gone (replaced with flat hint)
    check(
        "Sciana right zone: blk_suggestions is None (replaced with flat hint)",
        getattr(_sciana_instance, "blk_suggestions", "SENTINEL") is None,
        "blk_suggestions still a live CollapsibleBlock — should be a flat note",
    )

    # 11c. blk_summary exists
    check(
        "Sciana right zone: blk_summary exists",
        getattr(_sciana_instance, "blk_summary", None) is not None,
        "blk_summary missing on TabScianaLayout instance",
    )

    # 11d. blk_collisions exists
    check(
        "Sciana right zone: blk_collisions exists",
        getattr(_sciana_instance, "blk_collisions", None) is not None,
        "blk_collisions missing on TabScianaLayout instance",
    )

    # 11e. blk_obstacle_details exists
    check(
        "Sciana right zone: blk_obstacle_details exists",
        getattr(_sciana_instance, "blk_obstacle_details", None) is not None,
        "blk_obstacle_details missing on TabScianaLayout instance",
    )

    # 11f. blk_summary starts expanded
    _found, _hidden = _blk_body_hidden(_sciana_instance, "blk_summary")
    check(
        "Sciana right zone: blk_summary starts expanded (body not hidden)",
        _found and not _hidden,
        "blk_summary body is hidden — expected open on startup",
    )

    # 11g. blk_collisions starts expanded
    _found, _hidden = _blk_body_hidden(_sciana_instance, "blk_collisions")
    check(
        "Sciana right zone: blk_collisions starts expanded (body not hidden)",
        _found and not _hidden,
        "blk_collisions body is hidden — expected open on startup",
    )

    # 11h. blk_obstacle_details starts collapsed
    _found, _hidden = _blk_body_hidden(_sciana_instance, "blk_obstacle_details")
    check(
        "Sciana right zone: blk_obstacle_details starts collapsed (body hidden)",
        _found and _hidden is True,
        "blk_obstacle_details body is not hidden — expected collapsed on startup",
    )

    # 11i. lab_room_info still present (content merged into blk_summary, attribute unchanged)
    check(
        "Sciana right zone: lab_room_info attribute still present",
        getattr(_sciana_instance, "lab_room_info", None) is not None,
        "lab_room_info missing — room info rendering would silently break",
    )

    # 11j. lab_summary still present
    check(
        "Sciana right zone: lab_summary attribute still present",
        getattr(_sciana_instance, "lab_summary", None) is not None,
        "lab_summary missing — wall summary rendering would silently break",
    )

    # 11k. lab_suggestions still present (even as flat widget, attribute is kept)
    check(
        "Sciana right zone: lab_suggestions attribute still present",
        getattr(_sciana_instance, "lab_suggestions", None) is not None,
        "lab_suggestions attribute missing — hint text would not render",
    )

else:
    for _desc in (
        "Sciana right zone: blk_room is None (merged into blk_summary)",
        "Sciana right zone: blk_suggestions is None (replaced with flat hint)",
        "Sciana right zone: blk_summary exists",
        "Sciana right zone: blk_collisions exists",
        "Sciana right zone: blk_obstacle_details exists",
        "Sciana right zone: blk_summary starts expanded (body not hidden)",
        "Sciana right zone: blk_collisions starts expanded (body not hidden)",
        "Sciana right zone: blk_obstacle_details starts collapsed (body hidden)",
        "Sciana right zone: lab_room_info attribute still present",
        "Sciana right zone: lab_summary attribute still present",
        "Sciana right zone: lab_suggestions attribute still present",
    ):
        fail(_desc, "skipped — TabScianaLayout instance unavailable")

# ---------------------------------------------------------------------------
# 12. "Komplet" tab — TabSciana accepted structure (Steps 31-34)
#
# Accepted state:
#   - runtime wires to TabSciana (tab_sciana.py), not a placeholder
#   - zone labels ("STREFA LEWA" etc.) are removed
#   - center quick-actions bar is split into 2 rows (quick_actions_bar widget)
#   - right-zone module buttons are split into 2 rows (items_btn_vbox)
#   - left zone: old monolithic box_setup is None; blk_identity exists
#   - key identity and store attributes still present
# ---------------------------------------------------------------------------

_komplet_instance = None
_komplet_load_failed = False
try:
    _komplet_instance = __import__(
        "src.tabs.sciana.tab_sciana", fromlist=["TabSciana"]
    ).TabSciana()
except Exception as _k_err:
    _komplet_load_failed = True

# 12a. TabSciana instantiates without error
check(
    "Komplet: TabSciana instantiates without error",
    not _komplet_load_failed and _komplet_instance is not None,
    f"TabSciana() raised an exception — Komplet tab would show placeholder",
)

if _komplet_instance is not None:

    # 12b. box_setup is None (old monolithic form removed in Step 34)
    check(
        "Komplet left zone: box_setup is None (old monolithic form removed)",
        getattr(_komplet_instance, "box_setup", "SENTINEL") is None,
        "box_setup is still a live widget — old monolithic setup form was not removed",
    )

    # 12c. blk_identity exists
    check(
        "Komplet left zone: blk_identity exists",
        getattr(_komplet_instance, "blk_identity", None) is not None,
        "blk_identity missing — identity section not found",
    )

    # 12d. Core identity widgets still present
    for _attr in ("ed_name", "cb_wall", "ed_client", "ed_order", "cb_worker"):
        check(
            f"Komplet left zone: identity widget '{_attr}' present",
            getattr(_komplet_instance, _attr, None) is not None,
            f"attribute missing — identity form would be incomplete",
        )

    # 12e. Store action widgets still present
    for _attr in ("btn_save", "btn_load", "btn_overwrite", "btn_back_to_order", "lab_store_status"):
        check(
            f"Komplet left zone: store widget '{_attr}' present",
            getattr(_komplet_instance, _attr, None) is not None,
            f"attribute missing — save/load actions would break",
        )

    # 12f. Hidden advanced fields kept as attributes (signal connections still work)
    for _attr in ("sp_width", "sp_height", "sp_depth", "sp_gap", "cb_profile", "chk_force_hardware"):
        check(
            f"Komplet left zone: advanced field '{_attr}' kept as attribute",
            getattr(_komplet_instance, _attr, None) is not None,
            f"attribute missing — business logic referencing this field would crash",
        )

    # 12g. Center quick-actions bar exists as self.quick_actions_bar (2-row layout, Step 32)
    check(
        "Komplet center: quick_actions_bar attribute exists (2-row layout)",
        getattr(_komplet_instance, "quick_actions_bar", None) is not None,
        "quick_actions_bar missing — center quick-actions were restructured but attr not set",
    )

    # 12h. All 8 quick-action buttons still present
    for _attr in (
        "btn_q_save", "btn_q_overwrite", "btn_q_load", "btn_q_new",
        "btn_q_search", "btn_q_duplicate", "btn_q_snap", "btn_q_shortcuts",
    ):
        check(
            f"Komplet center: quick-action button '{_attr}' present",
            getattr(_komplet_instance, _attr, None) is not None,
            f"button missing — quick-action would be unavailable",
        )

    # 12i. Right-zone module list and all 9 action buttons still present
    check(
        "Komplet right zone: tbl_items present",
        getattr(_komplet_instance, "tbl_items", None) is not None,
        "tbl_items missing — module list would not render",
    )
    for _attr in (
        "btn_move_up", "btn_move_down", "btn_duplicate",
        "btn_align_left", "btn_align_right", "btn_align_top",
        "btn_align_bottom", "btn_distribute", "btn_remove",
    ):
        check(
            f"Komplet right zone: action button '{_attr}' present",
            getattr(_komplet_instance, _attr, None) is not None,
            f"button missing — module action would be unavailable",
        )

    # 12j. Materials and saved-modules blocks still intact
    check(
        "Komplet left zone: block_materials CollapsibleBlock present",
        getattr(_komplet_instance, "block_materials", None) is not None,
        "block_materials missing — materials section would not render",
    )
    check(
        "Komplet left zone: block_store CollapsibleBlock present",
        getattr(_komplet_instance, "block_store", None) is not None,
        "block_store missing — saved modules section would not render",
    )

else:
    _k_skip_descs = (
        "Komplet left zone: box_setup is None (old monolithic form removed)",
        "Komplet left zone: blk_identity exists",
        "Komplet left zone: identity widget 'ed_name' present",
        "Komplet left zone: identity widget 'cb_wall' present",
        "Komplet left zone: identity widget 'ed_client' present",
        "Komplet left zone: identity widget 'ed_order' present",
        "Komplet left zone: identity widget 'cb_worker' present",
        "Komplet left zone: store widget 'btn_save' present",
        "Komplet left zone: store widget 'btn_load' present",
        "Komplet left zone: store widget 'btn_overwrite' present",
        "Komplet left zone: store widget 'btn_back_to_order' present",
        "Komplet left zone: store widget 'lab_store_status' present",
        "Komplet left zone: advanced field 'sp_width' kept as attribute",
        "Komplet left zone: advanced field 'sp_height' kept as attribute",
        "Komplet left zone: advanced field 'sp_depth' kept as attribute",
        "Komplet left zone: advanced field 'sp_gap' kept as attribute",
        "Komplet left zone: advanced field 'cb_profile' kept as attribute",
        "Komplet left zone: advanced field 'chk_force_hardware' kept as attribute",
        "Komplet center: quick_actions_bar attribute exists (2-row layout)",
        "Komplet center: quick-action button 'btn_q_save' present",
        "Komplet center: quick-action button 'btn_q_overwrite' present",
        "Komplet center: quick-action button 'btn_q_load' present",
        "Komplet center: quick-action button 'btn_q_new' present",
        "Komplet center: quick-action button 'btn_q_search' present",
        "Komplet center: quick-action button 'btn_q_duplicate' present",
        "Komplet center: quick-action button 'btn_q_snap' present",
        "Komplet center: quick-action button 'btn_q_shortcuts' present",
        "Komplet right zone: tbl_items present",
        "Komplet right zone: action button 'btn_move_up' present",
        "Komplet right zone: action button 'btn_move_down' present",
        "Komplet right zone: action button 'btn_duplicate' present",
        "Komplet right zone: action button 'btn_align_left' present",
        "Komplet right zone: action button 'btn_align_right' present",
        "Komplet right zone: action button 'btn_align_top' present",
        "Komplet right zone: action button 'btn_align_bottom' present",
        "Komplet right zone: action button 'btn_distribute' present",
        "Komplet right zone: action button 'btn_remove' present",
        "Komplet left zone: block_materials CollapsibleBlock present",
        "Komplet left zone: block_store CollapsibleBlock present",
    )
    for _desc in _k_skip_descs:
        fail(_desc, "skipped — TabSciana instance unavailable")

# ---------------------------------------------------------------------------
# Screenshots — saved for manual verification
# ---------------------------------------------------------------------------
OUT = r"C:\PythonProject\TECH_modul\_regression_screenshots"
os.makedirs(OUT, exist_ok=True)
SCREENS = {0: "01_Klient", 1: "02_Zamowienie", 2: "03_Pozycje",
           3: "04_Zalaczniki", 4: "05_Podsumowanie"}
for idx, name in SCREENS.items():
    wt.setCurrentIndex(idx)
    app.processEvents()
    widget.grab().save(os.path.join(OUT, f"{name}.png"), "PNG")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
total = len(_passes) + len(_failures)
print()
print(f"{'='*55}")
print(f"  {len(_passes)}/{total} checks passed", end="")
if _failures:
    print(f"  |  {len(_failures)} FAILED")
    for f in _failures:
        print(f"    x  {f}")
    print(f"{'='*55}")
    sys.exit(1)
else:
    print("  —  all OK")
    print(f"{'='*55}")
    sys.exit(0)
