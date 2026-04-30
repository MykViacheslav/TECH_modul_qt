from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def new_service_id() -> str:
    return str(uuid.uuid4())[:8].upper()


@dataclass
class ServiceDef:
    """Usługa w cenniku."""
    service_id: str = ""
    name: str = ""
    price: float = 0.0
    duration_min: int = 0
    category: str = ""
    description: str = ""
    deadline: str = ""
    created_at: str = ""
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "service_id": self.service_id,
            "name": self.name,
            "price": self.price,
            "duration_min": self.duration_min,
            "category": self.category,
            "description": self.description,
            "deadline": self.deadline,
            "created_at": self.created_at,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ServiceDef":
        if not isinstance(data, dict):
            data = {}
        return cls(
            service_id=str(data.get("service_id", "") or "") or new_service_id(),
            name=str(data.get("name", "") or ""),
            price=float(data.get("price", 0.0) or 0.0),
            duration_min=int(data.get("duration_min", 0) or 0),
            category=str(data.get("category", "") or ""),
            description=str(data.get("description", "") or ""),
            deadline=str(data.get("deadline", "") or ""),
            created_at=str(data.get("created_at", "") or ""),
            note=str(data.get("note", "") or ""),
        )


# Service types
SERVICE_TYPES = (
    "wycinanie_oklejanie",
    "fronty_surowe",
    "lakierowanie",
    "giete_elementy",
    "blaty_kerrock",
    "inne",
)

SERVICE_TYPE_LABELS = {
    "wycinanie_oklejanie": "Wycinanie i oklejanie",
    "fronty_surowe": "Fronty surowe",
    "lakierowanie": "Lakierowanie",
    "giete_elementy": "Gięte elementy",
    "blaty_kerrock": "Blaty z kerrock",
    "inne": "Inne usługi",
}

SERVICE_STATUS = (
    "nowe",
    "wycena",
    "przyjete",
    "w_trakcie",
    "gotowe",
    "wydane",
    "anulowane",
)

SERVICE_STATUS_LABELS = {
    "nowe": "Nowe",
    "wycena": "Do wyceny",
    "przyjete": "Przyjęte",
    "w_trakcie": "W trakcie",
    "gotowe": "Gotowe",
    "wydane": "Wydane",
    "anulowane": "Anulowane",
}


@dataclass
class ServiceItemDef:
    """Pojedyncza pozycja/formatka w zleceniu."""
    item_id: str = ""
    name: str = ""
    material: str = ""
    width_mm: float = 0.0
    height_mm: float = 0.0
    quantity: int = 1
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "name": self.name,
            "material": self.material,
            "width_mm": float(self.width_mm or 0.0),
            "height_mm": float(self.height_mm or 0.0),
            "quantity": int(self.quantity or 1),
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ServiceItemDef":
        data = data or {}
        return cls(
            item_id=str(data.get("item_id", "") or ""),
            name=str(data.get("name", "") or ""),
            material=str(data.get("material", "") or ""),
            width_mm=float(data.get("width_mm", 0.0) or 0.0),
            height_mm=float(data.get("height_mm", 0.0) or 0.0),
            quantity=int(data.get("quantity", 1) or 1),
            notes=str(data.get("notes", "") or ""),
        )


