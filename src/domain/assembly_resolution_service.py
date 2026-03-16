from __future__ import annotations

from dataclasses import dataclass

from src.core.costing.module_costs import ModuleCostBreakdown, calculate_module_cost_breakdown
from src.core.module_parts_service import build_module_parts
from src.domain.assembly_models import (
    AssemblyModuleItemDef,
    FurnitureAssemblyDef,
    normalize_assembly_offset_ref_mode,
)
from src.domain.module_family_service import resolve_module_with_family_registry
from src.domain.module_models import ModuleDef, module_type_to_cabinet_kind, normalize_module_type
from src.domain.wall_models import WallLayoutDef
from src.storage.catalog_store_json import CatalogStoreJson


PROFILE_GROUP_KEYS: dict[str, tuple[str, ...]] = {
    "carcass": ("carcass", "side", "top", "bottom", "shelf", "divider"),
    "front": ("front",),
    "back": ("back",),
}


@dataclass(frozen=True)
class ResolvedAssemblyItem:
    item: AssemblyModuleItemDef
    module: ModuleDef
    x_mm: float
    y_mm: float
    width_mm: float
    height_mm: float
    depth_mm: float
    cost_breakdown: ModuleCostBreakdown
    has_collision: bool = False

    @property
    def display_name(self) -> str:
        return self.item.display_name()


def _clone_module(module: ModuleDef) -> ModuleDef:
    if hasattr(module, "to_dict"):
        return ModuleDef.from_dict(module.to_dict())
    return ModuleDef()


def _collapse_profile_map_to_groups(
    source_map: dict[str, str] | None,
    fallback_map: dict[str, str] | None = None,
) -> dict[str, str]:
    source = dict(source_map or {})
    fallback = dict(fallback_map or {})
    out: dict[str, str] = {}

    for group_key, logical_keys in PROFILE_GROUP_KEYS.items():
        selected = ""
        for logical_key in logical_keys:
            raw = str(source.get(logical_key, "") or "").strip()
            if raw:
                selected = raw
                break
        if not selected:
            selected = str(fallback.get(group_key, "") or "").strip()
        if selected:
            out[group_key] = selected

    return out


def _expand_group_edgebands_to_module_map(
    group_defaults: dict[str, str] | None,
    base_map: dict[str, str] | None = None,
) -> dict[str, str]:
    source = dict(group_defaults or {})
    out = dict(base_map or {})

    for group_key, logical_keys in PROFILE_GROUP_KEYS.items():
        selected = str(source.get(group_key, out.get(group_key, "Brak")) or "Brak").strip() or "Brak"
        out[group_key] = selected
        for logical_key in logical_keys:
            out[logical_key] = selected

    return out


def _expand_group_materials_to_module_map(
    group_defaults: dict[str, str] | None,
    base_map: dict[str, str] | None = None,
) -> dict[str, str]:
    source = dict(group_defaults or {})
    out = dict(base_map or {})

    for group_key, logical_keys in PROFILE_GROUP_KEYS.items():
        selected = str(source.get(group_key, "") or "").strip()
        if not selected:
            continue
        out[group_key] = selected
        for logical_key in logical_keys:
            out[logical_key] = selected

    return out


def resolve_assembly_module_item(
    item: AssemblyModuleItemDef,
    assembly: FurnitureAssemblyDef,
    catalog: CatalogStoreJson,
) -> ModuleDef:
    module = _clone_module(item.module)
    module = resolve_module_with_family_registry(module)

    profile_key = str(assembly.material_profile_key or getattr(module, "material_profile_key", "STD_WHITE") or "STD_WHITE")
    profile = catalog.get_material_profile(profile_key)

    if bool(getattr(module, "inherit_height_from_wall", False)):
        module.height_mm = float(assembly.height_mm)

    if bool(getattr(module, "inherit_depth_from_wall", False)):
        module.depth_mm = float(assembly.depth_mm)

    if bool(getattr(module, "inherit_materials_from_group", False)):
        inherited_materials = _collapse_profile_map_to_groups(
            dict(profile.material_map or {}),
            fallback_map=dict(module.materials or {}),
        )
        merged_materials = dict(module.materials or {})
        merged_materials.update(inherited_materials)
        module.materials = merged_materials
        module.material_profile_key = profile.key

    if bool(getattr(module, "inherit_edgeband_from_group", False)):
        inherited_edgebands = _collapse_profile_map_to_groups(
            dict(profile.edgeband_map or {}),
            fallback_map={},
        )
        module.edgebands = _expand_group_edgebands_to_module_map(
            inherited_edgebands,
            base_map=dict(module.edgebands or {}),
        )
        module.material_profile_key = profile.key

    if bool(getattr(assembly, "force_hardware_from_profile", True)):
        hardware_map = dict(profile.hardware_vendor_map or {})
        hinge_vendor = str(hardware_map.get("hinge", "") or "").strip().lower()
        drawer_vendor = str(hardware_map.get("drawer_system", "") or "").strip().lower()
        if hinge_vendor:
            module.hinge_vendor = hinge_vendor
        if drawer_vendor:
            module.drawer_vendor = drawer_vendor
        module.material_profile_key = profile.key

    hardware_vendor_overrides = {
        str(key or "").strip().lower(): str(value or "").strip().lower()
        for key, value in dict(getattr(assembly, "hardware_vendor_overrides", {}) or {}).items()
        if str(value or "").strip()
    }
    if hardware_vendor_overrides:
        hinge_vendor = str(hardware_vendor_overrides.get("hinge", "") or "").strip()
        drawer_vendor = str(hardware_vendor_overrides.get("drawer_system", "") or "").strip()
        if hinge_vendor:
            module.hinge_vendor = hinge_vendor
        if drawer_vendor:
            module.drawer_vendor = drawer_vendor

    assembly_material_overrides = {
        str(key or "").strip().lower(): str(value or "").strip()
        for key, value in dict(getattr(assembly, "material_overrides", {}) or {}).items()
        if str(value or "").strip()
    }
    if assembly_material_overrides:
        module.materials = _expand_group_materials_to_module_map(
            assembly_material_overrides,
            base_map=dict(module.materials or {}),
        )

    module.parts = build_module_parts(module, catalog)
    return module


