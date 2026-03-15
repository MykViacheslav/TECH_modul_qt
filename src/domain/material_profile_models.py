from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class MaterialProfileDef:
    # Identity
    key: str = "STD_WHITE"
    name_pl: str = "Standard bialy"

    # Material / edgeband maps by logical module part:
    # side, top, bottom, back, shelf, divider, front
    material_map: Dict[str, str] = field(default_factory=dict)
    edgeband_map: Dict[str, str] = field(default_factory=dict)
    hardware_vendor_map: Dict[str, str] = field(default_factory=dict)

    # Description
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "name_pl": self.name_pl,
            "material_map": dict(self.material_map or {}),
            "edgeband_map": dict(self.edgeband_map or {}),
            "hardware_vendor_map": dict(self.hardware_vendor_map or {}),
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MaterialProfileDef":
        data = data or {}

        return cls(
            key=str(data.get("key", "STD_WHITE") or "STD_WHITE"),
            name_pl=str(data.get("name_pl", "Standard bialy") or "Standard bialy"),
            material_map={
                str(k): str(v)
                for k, v in (data.get("material_map", {}) or {}).items()
            },
            edgeband_map={
                str(k): str(v)
                for k, v in (data.get("edgeband_map", {}) or {}).items()
            },
            hardware_vendor_map={
                str(k): str(v)
                for k, v in (data.get("hardware_vendor_map", {}) or {}).items()
            },
            description=str(data.get("description", "") or ""),
        )