@dataclass
class ServiceComponentDef:
    """
    Legacy-compatible komponent uslugi (material/praca/usluga).
    Utrzymany ze wzgledow kompatybilnosci testow i store JSON.
    """
    component_id: str = ""
    service_id: str = ""
    component_type: str = ""  # material | work | service
    ref_id: str = ""
    name: str = ""
    quantity: float = 0.0
    unit: str = ""
    estimated_cost: float = 0.0
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_id": str(self.component_id or ""),
            "service_id": str(self.service_id or ""),
            "component_type": str(self.component_type or ""),
            "ref_id": str(self.ref_id or ""),
            "name": str(self.name or ""),
            "quantity": float(self.quantity or 0.0),
            "unit": str(self.unit or ""),
            "estimated_cost": float(self.estimated_cost or 0.0),
            "note": str(self.note or ""),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ServiceComponentDef":
        data = data or {}
        return cls(
            component_id=str(data.get("component_id", "") or ""),
            service_id=str(data.get("service_id", "") or ""),
            component_type=str(data.get("component_type", "") or ""),
            ref_id=str(data.get("ref_id", "") or ""),
            name=str(data.get("name", "") or ""),
            quantity=float(data.get("quantity", 0.0) or 0.0),
            unit=str(data.get("unit", "") or ""),
            estimated_cost=float(data.get("estimated_cost", 0.0) or 0.0),
            note=str(data.get("note", "") or ""),
        )


@dataclass
class ServiceOrderDef:
    """Zlecenie usługowe."""
    service_id: str = ""
    order_number: str = ""
    client_name: str = ""
    client_phone: str = ""
    client_email: str = ""
    service_type: str = "inne"
    status: str = "nowe"
    date_received: str = ""
    date_deadline: str = ""
    date_completed: str = ""
    items: List[ServiceItemDef] = field(default_factory=list)
    
    # Wycena
    price_base: float = 0.0
    price_transport: float = 0.0
    price_extra: float = 0.0
    price_total: float = 0.0
    margin_percent: float = 0.0
    price_final: float = 0.0
    
    # Notatki
    notes: str = ""
    internal_notes: str = ""
    
    # Pliki
    source_file: str = ""
    
    # Historia
    status_history: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "service_id": self.service_id,
            "order_number": self.order_number,
            "client_name": self.client_name,
            "client_phone": self.client_phone,
            "client_email": self.client_email,
            "service_type": self.service_type,
            "status": self.status,
            "date_received": self.date_received,
            "date_deadline": self.date_deadline,
            "date_completed": self.date_completed,
            "items": [item.to_dict() for item in self.items],
            "price_base": float(self.price_base or 0.0),
            "price_transport": float(self.price_transport or 0.0),
            "price_extra": float(self.price_extra or 0.0),
            "price_total": float(self.price_total or 0.0),
            "margin_percent": float(self.margin_percent or 0.0),
            "price_final": float(self.price_final or 0.0),
            "notes": self.notes,
            "internal_notes": self.internal_notes,
            "source_file": self.source_file,
            "status_history": [dict(h) for h in self.status_history],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ServiceOrderDef":
        data = data or {}
        items_raw = data.get("items", []) or []
        history_raw = data.get("status_history", []) or []
        return cls(
            service_id=str(data.get("service_id", "") or ""),
            order_number=str(data.get("order_number", "") or ""),
            client_name=str(data.get("client_name", "") or ""),
            client_phone=str(data.get("client_phone", "") or ""),
            client_email=str(data.get("client_email", "") or ""),
            service_type=str(data.get("service_type", "inne") or "inne"),
            status=str(data.get("status", "nowe") or "nowe"),
            date_received=str(data.get("date_received", "") or ""),
            date_deadline=str(data.get("date_deadline", "") or ""),
            date_completed=str(data.get("date_completed", "") or ""),
            items=[ServiceItemDef.from_dict(item) for item in items_raw if isinstance(item, dict)],
            price_base=float(data.get("price_base", 0.0) or 0.0),
            price_transport=float(data.get("price_transport", 0.0) or 0.0),
            price_extra=float(data.get("price_extra", 0.0) or 0.0),
            price_total=float(data.get("price_total", 0.0) or 0.0),
            margin_percent=float(data.get("margin_percent", 0.0) or 0.0),
            price_final=float(data.get("price_final", 0.0) or 0.0),
            notes=str(data.get("notes", "") or ""),
            internal_notes=str(data.get("internal_notes", "") or ""),
            source_file=str(data.get("source_file", "") or ""),
            status_history=[dict(h) for h in history_raw if isinstance(h, dict)],
        )
