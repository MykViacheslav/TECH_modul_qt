from __future__ import annotations

import collections.abc

GRAIN_VERTICAL = "vertical"
GRAIN_HORIZONTAL = "horizontal"
GRAIN_NONE = "none"

GRAIN_LABELS = {
    GRAIN_VERTICAL: "Pionowo",
    GRAIN_HORIZONTAL: "Poziomo",
    GRAIN_NONE: "Brak / Dowolny"
}

SHELF_MOUNT_KEYS = ["left", "right", "both"]


def default_grain_for_part(part_key: str) -> str:
    """Legacy helper for determining default grain direction by part key."""
    k = str(part_key or "").strip().lower()
    if "front" in k:
        return GRAIN_VERTICAL
    return GRAIN_NONE

import uuid
from enum import Enum
from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Optional, Set, Union


def normalize_module_base_group(key: str, fallback_key: str = "") -> str:
    k = str(key or "").strip()
    return k if k else fallback_key


def default_module_base_group_for_family(family: str) -> str:
    f = str(family or "").strip().lower()
    if "kitchen" in f:
        return "kitchen_lower"
    if "wardrobe" in f:
        return "wardrobe"
    return "general"


def normalize_module_type(m_type: str) -> str:
    t = str(m_type or "legacy").strip().lower()
    if t in ("legacy", "legs", "legs_plinth", "hanging", "corner"):
        return t
    return "legacy"


def normalize_shelf_mount(mount: str) -> str:
    m = str(mount or "right").strip().lower()
    if m in ("left", "right", "both"):
        return m
    return "right"


def new_module_id() -> str:
    return str(uuid.uuid4())


@dataclass(frozen=True)
class ModuleFamilyDef:
    key: str
    name_pl: str
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
    def from_dict(cls, data: Dict[str, Any]) -> ModuleFamilyDef:
        return cls(
            key=str(data.get("key", "") or ""),
            name_pl=str(data.get("name_pl", "") or ""),
            default_cabinet_kind=str(data.get("default_cabinet_kind", "lower") or "lower"),
            default_ref_point=str(data.get("default_ref_point", "LBB") or "LBB"),
            default_height_mm=float(data.get("default_height_mm", 720.0)),
            default_depth_mm=float(data.get("default_depth_mm", 560.0)),
            default_material_profile_key=str(data.get("default_material_profile_key", "") or ""),
            allow_inherit_height_from_wall=bool(data.get("allow_inherit_height_from_wall", True)),
            allow_inherit_depth_from_wall=bool(data.get("allow_inherit_depth_from_wall", False)),
            allow_inherit_materials_from_group=bool(data.get("allow_inherit_materials_from_group", True)),
            allow_inherit_edgeband_from_group=bool(data.get("allow_inherit_edgeband_from_group", True)),
        )


def module_type_to_cabinet_kind(m_type: str, fallback_kind: str = "lower") -> str:
    t = str(m_type or "legacy").strip().lower()
    if t in ("hanging",):
        return "upper"
    if t in ("corner",):
        return "corner"
    return fallback_kind or "lower"


@dataclass
class PartDef:
    id: str
    name_pl: str
    material_key: str = ""
    dims_mm: Dict[str, float] = field(default_factory=dict)
    edge_banding: Dict[str, str] = field(default_factory=dict)
    material_override_key: str = ""
    veneer_active: bool = False
    lacquer_active: bool = False
    grain_direction: str = "none"

    @property
    def key(self) -> str:
        """Legacy access for codebase still using .key instead of .id"""
        return self.id

    def effective_grain(self) -> str:
        return str(self.grain_direction or "none")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "key": self.id,  # Add legacy key to dict
            "name_pl": self.name_pl,
            "material_key": self.material_key,
            "dims_mm": {k: float(v) for k, v in self.dims_mm.items()},
            "edge_banding": dict(self.edge_banding or {}),
            "material_override_key": self.material_override_key,
            "veneer_active": bool(self.veneer_active),
            "lacquer_active": bool(self.lacquer_active),
            "grain_direction": self.grain_direction,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PartDef":
        return cls(
            id=str(data.get("id", data.get("key", "")) or ""), # Support legacy key
            name_pl=str(data.get("name_pl", "") or ""),
            material_key=str(data.get("material_key", "") or ""),
            dims_mm={k: float(v) for k, v in (data.get("dims_mm") or {}).items()},
            edge_banding=dict(data.get("edge_banding") or {}),
            material_override_key=str(data.get("material_override_key", "") or ""),
            veneer_active=bool(data.get("veneer_active", False)),
            lacquer_active=bool(data.get("lacquer_active", False)),
            grain_direction=str(data.get("grain_direction", "none") or "none"),
        )


