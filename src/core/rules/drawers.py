from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass(frozen=True)
class DrawerSystemDef:
    id: str
    name: str
    vendor: str
    bottom_width_offset: float # InternalWidth - bottom_width_offset
    bottom_depth_offset: float # SlideLength - bottom_depth_offset
    rear_width_offset: float   # InternalWidth - rear_width_offset
    rear_height_vals: Dict[str, float] # e.g. {'M': 68, 'K': 116, 'C': 160}

# Standard Blum Tandembox/Antaro logic
BLUM_ANTARO = DrawerSystemDef(
    id="blum_antaro",
    name="Blum Antaro",
    vendor="blum",
    bottom_width_offset=75.0, # (W - 75)
    bottom_depth_offset=24.0,  # (L - 24)
    rear_width_offset=87.0,    # (W - 87)
    rear_height_vals={'N': 68, 'M': 84, 'K': 116, 'C': 167, 'F': 199}
)

# GTV Modern Box
GTV_MODERN_BOX = DrawerSystemDef(
    id="gtv_modernbox",
    name="GTV Modern Box",
    vendor="gtv",
    bottom_width_offset=75.0,
    bottom_depth_offset=24.0,
    rear_width_offset=87.0,
    rear_height_vals={'M': 84, 'K': 135, 'C': 199}
)

DRAWER_SYSTEMS = {
    "blum_antaro": BLUM_ANTARO,
    "gtv_modernbox": GTV_MODERN_BOX
}

@dataclass(frozen=True)
class DrawerPartSpec:
    name: str
    w: float
    h: float
    t: float
    group: str = "drawer_internal"

def calculate_drawer_parts(
    module_width: float,
    side_thickness: float,
    slide_length: float,
    system_id: str,
    height_key: str = 'M'
) -> List[DrawerPartSpec]:
    """Calculates internal parts (bottom and back) for a single drawer."""
    sys = DRAWER_SYSTEMS.get(system_id, BLUM_ANTARO)
    
    internal_w = module_width - 2 * side_thickness
    
    # Bottom
    b_w = internal_w - sys.bottom_width_offset
    b_d = slide_length - sys.bottom_depth_offset
    
    # Rear
    r_w = internal_w - sys.rear_width_offset
    r_h = sys.rear_height_vals.get(height_key, 84.0)
    
    return [
        DrawerPartSpec(name="Dno szuflady", w=b_w, h=b_d, t=16.0, group="drawer_bottom"),
        DrawerPartSpec(name="Plecy szuflady", w=r_w, h=r_h, t=16.0, group="drawer_rear")
    ]

@dataclass(frozen=True)
class DrawerCalcInput:
    depth_mm: float
    rear_clearance_mm: float = 10.0
    front_layout: str = "overlay"
    front_thickness_mm: float = 0.0
    tip_on: bool = False
    tip_on_clearance_mm: float = 0.0


def pick_slide_length_mm(inp_or_depth, rear_clearance: float = 10.0) -> int:
    """Selects standard slide length (blum/gtv steps co 50mm).

    Accepts either a DrawerCalcInput or a bare depth_mm float (legacy).
    """
    if isinstance(inp_or_depth, DrawerCalcInput):
        inp = inp_or_depth
        avail = inp.depth_mm - inp.rear_clearance_mm
        if inp.front_layout == "inset":
            avail -= inp.front_thickness_mm
        if inp.tip_on:
            avail -= inp.tip_on_clearance_mm
    else:
        avail = inp_or_depth - rear_clearance
    lengths = list(range(250, 751, 50))
    ok = [L for L in lengths if L <= avail]
    return max(ok) if ok else 250