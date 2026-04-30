from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from .types import OperationMode, utc_now_iso


@dataclass(frozen=True)
class OperationRequest:
    action: str
    target: Dict[str, Any]
    params: Dict[str, Any] = field(default_factory=dict)
    mode: OperationMode = "preview"
    source: str = "unknown"
    requested_at: str = field(default_factory=utc_now_iso)

