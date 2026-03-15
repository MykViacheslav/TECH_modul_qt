from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class OrderDef:
    code: str = ""
    client_name: str = ""
    worker_name: str = ""
    status: str = "Nowe"
    site_address: str = ""
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "client_name": self.client_name,
            "worker_name": self.worker_name,
            "status": self.status,
            "site_address": self.site_address,
            "notes": self.notes,
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
        )
