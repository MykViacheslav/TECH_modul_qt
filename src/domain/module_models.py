from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Dict, Any

from src.domain.module_base_group import default_module_base_group_for_family, normalize_module_base_group


def new_module_id() -> str:
    return str(uuid.uuid4())[:8].upper()


PartKey = str
MaterialKey = str
EdgeSide = str
EdgeBandKey = str


MODULE_TYPE_KEYS = {
    "legacy",
    "hanging",
    "legs",
    "legs_plinth",
    "corner",
}


def normalize_module_type(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in MODULE_TYPE_KEYS:
        return normalized
    return "legacy"


def module_type_to_cabinet_kind(module_type: str, fallback_kind: str = "lower") -> str:
    normalized_type = normalize_module_type(module_type)
    if normalized_type == "hanging":
        return "upper"
    if normalized_type in ("legs", "legs_plinth", "corner"):
        return "lower"

    fallback = str(fallback_kind or "lower").strip().lower()
    if fallback in ("upper", "lower"):
        return fallback
    return "lower"


SHELF_MOUNT_KEYS = {"left", "right", "both"}


def normalize_shelf_mount(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in SHELF_MOUNT_KEYS:
        return normalized
    return "right"


@dataclass
class PartDef:
    key: PartKey
    name_pl: str
    material_key: MaterialKey = ""
    dims_mm: Dict[str, float] = field(default_factory=dict)
    edge_banding: Dict[EdgeSide, EdgeBandKey] = field(default_factory=dict)
    material_override_key: MaterialKey = ""

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "name_pl": self.name_pl,
            "material_key": self.material_key,
            "material_override_key": self.material_override_key,
            "dims_mm": dict(self.dims_mm),
            "edge_banding": dict(self.edge_banding),
        }

    @staticmethod
    def from_dict(d: dict) -> "PartDef":
        return PartDef(
            key=str(d.get("key", "")),
            name_pl=str(d.get("name_pl", "")),
            material_key=str(d.get("material_key", "")),
            dims_mm={k: float(v) for k, v in (d.get("dims_mm", {}) or {}).items()},
            edge_banding={k: str(v) for k, v in (d.get("edge_banding", {}) or {}).items()},
            material_override_key=str(d.get("material_override_key", "")),
        )


@dataclass
class ModuleFamilyDef:
    key: str = "kitchen_lower"
    name_pl: str = "Szafka dolna"

    default_cabinet_kind: str = "lower"
    default_ref_point: str = "LBB"

    default_height_mm: float = 720.0
    default_depth_mm: float = 560.0

    default_material_profile_key: str = ""

    allow_inherit_height_from_wall: bool = True
    allow_inherit_depth_from_wall: bool = False
    allow_inherit_materials_from_group: bool = True
    allow_inherit_edgeband_from_group: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "name_pl": self.name_pl,
            "default_cabinet_kind": self.default_cabinet_kind,
            "default_ref_point": self.default_ref_point,
            "default_height_mm": float(self.default_height_mm),
            "default_depth_mm": float(self.default_depth_mm),
            "default_material_profile_key": self.default_material_profile_key,
            "allow_inherit_height_from_wall": bool(self.allow_inherit_height_from_wall),
            "allow_inherit_depth_from_wall": bool(self.allow_inherit_depth_from_wall),
            "allow_inherit_materials_from_group": bool(self.allow_inherit_materials_from_group),
            "allow_inherit_edgeband_from_group": bool(self.allow_inherit_edgeband_from_group),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModuleFamilyDef":
        data = data or {}

        return cls(
            key=str(data.get("key", "kitchen_lower") or "kitchen_lower"),
            name_pl=str(data.get("name_pl", "Szafka dolna") or "Szafka dolna"),
            default_cabinet_kind=str(data.get("default_cabinet_kind", "lower") or "lower"),
            default_ref_point=str(data.get("default_ref_point", "LBB") or "LBB"),
            default_height_mm=float(data.get("default_height_mm", 720.0) or 720.0),
            default_depth_mm=float(data.get("default_depth_mm", 560.0) or 560.0),
            default_material_profile_key=str(data.get("default_material_profile_key", "") or ""),
            allow_inherit_height_from_wall=bool(data.get("allow_inherit_height_from_wall", True)),
            allow_inherit_depth_from_wall=bool(data.get("allow_inherit_depth_from_wall", False)),
            allow_inherit_materials_from_group=bool(data.get("allow_inherit_materials_from_group", True)),
            allow_inherit_edgeband_from_group=bool(data.get("allow_inherit_edgeband_from_group", True)),
        )


@dataclass
class ModuleDef:
    module_id: str = ""
    name: str = "MOD_TEST_1"
    base_group: str = ""

    width_mm: float = 820.0
    depth_mm: float = 500.0
    height_mm: float = 700.0

    top_rail_offset_mm: float = 0.0
    bottom_rail_offset_mm: float = 0.0

    carcass_joint_type: str = "type2"

    shelf_count: int = 0
    divider_count: int = 0
    shelf_mount: str = "right"
    module_type: str = "legacy"

    cabinet_kind: str = "lower"
    ref_point: str = "LBB"
    module_family: str = "kitchen_lower"

    visible_parts: set[str] = field(default_factory=set)

    materials: Dict[str, str] = field(default_factory=dict)
    edgebands: Dict[str, str] = field(default_factory=dict)

    material_profile_key: str = ""

    inherit_height_from_wall: bool = False
    inherit_depth_from_wall: bool = False
    inherit_materials_from_group: bool = False
    inherit_edgeband_from_group: bool = False

    front_layout: str = "overlay"

    # region FRONT_ZONE
    front_height_mode: str = "full"  # full | to_top_rail | offsets
    front_offset_top_mm: float = 0.0
    front_offset_bottom_mm: float = 0.0
    # endregion

    facade_mode: str = "doors"
    drawer_count: int = 3
    hinge_vendor: str = "generic"
    drawer_vendor: str = "generic"
    drawer_layout_mode: str = "equal"
    drawer_small_front_height_mm: float = 140.0
    drawer_tip_on: bool = False
    drawer_rear_clearance_mm: float = 10.0
    drawer_tip_on_clearance_mm: float = 20.0
    door_hinge_side: str = "left"

    parts: Dict[str, "PartDef"] = field(default_factory=dict)

    def __post_init__(self) -> None:
        fallback_group = default_module_base_group_for_family(getattr(self, "module_family", ""))
        self.base_group = normalize_module_base_group(getattr(self, "base_group", ""), fallback_key=fallback_group)
        self.module_type = normalize_module_type(getattr(self, "module_type", "legacy"))
        self.shelf_mount = normalize_shelf_mount(getattr(self, "shelf_mount", "right"))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "module_id": self.module_id,
            "name": self.name,
            "base_group": self.base_group,
            "width_mm": float(self.width_mm),
            "depth_mm": float(self.depth_mm),
            "height_mm": float(self.height_mm),
            "top_rail_offset_mm": float(self.top_rail_offset_mm),
            "bottom_rail_offset_mm": float(self.bottom_rail_offset_mm),
            "carcass_joint_type": self.carcass_joint_type,
            "shelf_count": int(self.shelf_count),
            "divider_count": int(self.divider_count),
            "shelf_mount": self.shelf_mount,
            "module_type": self.module_type,
            "cabinet_kind": self.cabinet_kind,
            "ref_point": self.ref_point,
            "module_family": self.module_family,
            "visible_parts": sorted(list(self.visible_parts or set())),
            "materials": dict(self.materials or {}),
            "edgebands": dict(self.edgebands or {}),
            "material_profile_key": self.material_profile_key,
            "inherit_height_from_wall": bool(self.inherit_height_from_wall),
            "inherit_depth_from_wall": bool(self.inherit_depth_from_wall),
            "inherit_materials_from_group": bool(self.inherit_materials_from_group),
            "inherit_edgeband_from_group": bool(self.inherit_edgeband_from_group),
            "front_layout": self.front_layout,
            "facade_mode": self.facade_mode,
            "drawer_count": int(self.drawer_count),
            "hinge_vendor": self.hinge_vendor,
            "drawer_vendor": self.drawer_vendor,
            "drawer_layout_mode": self.drawer_layout_mode,
            "drawer_small_front_height_mm": float(self.drawer_small_front_height_mm),
            "drawer_tip_on": bool(self.drawer_tip_on),
            "drawer_rear_clearance_mm": float(self.drawer_rear_clearance_mm),
            "drawer_tip_on_clearance_mm": float(self.drawer_tip_on_clearance_mm),
            "door_hinge_side": self.door_hinge_side,
            "parts": {
                k: v.to_dict() if hasattr(v, "to_dict") else v
                for k, v in (self.parts or {}).items()
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModuleDef":
        data = data or {}

        raw_parts = data.get("parts") or {}
        parsed_parts: Dict[str, PartDef] = {}

        if isinstance(raw_parts, dict):
            for k, v in raw_parts.items():
                if hasattr(PartDef, "from_dict") and isinstance(v, dict):
                    parsed_parts[str(k)] = PartDef.from_dict(v)
                elif isinstance(v, PartDef):
                    parsed_parts[str(k)] = v

        return cls(
            module_id=str(data.get("module_id", "") or ""),
            name=str(data.get("name", "MOD_TEST_1") or "MOD_TEST_1"),
            base_group=str(data.get("base_group", "") or ""),
            width_mm=float(data.get("width_mm", 820.0) or 820.0),
            depth_mm=float(data.get("depth_mm", 500.0) or 500.0),
            height_mm=float(data.get("height_mm", 700.0) or 700.0),
            top_rail_offset_mm=float(data.get("top_rail_offset_mm", 0.0) or 0.0),
            bottom_rail_offset_mm=float(data.get("bottom_rail_offset_mm", 0.0) or 0.0),
            carcass_joint_type=str(data.get("carcass_joint_type", "type2") or "type2"),
            shelf_count=int(data.get("shelf_count", 0) or 0),
            divider_count=int(data.get("divider_count", 0) or 0),
            shelf_mount=str(data.get("shelf_mount", "right") or "right"),
            module_type=str(data.get("module_type", "legacy") or "legacy"),
            cabinet_kind=str(data.get("cabinet_kind", "lower") or "lower"),
            ref_point=str(data.get("ref_point", "LBB") or "LBB"),
            module_family=str(data.get("module_family", "kitchen_lower") or "kitchen_lower"),
            visible_parts=set(data.get("visible_parts", []) or []),
            materials=dict(data.get("materials", {}) or {}),
            edgebands=dict(data.get("edgebands", {}) or {}),
            material_profile_key=str(data.get("material_profile_key", "") or ""),
            inherit_height_from_wall=bool(data.get("inherit_height_from_wall", False)),
            inherit_depth_from_wall=bool(data.get("inherit_depth_from_wall", False)),
            inherit_materials_from_group=bool(data.get("inherit_materials_from_group", False)),
            inherit_edgeband_from_group=bool(data.get("inherit_edgeband_from_group", False)),
            front_layout=str(data.get("front_layout", "overlay") or "overlay"),
            facade_mode=str(data.get("facade_mode", "doors") or "doors"),
            drawer_count=int(data.get("drawer_count", 3) or 3),
            hinge_vendor=str(data.get("hinge_vendor", "generic") or "generic"),
            drawer_vendor=str(data.get("drawer_vendor", "generic") or "generic"),
            drawer_layout_mode=str(data.get("drawer_layout_mode", "equal") or "equal"),
            drawer_small_front_height_mm=float(data.get("drawer_small_front_height_mm", 140.0) or 140.0),
            drawer_tip_on=bool(data.get("drawer_tip_on", False)),
            drawer_rear_clearance_mm=float(data.get("drawer_rear_clearance_mm", 10.0) or 10.0),
            drawer_tip_on_clearance_mm=float(data.get("drawer_tip_on_clearance_mm", 20.0) or 20.0),
            door_hinge_side=str(data.get("door_hinge_side", "left") or "left"),
            parts=parsed_parts,
        )
