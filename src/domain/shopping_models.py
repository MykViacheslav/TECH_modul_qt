from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def new_shopping_id() -> str:
    return str(uuid.uuid4())[:8].upper()


@dataclass
class ShoppingItemDef:
    """Pozycja na liście zakupów."""
    item_id: str = ""
    material_id: str = ""
    material_name: str = ""
    quantity_needed: float = 0.0
    unit: str = ""
    added_date: str = ""
    status: str = "do kupienia"  # do kupienia, zamówiono, zakupiono
    supplier: str = ""
    price_estimate: float = 0.0
    price_actual: float = 0.0
    notes: str = ""
    last_updated: str = ""
    # Powiązanie z projektem / zamówieniem
    project_name: str = ""
    order_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "material_id": self.material_id,
            "material_name": self.material_name,
            "quantity_needed": float(self.quantity_needed or 0.0),
            "unit": self.unit,
            "added_date": self.added_date,
            "status": self.status,
            "supplier": self.supplier,
            "price_estimate": float(self.price_estimate or 0.0),
            "price_actual": float(self.price_actual or 0.0),
            "notes": self.notes,
            "last_updated": self.last_updated,
            "project_name": self.project_name,
            "order_id": self.order_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ShoppingItemDef":
        data = data or {}
        return cls(
            item_id=str(data.get("item_id", "") or "") or new_shopping_id(),
            material_id=str(data.get("material_id", "") or ""),
            material_name=str(data.get("material_name", "") or ""),
            quantity_needed=float(data.get("quantity_needed", 0.0) or 0.0),
            unit=str(data.get("unit", "") or ""),
            added_date=str(data.get("added_date", "") or ""),
            status=str(data.get("status", "do kupienia") or "do kupienia"),
            supplier=str(data.get("supplier", "") or ""),
            price_estimate=float(data.get("price_estimate", 0.0) or 0.0),
            price_actual=float(data.get("price_actual", 0.0) or 0.0),
            notes=str(data.get("notes", "") or ""),
            last_updated=str(data.get("last_updated", "") or ""),
            project_name=str(data.get("project_name", "") or ""),
            order_id=str(data.get("order_id", "") or ""),
        )
