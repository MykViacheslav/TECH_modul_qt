from __future__ import annotations
from dataclasses import dataclass
from typing import List
from src.domain.module_models import ModuleDef, PartDef

@dataclass
class DrillingDef:
    x: float
    y: float
    z: float
    vx: float
    vy: float
    vz: float
    depth: float
    diam: float
    mark: str = "0"

def generate_drilling_for_part(module: ModuleDef, part: PartDef, part_key: str) -> List[DrillingDef]:
    """Generates CNC drilling operations for a specific part based on module rules."""
    drills: List[DrillingDef] = []
    
    # 1. Coordinate context
    # Usually we drill on the 'Face' (Z=thickness or 0) or on the 'Edges' (X/Y boundary)
    w = float((part.dims_mm or {}).get("w", 0))
    h = float((part.dims_mm or {}).get("h", 0))
    t = float((part.dims_mm or {}).get("t", 18))
    
    part_name = part_key.lower()
    
    # --- RULE: Hinges (Zawiasy) ---
    if "side" in part_name:
        # Drilling for hinge base plate (prowadnik)
        # Standard: 37mm from front edge, 32mm spacing
        from src.core.rules.hinges import hinges_count_for_door
        h_mod = float(getattr(module, "height_mm", 0))
        qty = hinges_count_for_door(h_mod)
        
        # Positions (from top/bottom)
        offsets = [100.0] # start with 100mm from bottom
        if qty >= 2: offsets.append(h_mod - 100.0) # 100mm from top
        if qty >= 3: offsets.append(h_mod / 2.0) # middle
        if qty >= 4:
             offsets = [100.0, h_mod - 100.0]
             offsets.append(100.0 + (h_mod - 200.0) / 3.0)
             offsets.append(100.0 + 2.0 * (h_mod - 200.0) / 3.0)
        
        for y_pos in offsets:
            # Prowadnik Blum (37mm from front)
            # Two holes fi-5 or fi-3
            # We use fi-3 depth 13mm
            drills.append(DrillingDef(x=37.0, y=y_pos - 16.0, z=0, vx=0, vy=0, vz=1, depth=13, diam=3, mark="HINGE_PLATE"))
            drills.append(DrillingDef(x=37.0, y=y_pos + 16.0, z=0, vx=0, vy=0, vz=1, depth=13, diam=3, mark="HINGE_PLATE"))

    if "front" in part_name:
        # Drilling for hinge cup (puszka fi-35)
        # Standard: 100mm/h-100mm offsets, 22.5mm from side edge
        from src.core.rules.hinges import hinges_count_for_door
        h_mod = float(getattr(module, "height_mm", 0))
        qty = hinges_count_for_door(h_mod)
        
        offsets = [100.0]
        if qty >= 2: offsets.append(h_mod - 100.0)
        if qty >= 3: offsets.append(h_mod / 2.0)
        # (similar offset logic as above)

        for y_pos in offsets:
            # Puszka fi-35 depth 12mm
            # Origin of part is bottom-left usually
            drills.append(DrillingDef(x=22.5, y=y_pos, z=t, vx=0, vy=0, vz=-1, depth=12.5, diam=35, mark="HINGE_CUP"))

    # --- RULE: Shelf Supports (Podpórki) ---
    if "side" in part_name:
         shelf_count = int(getattr(module, "shelf_count", 0) or 0)
         if shelf_count > 0:
             # Regular grid of holes fi-5 or just for current shelves
             depth_mod = float(getattr(module, "depth_mm", 0))
             y_step = h_mod / (shelf_count + 1)
             for i in range(1, shelf_count + 1):
                 y_pos = i * y_step
                 # Front and back supports
                 drills.append(DrillingDef(x=37.0, y=y_pos, z=0, vx=0, vy=0, vz=1, depth=8, diam=5, mark="SHELF_SUP"))
                 drills.append(DrillingDef(x=depth_mod - 37.0, y=y_pos, z=0, vx=0, vy=0, vz=1, depth=8, diam=5, mark="SHELF_SUP"))

    # --- RULE: Drawer Slides (Prowadnice) ---
    if "side" in part_name:
         facade_mode = str(getattr(module, "facade_mode", "doors") or "doors").lower()
         if facade_mode == "drawers":
             d_count = int(getattr(module, "drawer_count", 0) or 0)
             if d_count > 0:
                 # Standard vertical spacing (assume equal distribution)
                 h_mod = float(getattr(module, "height_mm", 0))
                 step = h_mod / d_count
                 for i in range(d_count):
                     y_pos = (i * step) + 32.0 # offset from drawer bottom
                     # Typically runners have holes at 37mm, 128mm, etc from front
                     # Hole 1: 37mm
                     drills.append(DrillingDef(x=37.0, y=y_pos, z=0, vx=0, vy=0, vz=1, depth=12, diam=5, mark="DRAWER_RUNNER"))
                     # Hole 2: 128mm or depends on length
                     drills.append(DrillingDef(x=128.0, y=y_pos, z=0, vx=0, vy=0, vz=1, depth=12, diam=5, mark="DRAWER_RUNNER"))

    return drills
