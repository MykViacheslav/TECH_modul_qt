from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

OperationStatus = Literal["ok", "validation_error", "conflict", "error"]
OperationMode = Literal["preview", "apply"]
ChangeKind = Literal["update", "add", "remove", "reorder"]
TargetType = Literal["module", "assembly", "wall"]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class OperationTarget:
    type: TargetType
    id: str = ""
    name: str = ""
    scope: str = ""

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "type": self.type,
            "id": str(self.id or ""),
            "name": str(self.name or ""),
        }
        if str(self.scope or "").strip():
            out["scope"] = str(self.scope)
        return out


@dataclass(frozen=True)
class OperationError:
    code: str
    message: str
    path: str = ""

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "code": str(self.code or ""),
            "message": str(self.message or ""),
        }
        if str(self.path or "").strip():
            out["path"] = str(self.path)
        return out


@dataclass(frozen=True)
class OperationChange:
    path: str
    label: str
    before: Any
    after: Any
    unit: str = ""
    kind: ChangeKind = "update"
    target_ref: Optional[OperationTarget] = None

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "path": str(self.path or ""),
            "label": str(self.label or ""),
            "before": self.before,
            "after": self.after,
            "unit": str(self.unit or ""),
            "kind": self.kind,
        }
        if self.target_ref is not None:
            out["target_ref"] = self.target_ref.to_dict()
        return out


@dataclass(frozen=True)
class OperationMeta:
    source: str = "unknown"
    requested_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": str(self.source or "unknown"),
            "requested_at": str(self.requested_at or utc_now_iso()),
        }


@dataclass
class OperationResult:
    version: str
    status: OperationStatus
    mode: OperationMode
    action: str
    target: OperationTarget
    warnings: List[str] = field(default_factory=list)
    errors: List[OperationError] = field(default_factory=list)
    changes: List[OperationChange] = field(default_factory=list)
    can_apply: bool = False
    meta: OperationMeta = field(default_factory=OperationMeta)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": str(self.version or "1.0"),
            "status": self.status,
            "mode": self.mode,
            "action": str(self.action or ""),
            "target": self.target.to_dict(),
            "warnings": [str(item) for item in (self.warnings or [])],
            "errors": [item.to_dict() for item in (self.errors or [])],
            "changes": [item.to_dict() for item in (self.changes or [])],
            "can_apply": bool(self.can_apply),
            "meta": self.meta.to_dict(),
        }

