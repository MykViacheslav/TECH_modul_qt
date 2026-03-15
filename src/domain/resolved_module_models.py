from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class ResolvedModuleDomainState:
    module_name: str = "MOD_TEST_1"

    module_family_key: str = "kitchen_lower"
    material_profile_key: str = "STD_WHITE"

    cabinet_kind: str = "lower"
    ref_point: str = "LBB"

    width_mm: float = 820.0
    depth_mm: float = 500.0
    height_mm: float = 700.0

    inherit_height_from_wall: bool = False
    inherit_depth_from_wall: bool = False
    inherit_materials_from_group: bool = False
    inherit_edgeband_from_group: bool = False

    materials: Dict[str, str] = field(default_factory=dict)
    edgebands: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "module_name": self.module_name,
            "module_family_key": self.module_family_key,
            "material_profile_key": self.material_profile_key,
            "cabinet_kind": self.cabinet_kind,
            "ref_point": self.ref_point,
            "width_mm": float(self.width_mm),
            "depth_mm": float(self.depth_mm),
            "height_mm": float(self.height_mm),
            "inherit_height_from_wall": bool(self.inherit_height_from_wall),
            "inherit_depth_from_wall": bool(self.inherit_depth_from_wall),
            "inherit_materials_from_group": bool(self.inherit_materials_from_group),
            "inherit_edgeband_from_group": bool(self.inherit_edgeband_from_group),
            "materials": dict(self.materials or {}),
            "edgebands": dict(self.edgebands or {}),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResolvedModuleDomainState":
        data = data or {}

        return cls(
            module_name=str(data.get("module_name", "MOD_TEST_1") or "MOD_TEST_1"),
            module_family_key=str(data.get("module_family_key", "kitchen_lower") or "kitchen_lower"),
            material_profile_key=str(data.get("material_profile_key", "STD_WHITE") or "STD_WHITE"),
            cabinet_kind=str(data.get("cabinet_kind", "lower") or "lower"),
            ref_point=str(data.get("ref_point", "LBB") or "LBB"),
            width_mm=float(data.get("width_mm", 820.0) or 820.0),
            depth_mm=float(data.get("depth_mm", 500.0) or 500.0),
            height_mm=float(data.get("height_mm", 700.0) or 700.0),
            inherit_height_from_wall=bool(data.get("inherit_height_from_wall", False)),
            inherit_depth_from_wall=bool(data.get("inherit_depth_from_wall", False)),
            inherit_materials_from_group=bool(data.get("inherit_materials_from_group", False)),
            inherit_edgeband_from_group=bool(data.get("inherit_edgeband_from_group", False)),
            materials={str(k): str(v) for k, v in (data.get("materials", {}) or {}).items()},
            edgebands={str(k): str(v) for k, v in (data.get("edgebands", {}) or {}).items()},
        )