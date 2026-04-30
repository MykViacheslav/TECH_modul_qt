from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


def _normalize_attachments(raw: Any) -> List[Dict[str, str]]:
    items = raw if isinstance(raw, list) else []
    result: List[Dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path", "") or "").strip()
        kind = str(item.get("kind", "") or "").strip()
        description = str(item.get("description", "") or "").strip()
        target_kind = str(item.get("target_kind", "") or "").strip()
        target_name = str(item.get("target_name", "") or "").strip()
        source_path = str(item.get("source_path", "") or "").strip()
        source_page = str(item.get("source_page", "") or "").strip()
        source_app = str(item.get("source_app", "") or "").strip()
        if not path:
            continue
        result.append(
            {
                "path": path,
                "kind": kind or "PDF",
                "description": description,
                "target_kind": target_kind,
                "target_name": target_name,
                "source_path": source_path,
                "source_page": source_page,
                "source_app": source_app,
            }
        )
    return result


def _normalize_quote_items(raw: Any) -> List[Dict[str, str]]:
    items = raw if isinstance(raw, list) else []
    result: List[Dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "") or "").strip()
        kind = str(item.get("kind", "") or "").strip()
        description = str(item.get("description", "") or "").strip()
        try:
            quantity = int(float(item.get("quantity", item.get("qty", 1)) or 1))
        except Exception:
            quantity = 1
        quantity = max(1, quantity)
        if not name:
            continue
        result.append(
            {
                "name": name,
                "kind": kind or "Inne",
                "description": description,
                "quantity": str(quantity),
            }
        )
    return result


