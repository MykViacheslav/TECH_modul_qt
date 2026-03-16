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
        if not name:
            continue
        result.append(
            {
                "name": name,
                "kind": kind or "Inne",
                "description": description,
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


def _normalize_customer_payments(raw: Any) -> List[Dict[str, Any]]:
    items = raw if isinstance(raw, list) else []
    result: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        stage = str(item.get("stage", "") or "").strip()
        amount = float(item.get("amount", 0.0) or 0.0)
        paid = bool(item.get("paid", False))
        note = str(item.get("note", "") or "").strip()
        if not stage and abs(amount) <= 0.0001 and not note:
            continue
        result.append(
            {
                "stage": stage or "Inne",
                "amount": amount,
                "paid": paid,
                "note": note,
            }
        )
    return result


@dataclass
class OrderDef:
    code: str = ""
    client_name: str = ""
    worker_name: str = ""
    status: str = "Nowe"
    progress_percent: float = 0.0
    calendar_stage: str = ""
    calendar_date: str = ""
    calendar_note: str = ""
    site_address: str = ""
    notes: str = ""
    attachments: List[Dict[str, str]] = field(default_factory=list)
    quote_items: List[Dict[str, str]] = field(default_factory=list)
    material_choices: List[Dict[str, str]] = field(default_factory=list)
    status_history: List[Dict[str, str]] = field(default_factory=list)
    customer_payments: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "client_name": self.client_name,
            "worker_name": self.worker_name,
            "status": self.status,
            "progress_percent": float(self.progress_percent),
            "calendar_stage": self.calendar_stage,
            "calendar_date": self.calendar_date,
            "calendar_note": self.calendar_note,
            "site_address": self.site_address,
            "notes": self.notes,
            "attachments": _normalize_attachments(self.attachments),
            "quote_items": _normalize_quote_items(self.quote_items),
            "material_choices": _normalize_material_choices(self.material_choices),
            "status_history": _normalize_status_history(self.status_history),
            "customer_payments": _normalize_customer_payments(self.customer_payments),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OrderDef":
        data = data or {}
        return cls(
            code=str(data.get("code", "") or ""),
            client_name=str(data.get("client_name", "") or ""),
            worker_name=str(data.get("worker_name", "") or ""),
            status=str(data.get("status", "Nowe") or "Nowe"),
            progress_percent=float(data.get("progress_percent", 0.0) or 0.0),
            calendar_stage=str(data.get("calendar_stage", "") or ""),
            calendar_date=str(data.get("calendar_date", "") or ""),
            calendar_note=str(data.get("calendar_note", "") or ""),
            site_address=str(data.get("site_address", "") or ""),
            notes=str(data.get("notes", "") or ""),
            attachments=_normalize_attachments(data.get("attachments", [])),
            quote_items=_normalize_quote_items(data.get("quote_items", [])),
            material_choices=_normalize_material_choices(data.get("material_choices", [])),
            status_history=_normalize_status_history(data.get("status_history", [])),
            customer_payments=_normalize_customer_payments(data.get("customer_payments", [])),
        )
