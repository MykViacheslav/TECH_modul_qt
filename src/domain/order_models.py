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
        if not path:
            continue
        result.append(
            {
                "path": path,
                "kind": kind or "PDF",
                "description": description,
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


@dataclass
class OrderDef:
    code: str = ""
    client_name: str = ""
    worker_name: str = ""
    status: str = "Nowe"
    site_address: str = ""
    notes: str = ""
    attachments: List[Dict[str, str]] = field(default_factory=list)
    quote_items: List[Dict[str, str]] = field(default_factory=list)
    material_choices: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "client_name": self.client_name,
            "worker_name": self.worker_name,
            "status": self.status,
            "site_address": self.site_address,
            "notes": self.notes,
            "attachments": _normalize_attachments(self.attachments),
            "quote_items": _normalize_quote_items(self.quote_items),
            "material_choices": _normalize_material_choices(self.material_choices),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OrderDef":
        data = data or {}
        return cls(
            code=str(data.get("code", "") or ""),
            client_name=str(data.get("client_name", "") or ""),
            worker_name=str(data.get("worker_name", "") or ""),
            status=str(data.get("status", "Nowe") or "Nowe"),
            site_address=str(data.get("site_address", "") or ""),
            notes=str(data.get("notes", "") or ""),
            attachments=_normalize_attachments(data.get("attachments", [])),
            quote_items=_normalize_quote_items(data.get("quote_items", [])),
            material_choices=_normalize_material_choices(data.get("material_choices", [])),
        )