@dataclass
class ModuleDef:
    module_id: str = ""
    name: str = "MOD_TEST_1"
    base_group: str = ""
    material_id: Optional[int] = None
    
    # Metadata (Desktop Parity)
    description: str = ""
    notes: str = ""
    quantity: int = 1
    angle_deg: float = 0.0

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
    carcass_joint_type_bottom: str = "type2"

    materials: Dict[str, str] = field(default_factory=dict)
    edgebands: Dict[str, str] = field(default_factory=dict)
    materials_finish: Dict[str, bool] = field(default_factory=dict)

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
    handle_type: str = "none"
    handle_length: int = 128
    handle_orientation: str = "horizontal"
    handle_pos_x: str = "center"
    handle_pos_y: str = "top"

    # region ADVANCED_CONSTRUCTION
    back_mounting_mode: str = "insert"  # overlay | insert | recess (nut)
    back_recess_depth_mm: float = 18.0
    back_clearance_mm: float = 0.0
    carcass_top_mode: str = "full"     # full | rails_h | rails_v
    carcass_bottom_mode: str = "full"  # full | rails_h | rails_v
    legs_height_mm: float = 100.0
    leg_type: str = "plastic_std"     # plastic_std | furniture_metal | plinth_brackets
    leg_offset_front: float = 50.0
    leg_offset_back: float = 50.0
    leg_offset_side: float = 50.0
    has_plinth: bool = False
    plinth_height_mm: float = 100.0
    plinth_inset_mm: float = 20.0

    front_grain_direction: str = "vertical"  # vertical | horizontal
    front_gap_top: float = 2.0
    front_gap_bottom: float = 2.0
    front_gap_left: float = 2.0
    front_gap_right: float = 2.0

    # region INTERNAL_ACCESSORIES
    hanging_rods_count: int = 0
    internal_drawers_count: int = 0
    led_lighting_active: bool = False
    lock_dimensions: bool = False
    visible_in_projection: bool = True
    drawer_guide_type: str = "soft_close"
    # endregion
    # endregion

    parts: Dict[str, "PartDef"] = field(default_factory=dict)

    def __post_init__(self) -> None:
        fallback_group = default_module_base_group_for_family(getattr(self, "module_family", ""))
        self.base_group = normalize_module_base_group(getattr(self, "base_group", ""), fallback_key=fallback_group)
        self.module_type = normalize_module_type(getattr(self, "module_type", "legacy"))
        self.shelf_mount = normalize_shelf_mount(getattr(self, "shelf_mount", "right"))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.module_id,
            "module_id": self.module_id,
            "name": self.name,
            "base_group": self.base_group,
            "material_id": self.material_id,
            "width_mm": float(self.width_mm),
            "depth_mm": float(self.depth_mm),
            "height_mm": float(self.height_mm),
            "description": self.description,
            "notes": self.notes,
            "quantity": int(self.quantity),
            "angle_deg": float(self.angle_deg),
            "top_rail_offset_mm": float(self.top_rail_offset_mm),
            "bottom_rail_offset_mm": float(self.bottom_rail_offset_mm),
            "carcass_joint_type": self.carcass_joint_type,
            "carcass_joint_type_bottom": self.carcass_joint_type_bottom,
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
            "materials_finish": dict(self.materials_finish or {}),
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
            "handle_type": self.handle_type,
            "handle_length": int(self.handle_length),
            "handle_orientation": self.handle_orientation,
            "handle_pos_x": self.handle_pos_x,
            "handle_pos_y": self.handle_pos_y,
            "back_mounting_mode": self.back_mounting_mode,
            "back_recess_depth_mm": float(self.back_recess_depth_mm),
            "back_clearance_mm": float(self.back_clearance_mm),
            "carcass_top_mode": self.carcass_top_mode,
            "carcass_bottom_mode": self.carcass_bottom_mode,
            "legs_height_mm": float(self.legs_height_mm),
            "leg_type": self.leg_type,
            "leg_offset_front": float(self.leg_offset_front),
            "leg_offset_back": float(self.leg_offset_back),
            "leg_offset_side": float(self.leg_offset_side),
            "has_plinth": bool(self.has_plinth),
            "plinth_height_mm": float(self.plinth_height_mm),
            "plinth_inset_mm": float(self.plinth_inset_mm),
            "front_grain_direction": self.front_grain_direction,
            "front_gap_top": float(self.front_gap_top),
            "front_gap_bottom": float(self.front_gap_bottom),
            "front_gap_left": float(self.front_gap_left),
            "front_gap_right": float(self.front_gap_right),
            "hanging_rods_count": int(self.hanging_rods_count),
            "internal_drawers_count": int(self.internal_drawers_count),
            "led_lighting_active": bool(self.led_lighting_active),
            "lock_dimensions": bool(self.lock_dimensions),
            "visible_in_projection": bool(self.visible_in_projection),
            "drawer_guide_type": self.drawer_guide_type,
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
            module_id=str(data.get("module_id", data.get("id", "")) or ""),
            name=str(data.get("name", "MOD_TEST_1") or "MOD_TEST_1"),
            base_group=str(data.get("base_group", "") or ""),
            material_id=data.get("material_id"),
            width_mm=float(data.get("width_mm", 820.0) or 820.0),
            depth_mm=float(data.get("depth_mm", 500.0) or 500.0),
            height_mm=float(data.get("height_mm", 700.0) or 700.0),
            description=str(data.get("description", "") or ""),
            notes=str(data.get("notes", "") or ""),
            quantity=int(data.get("quantity", 1) or 1),
            angle_deg=float(data.get("angle_deg", 0.0) or 0.0),
            top_rail_offset_mm=float(data.get("top_rail_offset_mm", 0.0) or 0.0),
            bottom_rail_offset_mm=float(data.get("bottom_rail_offset_mm", 0.0) or 0.0),
            carcass_joint_type=str(data.get("carcass_joint_type", "type2") or "type2"),
            carcass_joint_type_bottom=str(data.get("carcass_joint_type_bottom", "type2") or "type2"),
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
            materials_finish=dict(data.get("materials_finish", {}) or {}),
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
            handle_type=str(data.get("handle_type", "none") or "none"),
            handle_length=int(data.get("handle_length", 128) or 128),
            handle_orientation=str(data.get("handle_orientation", "horizontal") or "horizontal"),
            handle_pos_x=str(data.get("handle_pos_x", "center") or "center"),
            handle_pos_y=str(data.get("handle_pos_y", "top") or "top"),
            back_mounting_mode=str(data.get("back_mounting_mode", "insert") or "insert"),
            back_recess_depth_mm=float(data.get("back_recess_depth_mm", 18.0) or 18.0),
            back_clearance_mm=float(data.get("back_clearance_mm", 0.0) or 0.0),
            carcass_top_mode=str(data.get("carcass_top_mode", "full") or "full"),
            carcass_bottom_mode=str(data.get("carcass_bottom_mode", "full") or "full"),
            legs_height_mm=float(data.get("legs_height_mm", 100.0) or 100.0),
            leg_type=str(data.get("leg_type", "plastic_std") or "plastic_std"),
            leg_offset_front=float(data.get("leg_offset_front", 50.0) or 50.0),
            leg_offset_back=float(data.get("leg_offset_back", 50.0) or 50.0),
            leg_offset_side=float(data.get("leg_offset_side", 50.0) or 50.0),
            has_plinth=bool(data.get("has_plinth", False)),
            plinth_height_mm=float(data.get("plinth_height_mm", 100.0) or 100.0),
            plinth_inset_mm=float(data.get("plinth_inset_mm", 20.0) or 20.0),
            front_grain_direction=str(data.get("front_grain_direction", "vertical") or "vertical"),
            front_gap_top=float(data.get("front_gap_top", 2.0) or 2.0),
            front_gap_bottom=float(data.get("front_gap_bottom", 2.0) or 2.0),
            front_gap_left=float(data.get("front_gap_left", 2.0) or 2.0),
            front_gap_right=float(data.get("front_gap_right", 2.0) or 2.0),
            hanging_rods_count=int(data.get("hanging_rods_count", 0) or 0),
            internal_drawers_count=int(data.get("internal_drawers_count", 0) or 0),
            led_lighting_active=bool(data.get("led_lighting_active", False)),
            lock_dimensions=bool(data.get("lock_dimensions", False)),
            visible_in_projection=bool(data.get("visible_in_projection", True)),
            drawer_guide_type=str(data.get("drawer_guide_type", "soft_close") or "soft_close"),
            parts=parsed_parts,
        )
