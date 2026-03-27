from __future__ import annotations

from typing import Dict

from src.domain.module_models import ModuleDef, PartDef
from src.storage.catalog_store_json import CatalogStoreJson


def normalize_rail_offsets_mm(
    height_mm: float,
    rail_thickness_mm: float,
    top_offset_mm: float,
    bottom_offset_mm: float,
) -> tuple[float, float]:
    height = max(0.0, float(height_mm))
    thickness = max(0.0, float(rail_thickness_mm))

    try:
        top = max(0.0, float(top_offset_mm))
    except Exception:
        top = 0.0

    try:
        bottom = max(0.0, float(bottom_offset_mm))
    except Exception:
        bottom = 0.0

    max_top = max(0.0, height - 2.0 * thickness)
    top = min(top, max_top)

    max_bottom = max(0.0, height - 2.0 * thickness - top)
    bottom = min(bottom, max_bottom)

    return top, bottom


def build_module_parts(module: ModuleDef, catalog: CatalogStoreJson) -> Dict[str, PartDef]:
    """
    Builds module parts from the current effective module state.

    This function mutates only normalized rail offsets on the provided module.
    Returned parts preserve existing edge banding and part-level material overrides.
    """
    carcass_key = module.materials.get("carcass", "PB18")
    front_key = module.materials.get("front", "MDF19")
    back_key = module.materials.get("back", "HDF2.5")

    t_carcass = float(catalog.material_thickness(carcass_key, 18.0) or 18.0)
    t_front = float(catalog.material_thickness(front_key, 19.0) or 19.0)
    t_back = float(catalog.material_thickness(back_key, 2.5) or 2.5)

    if t_front <= 0.0:
        t_front = 19.0
    if t_back <= 0.0:
        t_back = 3.0
    if t_carcass <= 0.0:
        t_carcass = 18.0

    joint_type = getattr(module, "carcass_joint_type", "type1")

    width_mm = float(module.width_mm)
    depth_mm = float(module.depth_mm)
    height_mm = float(module.height_mm)
    thickness = float(t_carcass)

    def inside_width_between_sides() -> float:
        return max(0.0, width_mm - 2 * thickness)

    visible_parts = set(module.visible_parts or set())
    parts: Dict[str, PartDef] = {}

    raw_top_offset = float(getattr(module, "top_rail_offset_mm", 0.0) or 0.0)
    raw_bottom_offset = float(getattr(module, "bottom_rail_offset_mm", 0.0) or 0.0)

    normalized_top_offset, normalized_bottom_offset = normalize_rail_offsets_mm(
        height_mm=height_mm,
        rail_thickness_mm=thickness,
        top_offset_mm=raw_top_offset,
        bottom_offset_mm=raw_bottom_offset,
    )

    top_rail_offset_mm = normalized_top_offset if "top" in visible_parts else 0.0
    bottom_rail_offset_mm = normalized_bottom_offset if "bottom" in visible_parts else 0.0

    setattr(module, "top_rail_offset_mm", normalized_top_offset)
    setattr(module, "bottom_rail_offset_mm", normalized_bottom_offset)

    top_rail_presence_mm = thickness if "top" in visible_parts else 0.0
    bottom_rail_presence_mm = thickness if "bottom" in visible_parts else 0.0

    def inside_height_between_rails() -> float:
        return max(
            0.0,
            height_mm
            - top_rail_presence_mm
            - bottom_rail_presence_mm
            - top_rail_offset_mm
            - bottom_rail_offset_mm,
        )

    if "side_left" in visible_parts:
        parts["side_left"] = PartDef(
            "side_left",
            "Bok lewy",
            carcass_key,
            {"w": depth_mm, "h": height_mm if joint_type == "type1" else inside_height_between_rails(), "t": thickness},
            {},
        )

    if "side_right" in visible_parts:
        parts["side_right"] = PartDef(
            "side_right",
            "Bok prawy",
            carcass_key,
            {"w": depth_mm, "h": height_mm if joint_type == "type1" else inside_height_between_rails(), "t": thickness},
            {},
        )

    if "top" in visible_parts:
        parts["top"] = PartDef(
            "top",
            "Wieniec gorny",
            carcass_key,
            {"w": (inside_width_between_sides() if joint_type == "type1" else width_mm), "h": depth_mm, "t": thickness},
            {},
        )

    if "bottom" in visible_parts:
        parts["bottom"] = PartDef(
            "bottom",
            "Wieniec dolny",
            carcass_key,
            {"w": (inside_width_between_sides() if joint_type == "type1" else width_mm), "h": depth_mm, "t": thickness},
            {},
        )

    if "back" in visible_parts:
        parts["back"] = PartDef("back", "Plecy", back_key, {"w": width_mm, "h": height_mm, "t": t_back}, {})

    if "front" in visible_parts:
        front_layout = str(getattr(module, "front_layout", "overlay") or "overlay").lower()
        if front_layout == "inset":
            front_width = inside_width_between_sides()
            front_height = inside_height_between_rails()
        else:
            front_width = width_mm
            front_height = height_mm
        parts["front"] = PartDef("front", "Front", front_key, {"w": front_width, "h": front_height, "t": t_front}, {})

    divider_count = int(getattr(module, "divider_count", 0) or 0)
    if "divider" not in visible_parts:
        divider_count = 0
    divider_count = max(0, min(4, divider_count))

    for index in range(1, divider_count + 1):
        key = f"divider_{index}"
        parts[key] = PartDef(
            key,
            f"Pion {index}",
            carcass_key,
            {"w": depth_mm, "h": inside_height_between_rails(), "t": thickness},
            {},
        )

    shelf_count = int(getattr(module, "shelf_count", 0) or 0)
    if "shelf" not in visible_parts:
        shelf_count = 0
    shelf_count = max(0, shelf_count)

    inner_width = inside_width_between_sides()
    segment_width = inner_width
    if divider_count > 0:
        clear_width = max(0.0, inner_width - divider_count * thickness)
        segment_width = clear_width / (divider_count + 1) if (divider_count + 1) > 0 else clear_width

    mount = str(getattr(module, "shelf_mount", "right") or "right").strip().lower()
    mount_both = (mount == "both") and divider_count > 0

    for index in range(1, shelf_count + 1):
        if mount_both:
            for side_key, side_label in (("left", "L"), ("right", "P")):
                key = f"shelf_{side_key}_{index}"
                parts[key] = PartDef(
                    key,
                    f"Polka {side_label} {index}",
                    carcass_key,
                    {"w": segment_width, "h": depth_mm, "t": thickness},
                    {},
                )
            continue

        key = f"shelf_{index}"
        parts[key] = PartDef(
            key,
            f"Polka {index}",
            carcass_key,
            {"w": segment_width, "h": depth_mm, "t": thickness},
            {},
        )

    old_parts = module.parts or {}
    for key, part in parts.items():
        old_part = old_parts.get(key)
        if old_part is None:
            continue

        part.edge_banding = dict(old_part.edge_banding or {})

        override_key = str(getattr(old_part, "material_override_key", "") or "").strip()
        if not override_key:
            part.material_override_key = ""
            continue

        part.material_key = override_key
        part.material_override_key = override_key
        try:
            part.dims_mm["t"] = float(catalog.material_thickness(override_key, part.dims_mm.get("t", 0.0)))
        except Exception:
            pass

    return parts
