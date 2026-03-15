from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from src.domain.module_models import ModuleDef


def normalize_assembly_offset_ref_mode(raw_mode: str) -> str:
    mode = str(raw_mode or "").strip().lower()
    if mode in {"previous", "prev", "previous_module", "module"}:
        return "previous_module"
    return "wall_left"


@dataclass
class AssemblyModuleItemDef:
    source_name: str = ""
    instance_name: str = ""
    offset_ref_mode: str = "wall_left"
    offset_mm: float = 0.0
    position_y_mm: float | None = None
    wall_depth_offset_mm: float = 0.0
    module: ModuleDef = field(default_factory=ModuleDef)

    def display_name(self) -> str:
        return str(self.instance_name or getattr(self.module, "name", "") or self.source_name or "Modul").strip() or "Modul"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_name": self.source_name,
            "instance_name": self.instance_name,
            "offset_ref_mode": normalize_assembly_offset_ref_mode(self.offset_ref_mode),
            "offset_mm": float(self.offset_mm),
            "position_y_mm": None if self.position_y_mm is None else float(self.position_y_mm),
            "wall_depth_offset_mm": float(self.wall_depth_offset_mm),
            "module": self.module.to_dict() if hasattr(self.module, "to_dict") else {},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AssemblyModuleItemDef":
        data = data or {}
        raw_module = data.get("module") or {}
        if isinstance(raw_module, ModuleDef):
            module = raw_module
        else:
            module = ModuleDef.from_dict(raw_module) if isinstance(raw_module, dict) else ModuleDef()

        return cls(
            source_name=str(data.get("source_name", "") or ""),
            instance_name=str(data.get("instance_name", "") or ""),
            offset_ref_mode=normalize_assembly_offset_ref_mode(data.get("offset_ref_mode", "previous_module")),
            offset_mm=float(data.get("offset_mm", 0.0) or 0.0),
            position_y_mm=(
                None
                if data.get("position_y_mm", None) in (None, "")
                else float(data.get("position_y_mm", 0.0) or 0.0)
            ),
            wall_depth_offset_mm=float(data.get("wall_depth_offset_mm", 0.0) or 0.0),
            module=module,
        )


@dataclass
class FurnitureAssemblyDef:
    name: str = "Komplet 1"
    wall_name: str = ""
    client_name: str = ""
    order_name: str = ""
    worker_name: str = ""
    width_mm: float = 3000.0
    height_mm: float = 2500.0
    depth_mm: float = 560.0
    gap_mm: float = 0.0
    material_profile_key: str = "STD_WHITE"
    force_hardware_from_profile: bool = True
    material_overrides: Dict[str, str] = field(default_factory=dict)
    items: List[AssemblyModuleItemDef] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "wall_name": self.wall_name,
            "client_name": self.client_name,
            "order_name": self.order_name,
            "worker_name": self.worker_name,
            "width_mm": float(self.width_mm),
            "height_mm": float(self.height_mm),
            "depth_mm": float(self.depth_mm),
            "gap_mm": float(self.gap_mm),
            "material_profile_key": self.material_profile_key,
            "force_hardware_from_profile": bool(self.force_hardware_from_profile),
            "material_overrides": {
                str(key): str(value)
                for key, value in dict(self.material_overrides or {}).items()
                if str(value or "").strip()
            },
            "items": [item.to_dict() for item in (self.items or [])],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FurnitureAssemblyDef":
        data = data or {}
        raw_items = data.get("items") or []
        items: List[AssemblyModuleItemDef] = []
        if isinstance(raw_items, list):
            for raw_item in raw_items:
                if isinstance(raw_item, AssemblyModuleItemDef):
                    items.append(raw_item)
                elif isinstance(raw_item, dict):
                    items.append(AssemblyModuleItemDef.from_dict(raw_item))

        return cls(
            name=str(data.get("name", "Komplet 1") or "Komplet 1"),
            wall_name=str(data.get("wall_name", "") or ""),
            client_name=str(data.get("client_name", "") or ""),
            order_name=str(data.get("order_name", "") or ""),
            worker_name=str(data.get("worker_name", "") or ""),
            width_mm=float(data.get("width_mm", 3000.0) or 3000.0),
            height_mm=float(data.get("height_mm", 2500.0) or 2500.0),
            depth_mm=float(data.get("depth_mm", 560.0) or 560.0),
            gap_mm=float(data.get("gap_mm", 0.0) or 0.0),
            material_profile_key=str(data.get("material_profile_key", "STD_WHITE") or "STD_WHITE"),
            force_hardware_from_profile=bool(data.get("force_hardware_from_profile", True)),
            material_overrides={
                str(key): str(value)
                for key, value in dict(data.get("material_overrides") or {}).items()
                if str(value or "").strip()
            },
            items=items,
        )
