"""
Test: Komplet shopping-list export derives order_id from the order store.

Before the fix (Step 39), _on_send_to_shopping_list() did:
    order_id = str(getattr(self._assembly, "order_id", "") or "")
FurnitureAssemblyDef has no order_id field, so this always returned "".

After the fix, it derives order_id via:
    order_name -> self._order_store.get(order_name) -> order_def.order_id
"""
import pytest

from src.domain.assembly_models import FurnitureAssemblyDef
from src.domain.order_models import OrderDef
from src.storage.order_store_json import OrderStoreJson


# ---------------------------------------------------------------------------
# Part 1 — confirm the OLD path was always broken
# ---------------------------------------------------------------------------

def test_assembly_has_no_order_id_field():
    """FurnitureAssemblyDef must NOT have an order_id attribute.
    If it gains one in the future, this test signals that the lookup
    logic in _on_send_to_shopping_list must be re-evaluated."""
    assembly = FurnitureAssemblyDef(name="K1", order_name="ORD-X")
    assert not hasattr(assembly, "order_id"), (
        "FurnitureAssemblyDef gained an order_id field. "
        "Review _on_send_to_shopping_list: the getattr fallback "
        "may now return a stale or wrong value."
    )


def test_old_getattr_path_returns_empty():
    """The pre-fix getattr call always produces '' for any assembly."""
    assembly = FurnitureAssemblyDef(name="K1", order_name="ORD-99")
    result = str(getattr(assembly, "order_id", "") or "")
    assert result == "", (
        "Expected '' from the old broken path; got something else."
    )


# ---------------------------------------------------------------------------
# Part 2 — confirm the NEW lookup logic returns the real order_id
# ---------------------------------------------------------------------------

def test_order_id_derived_from_order_store(tmp_path):
    """The fixed lookup reads order_name from the assembly,
    fetches the order from the store, and returns its real order_id."""
    order_store = OrderStoreJson(path=tmp_path / "orders.json")

    # Save an order — the store auto-assigns order_id on save
    result = order_store.save_new(
        OrderDef(
            code="ORD-500",
            client_name="Test Klient",
            worker_name="Test Worker",
            status="Nowe",
        )
    )
    assert result.ok

    saved_order = order_store.get("ORD-500")
    assert saved_order is not None
    real_order_id = str(saved_order.order_id or "").strip()
    assert real_order_id, "Order store must assign a non-empty order_id on save"

    # Assembly knows its order by name only (no order_id field)
    assembly = FurnitureAssemblyDef(name="Komplet Test", order_name="ORD-500")

    # --- replicate the fixed lookup from _on_send_to_shopping_list ---
    _order_name = str(getattr(assembly, "order_name", "") or "").strip()
    order_id = ""
    if _order_name:
        _order_def = order_store.get(_order_name)
        if _order_def is not None:
            order_id = str(getattr(_order_def, "order_id", "") or "").strip()
    # ------------------------------------------------------------------

    assert order_id == real_order_id, (
        f"Expected order_id={real_order_id!r} from live lookup, got {order_id!r}"
    )


def test_order_id_empty_when_order_not_in_store(tmp_path):
    """If the order_name does not exist in the store, order_id stays ''."""
    order_store = OrderStoreJson(path=tmp_path / "orders.json")
    assembly = FurnitureAssemblyDef(name="Komplet Missing", order_name="ORD-NONEXISTENT")

    _order_name = str(getattr(assembly, "order_name", "") or "").strip()
    order_id = ""
    if _order_name:
        _order_def = order_store.get(_order_name)
        if _order_def is not None:
            order_id = str(getattr(_order_def, "order_id", "") or "").strip()

    assert order_id == "", "Must fall back to '' when order is not found"


def test_order_id_empty_when_assembly_has_no_order_name(tmp_path):
    """If the assembly has no order_name, order_id stays ''."""
    order_store = OrderStoreJson(path=tmp_path / "orders.json")
    assembly = FurnitureAssemblyDef(name="Komplet Blank")  # order_name=""

    _order_name = str(getattr(assembly, "order_name", "") or "").strip()
    order_id = ""
    if _order_name:
        _order_def = order_store.get(_order_name)
        if _order_def is not None:
            order_id = str(getattr(_order_def, "order_id", "") or "").strip()

    assert order_id == "", "Must fall back to '' when assembly has no order_name"