def _normalize_material_choices(raw: Any) -> List[Dict[str, str]]:
    items = raw if isinstance(raw, list) else []
    result: List[Dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        scope = str(item.get("scope", "") or "").strip()
        material = str(item.get("material", "") or "").strip()
        color = str(item.get("color", "") or "").strip()
        code = str(item.get("code", "") or "").strip()
        status = str(item.get("status", "") or "").strip()
        notes = str(item.get("notes", "") or "").strip()
        if not any((scope, material, color, code, status, notes)):
            continue
        result.append(
            {
                "scope": scope or "Inne",
                "material": material,
                "color": color,
                "code": code,
                "status": status or "Probka pokazana",
                "notes": notes,
            }
        )
    return result


def _normalize_status_history(raw: Any) -> List[Dict[str, str]]:
    items = raw if isinstance(raw, list) else []
    result: List[Dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        changed_at = str(item.get("changed_at", "") or "").strip()
        from_status = str(item.get("from_status", "") or "").strip()
        to_status = str(item.get("to_status", "") or "").strip()
        changed_by = str(item.get("changed_by", "") or "").strip()
        note = str(item.get("note", "") or "").strip()
        if not to_status and not changed_at:
            continue
        result.append(
            {
                "changed_at": changed_at,
                "from_status": from_status,
                "to_status": to_status,
                "changed_by": changed_by,
                "note": note,
            }
        )
    return result



def _normalize_schedule(raw: Any) -> List[Dict[str, str]]:
    items = raw if isinstance(raw, list) else []
    result: List[Dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        stage = str(item.get("stage", "") or "").strip()
        date_from = str(item.get("date_from", "") or "").strip()
        date_to = str(item.get("date_to", "") or "").strip()
        note = str(item.get("note", "") or "").strip()
        if not stage and not date_from:
            continue
        result.append(
            {
                "stage": stage,
                "date_from": date_from,
                "date_to": date_to,
                "note": note,
            }
        )
    return result


def _normalize_customer_payments(raw: Any) -> List[Dict[str, Any]]:
    items = raw if isinstance(raw, list) else []
    result: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        stage = str(item.get("stage", "") or "").strip()
        amount = float(item.get("amount", 0.0) or 0.0)
        paid = bool(item.get("paid", False))
        account_type = str(item.get("account_type", "bank") or "bank").strip().lower()
        if not stage and abs(amount) <= 0.0001 and not note:
            continue
        result.append(
            {
                "stage": stage or "Inne",
                "amount": amount,
                "paid": paid,
                "note": note,
                "account_type": account_type,
            }
        )
    return result


@dataclass
class OrderDef:
    id: str = ""
    code: str = ""
    order_name: str = ""
    order_id: str = ""
    client_name: str = ""
    worker_name: str = ""
    status: str = "Nowe"
    progress_percent: float = 0.0
    calendar_stage: str = ""
    calendar_date: str = ""
    calendar_note: str = ""
    site_address: str = ""
    site_street: str = ""
    site_house_number: str = ""
    site_apartment_number: str = ""
    site_postal_code: str = ""
    site_city: str = ""
    notes: str = ""
    date_wycena: str = ""
    date_produkcja: str = ""
    date_zakup_mat: str = ""
    date_montaz: str = ""
    date_poprawki: str = ""
    date_projekt: str = ""
    date_probki: str = ""
    date_wycena_end: str = ""
    date_produkcja_end: str = ""
    date_zakup_mat_end: str = ""
    date_montaz_end: str = ""
    date_poprawki_end: str = ""
    date_projekt_end: str = ""
    date_probki_end: str = ""
    attachments: List[Dict[str, str]] = field(default_factory=list)
    quote_items: List[Dict[str, str]] = field(default_factory=list)
    material_choices: List[Dict[str, str]] = field(default_factory=list)
    status_history: List[Dict[str, str]] = field(default_factory=list)
    schedule: List[Dict[str, str]] = field(default_factory=list)
    customer_payments: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "code": self.code,
            "order_name": self.order_name,
            "order_id": self.order_id,
            "client_name": self.client_name,
            "worker_name": self.worker_name,
            "status": self.status,
            "progress_percent": float(self.progress_percent),
            "calendar_stage": self.calendar_stage,
            "calendar_date": self.calendar_date,
            "calendar_note": self.calendar_note,
            "site_address": self.site_address,
            "site_street": self.site_street,
            "site_house_number": self.site_house_number,
            "site_apartment_number": self.site_apartment_number,
            "site_postal_code": self.site_postal_code,
            "site_city": self.site_city,
            "notes": self.notes,
            "date_wycena": self.date_wycena,
            "date_produkcja": self.date_produkcja,
            "date_zakup_mat": self.date_zakup_mat,
            "date_montaz": self.date_montaz,
            "date_poprawki": self.date_poprawki,
            "date_projekt": self.date_projekt,
            "date_probki": self.date_probki,
            "date_wycena_end": self.date_wycena_end,
            "date_produkcja_end": self.date_produkcja_end,
            "date_zakup_mat_end": self.date_zakup_mat_end,
            "date_montaz_end": self.date_montaz_end,
            "date_poprawki_end": self.date_poprawki_end,
            "date_projekt_end": self.date_projekt_end,
            "date_probki_end": self.date_probki_end,
            "attachments": _normalize_attachments(self.attachments),
            "quote_items": _normalize_quote_items(self.quote_items),
            "material_choices": _normalize_material_choices(self.material_choices),
            "status_history": _normalize_status_history(self.status_history),
            "schedule": _normalize_schedule(self.schedule),
            "customer_payments": _normalize_customer_payments(self.customer_payments),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OrderDef":
        data = data or {}
        raw_id = str(data.get("id", "") or "")
        raw_order_id = str(data.get("order_id", "") or "")
        return cls(
            id=raw_id or raw_order_id,
            code=str(data.get("code", "") or ""),
            order_name=str(data.get("order_name", "") or ""),
            order_id=raw_order_id or raw_id,
            client_name=str(data.get("client_name", "") or ""),
            worker_name=str(data.get("worker_name", "") or ""),
            status=str(data.get("status", "Nowe") or "Nowe"),
            progress_percent=float(data.get("progress_percent", 0.0) or 0.0),
            calendar_stage=str(data.get("calendar_stage", "") or ""),
            calendar_date=str(data.get("calendar_date", "") or ""),
            calendar_note=str(data.get("calendar_note", "") or ""),
            site_address=str(data.get("site_address", "") or ""),
            site_street=str(data.get("site_street", "") or ""),
            site_house_number=str(data.get("site_house_number", "") or ""),
            site_apartment_number=str(data.get("site_apartment_number", "") or ""),
            site_postal_code=str(data.get("site_postal_code", "") or ""),
            site_city=str(data.get("site_city", "") or ""),
            notes=str(data.get("notes", "") or ""),
            date_wycena=str(data.get("date_wycena", "") or ""),
            date_produkcja=str(data.get("date_produkcja", "") or ""),
            date_zakup_mat=str(data.get("date_zakup_mat", "") or ""),
            date_montaz=str(data.get("date_montaz", "") or ""),
            date_poprawki=str(data.get("date_poprawki", "") or ""),
            date_projekt=str(data.get("date_projekt", "") or ""),
            date_probki=str(data.get("date_probki", "") or ""),
            date_wycena_end=str(data.get("date_wycena_end", "") or ""),
            date_produkcja_end=str(data.get("date_produkcja_end", "") or ""),
            date_zakup_mat_end=str(data.get("date_zakup_mat_end", "") or ""),
            date_montaz_end=str(data.get("date_montaz_end", "") or ""),
            date_poprawki_end=str(data.get("date_poprawki_end", "") or ""),
            date_projekt_end=str(data.get("date_projekt_end", "") or ""),
            date_probki_end=str(data.get("date_probki_end", "") or ""),
            attachments=_normalize_attachments(data.get("attachments", [])),
            quote_items=_normalize_quote_items(data.get("quote_items", [])),
            material_choices=_normalize_material_choices(data.get("material_choices", [])),
            status_history=_normalize_status_history(data.get("status_history", [])),
            schedule=_normalize_schedule(data.get("schedule", [])),
            customer_payments=_normalize_customer_payments(data.get("customer_payments", [])),
            created_at=str(data.get("created_at", "") or ""),
            updated_at=str(data.get("updated_at", "") or ""),
        )
