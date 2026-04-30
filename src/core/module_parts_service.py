from __future__ import annotations

from typing import Dict
from src.domain.module_models import ModuleDef, PartDef
from src.storage.catalog_store_json import CatalogStoreJson
from src.core.rules.drawers import calculate_drawer_parts, pick_slide_length_mm


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
    Implements Corpus-style carcass logic (rails, back wall recess).
    """
    carcass_key = module.materials.get("carcass", "PB18")
    front_key = module.materials.get("front", "MDF19")
    back_key = module.materials.get("back", "HDF2.5")

    t_carcass = float(catalog.material_thickness(carcass_key, 18.0) or 18.0)
    t_front = float(catalog.material_thickness(front_key, 19.0) or 19.0)
    t_back = float(catalog.material_thickness(back_key, 2.5) or 2.5)

    if t_front <= 0.0: t_front = 19.0
    if t_back <= 0.0: t_back = 3.0
    if t_carcass <= 0.0: t_carcass = 18.0

    joint_type_top = getattr(module, "carcass_joint_type", "type2")
    joint_type_bottom = getattr(module, "carcass_joint_type_bottom", "type2")
    
    width_mm = float(module.width_mm)
    depth_mm = float(module.depth_mm)
    height_mm = float(module.height_mm)
    thickness = float(t_carcass)
    facade_mode = str(getattr(module, "facade_mode", "doors") or "doors").lower()

    visible_parts = set(module.visible_parts or set())
    parts: Dict[str, PartDef] = {}

    # region CONSTRUCTION PRE-CALCS
    raw_top_offset = float(getattr(module, "top_rail_offset_mm", 0.0) or 0.0)
    raw_bottom_offset = float(getattr(module, "bottom_rail_offset_mm", 0.0) or 0.0)

    # Note: offsets are usually handled downstream, but we need them for inside_h
    top_presence = thickness if "top" in visible_parts else 0.0
    bot_presence = thickness if "bottom" in visible_parts else 0.0

    # Inside height depends on joints
    # Type 1: side is between top/bottom
    # Type 2: top/bottom is between sides
    # We apply this per end
    
    # Calculate how much height top panel takes from side
    side_shorten_top = thickness if joint_type_top == "type2" else 0.0
    side_shorten_bottom = thickness if joint_type_bottom == "type2" else 0.0
    
    side_h = height_mm - side_shorten_top - side_shorten_bottom - raw_top_offset - raw_bottom_offset
    
    # Inside height (between top and bottom panel)
    inside_h = max(0.0, height_mm - 2 * thickness)

    # Inside width between vertical panels
    inside_w = max(0.0, width_mm - 2 * thickness)
    # endregion

    # --- SIDES ---
    if "side_left" in visible_parts:
        parts["side_left"] = PartDef("side_left", "Bok lewy", carcass_key, {"w": depth_mm, "h": side_h, "t": thickness}, {})
    if "side_right" in visible_parts:
        parts["side_right"] = PartDef("side_right", "Bok prawy", carcass_key, {"w": depth_mm, "h": side_h, "t": thickness}, {})

    # --- TOP (Plate or Rails) ---
    top_mode = getattr(module, "carcass_top_mode", "full")
    top_w = width_mm if joint_type_top == "type2" else inside_w
    if "top" in visible_parts:
        if top_mode == "rails_h":
            # Two horizontal rails (front and back) - typically 80mm
            rail_depth = 80.0
            parts["top_rail_front"] = PartDef("top_rail_front", "Listwa górna przednia", carcass_key, {"w": top_w, "h": rail_depth, "t": thickness}, {})
            parts["top_rail_back"] = PartDef("top_rail_back", "Listwa górna tylna", carcass_key, {"w": top_w, "h": rail_depth, "t": thickness}, {})
        else:
            parts["top"] = PartDef("top", "Wieniec górny", carcass_key, {"w": top_w, "h": depth_mm, "t": thickness}, {})

    # --- BOTTOM (Plate or Rails) ---
    bot_mode = getattr(module, "carcass_bottom_mode", "full")
    bot_w = width_mm if joint_type_bottom == "type2" else inside_w
    if "bottom" in visible_parts:
        if bot_mode == "rails_h":
            rail_depth = 80.0
            parts["bottom_rail_front"] = PartDef("bottom_rail_front", "Listwa dolna przednia", carcass_key, {"w": bot_w, "h": rail_depth, "t": thickness}, {})
            parts["bottom_rail_back"] = PartDef("bottom_rail_back", "Listwa dolna tylna", carcass_key, {"w": bot_w, "h": rail_depth, "t": thickness}, {})
        else:
            parts["bottom"] = PartDef("bottom", "Wieniec dolny", carcass_key, {"w": bot_w, "h": depth_mm, "t": thickness}, {})

    # --- BACK WALL ---
    if "back" in visible_parts:
        back_mode = getattr(module, "back_mounting_mode", "insert")
        back_recess = float(getattr(module, "back_recess_depth_mm", 18.0) or 0.0)
        back_clearance = float(getattr(module, "back_clearance_mm", 0.0) or 0.0)
        
        # Dimensions calc
        bw = width_mm
        bh = height_mm
        
        if back_mode == "insert":
            bw = inside_w - 2 * back_clearance
            bh = inside_h - 2 * back_clearance
        elif back_mode == "recess": # Nut
            nut_depth = 8.0 # Typical depth in the side
            bw = inside_w + 2 * nut_depth
            bh = inside_h + 2 * nut_depth
            
        parts["back"] = PartDef("back", "Plecy", back_key, {"w": bw, "h": bh, "t": t_back}, {})

    # --- FRONT ---
    if "front" in visible_parts:
        front_layout = str(getattr(module, "front_layout", "overlay") or "overlay").lower()
        
        # Load gaps from properties with fallback to standard Lignumsoft values
        gap_t = float(getattr(module, "front_gap_top", 2.0))
        gap_b = float(getattr(module, "front_gap_bottom", 3.0))
        gap_l = float(getattr(module, "front_gap_left", 2.0))
        gap_r = float(getattr(module, "front_gap_right", 2.0))

        if front_layout == "inset":
            fw = max(0.0, inside_w - gap_l - gap_r)
            fh = max(0.0, inside_h - gap_t - gap_b)
        else:
            fw = max(0.0, width_mm - gap_l - gap_r)
            fh = max(0.0, height_mm - gap_t - gap_b)
            
        grain_pl = "pionowe" if getattr(module, "front_grain_direction", "vertical") == "vertical" else "poziome"
        parts["front"] = PartDef("front", f"Front (słoj: {grain_pl})", front_key, {"w": fw, "h": fh, "t": t_front}, {})

    # --- DIVIDERS & SHELVES ---
    div_count = max(0, min(4, int(getattr(module, "divider_count", 0) or 0)))
    for i in range(1, div_count + 1):
        parts[f"divider_{i}"] = PartDef(f"divider_{i}", f"Pion {i}", carcass_key, {"w": depth_mm, "h": inside_h, "t": thickness}, {})

    shelf_count = max(0, int(getattr(module, "shelf_count", 0) or 0))
    seg_w = inside_w
    if div_count > 0:
        seg_w = (inside_w - div_count * thickness) / (div_count + 1)

    mount = str(getattr(module, "shelf_mount", "right") or "right").strip().lower()
    for i in range(1, shelf_count + 1):
        if mount == "both" and div_count > 0:
            parts[f"shelf_left_{i}"] = PartDef(f"shelf_left_{i}", f"Półka L {i}", carcass_key, {"w": seg_w, "h": depth_mm, "t": thickness}, {})
            parts[f"shelf_right_{i}"] = PartDef(f"shelf_right_{i}", f"Półka P {i}", carcass_key, {"w": seg_w, "h": depth_mm, "t": thickness}, {})
        else:
            parts[f"shelf_{i}"] = PartDef(f"shelf_{i}", f"Półka {i}", carcass_key, {"w": seg_w, "h": depth_mm, "t": thickness}, {})

    # --- DRAWERS INTERNALS ---
    if facade_mode == "drawers":
        d_count = max(0, int(getattr(module, "drawer_count", 0) or 0))
        d_system = str(getattr(module, "drawer_vendor", "blum_antaro") or "blum_antaro")
        
        slide_l = pick_slide_length_mm(depth_mm)
        
        for i in range(1, d_count + 1):
             # Assume all are 'M' height for now, could be improved with per-drawer config
             d_parts = calculate_drawer_parts(width_mm, thickness, slide_l, d_system)
             for dp in d_parts:
                 p_id = f"drawer_{i}_{dp.group}"
                 parts[p_id] = PartDef(p_id, f"{dp.name} {i}", carcass_key, {"w": dp.w, "h": dp.h, "t": dp.t}, {})

    # Sync edgebands and overrides
    old_parts = module.parts or {}
    for key, part in parts.items():
        old_part = old_parts.get(key)
        if not old_part: continue
        part.edge_banding = dict(old_part.edge_banding or {})
        override = str(getattr(old_part, "material_override_key", "") or "").strip()
        if override:
            part.material_key = override
            part.material_override_key = override
            try: part.dims_mm["t"] = float(catalog.material_thickness(override, part.dims_mm["t"]))
            except: pass

    return parts