def _resolve_module_auto_y_mm(
    module: ModuleDef,
    wall_height_mm: float,
    linked_wall: WallLayoutDef | None,
) -> float:
    wall_height_mm = max(1.0, float(wall_height_mm or 1.0))
    module_height_mm = max(0.0, float(getattr(module, "height_mm", 0.0) or 0.0))
    module_type = normalize_module_type(str(getattr(module, "module_type", "legacy") or "legacy"))
    cabinet_kind = module_type_to_cabinet_kind(
        module_type,
        fallback_kind=str(getattr(module, "cabinet_kind", "lower") or "lower"),
    )

    if linked_wall is None:
        if cabinet_kind == "upper":
            return 0.0
        return max(0.0, wall_height_mm - module_height_mm)

    upper_clearance_mm = max(0.0, float(getattr(linked_wall, "upper_clearance_mm", 0.0) or 0.0))
    base_plinth_mm = max(0.0, float(getattr(linked_wall, "base_plinth_mm", 0.0) or 0.0))

    if cabinet_kind == "upper":
        return max(0.0, min(upper_clearance_mm, wall_height_mm - module_height_mm))

    return max(0.0, wall_height_mm - base_plinth_mm - module_height_mm)


def _resolve_module_y_mm(
    item: AssemblyModuleItemDef,
    module: ModuleDef,
    wall_height_mm: float,
    linked_wall: WallLayoutDef | None,
) -> float:
    wall_height_mm = max(1.0, float(wall_height_mm or 1.0))
    module_height_mm = max(0.0, float(getattr(module, "height_mm", 0.0) or 0.0))
    auto_y_mm = _resolve_module_auto_y_mm(module, wall_height_mm, linked_wall)

    raw_y = getattr(item, "position_y_mm", None)
    if raw_y in (None, ""):
        return auto_y_mm

    try:
        y_mm = float(raw_y)
    except Exception:
        return auto_y_mm

    max_y = max(0.0, wall_height_mm - module_height_mm)
    y_mm = max(0.0, min(y_mm, max_y))
    if abs(y_mm - auto_y_mm) <= 20.0:
        return auto_y_mm
    return y_mm


def resolve_assembly_items(
    assembly: FurnitureAssemblyDef,
    catalog: CatalogStoreJson,
    auto_double_front_width_mm: float = 600.0,
    linked_wall: WallLayoutDef | None = None,
) -> list[ResolvedAssemblyItem]:
    resolved_items: list[ResolvedAssemblyItem] = []
    gap_mm = max(0.0, float(getattr(assembly, "gap_mm", 0.0) or 0.0))
    wall_height = max(1.0, float(getattr(assembly, "height_mm", 1.0) or 1.0))

    for index, item in enumerate(list(getattr(assembly, "items", []) or [])):
        module = resolve_assembly_module_item(item, assembly, catalog)
        width_mm = max(0.0, float(getattr(module, "width_mm", 0.0) or 0.0))
        height_mm = max(0.0, float(getattr(module, "height_mm", 0.0) or 0.0))
        depth_mm = max(0.0, float(getattr(module, "depth_mm", 0.0) or 0.0))
        offset_mm = float(getattr(item, "offset_mm", 0.0) or 0.0)
        y_mm = _resolve_module_y_mm(item, module, wall_height, linked_wall)
        offset_ref_mode = normalize_assembly_offset_ref_mode(getattr(item, "offset_ref_mode", "wall_left"))

        if offset_ref_mode == "previous_module" and index > 0 and resolved_items:
            previous = resolved_items[-1]
            base_x_mm = float(previous.x_mm) + float(previous.width_mm) + gap_mm
        else:
            base_x_mm = 0.0

        x_mm = base_x_mm + offset_mm

        cost_breakdown = calculate_module_cost_breakdown(
            module,
            catalog,
            auto_double_front_width_mm=float(auto_double_front_width_mm or 600.0),
        )

        resolved_items.append(
            ResolvedAssemblyItem(
                item=item,
                module=module,
                x_mm=x_mm,
                y_mm=y_mm,
                width_mm=width_mm,
                height_mm=height_mm,
                depth_mm=depth_mm,
                cost_breakdown=cost_breakdown,
                has_collision=False,
            )
        )

    for index, item in enumerate(resolved_items):
        rect_left = float(item.x_mm)
        rect_top = float(item.y_mm)
        rect_right = rect_left + float(item.width_mm)
        rect_bottom = rect_top + float(item.height_mm)
        for other_index, other in enumerate(resolved_items):
            if other_index >= index:
                break
            other_left = float(other.x_mm)
            other_top = float(other.y_mm)
            other_right = other_left + float(other.width_mm)
            other_bottom = other_top + float(other.height_mm)

            overlap_x = min(rect_right, other_right) - max(rect_left, other_left)
            overlap_y = min(rect_bottom, other_bottom) - max(rect_top, other_top)
            if overlap_x > 0.5 and overlap_y > 0.5:
                object.__setattr__(resolved_items[index], "has_collision", True)
                object.__setattr__(resolved_items[other_index], "has_collision", True)

    return resolved_items
