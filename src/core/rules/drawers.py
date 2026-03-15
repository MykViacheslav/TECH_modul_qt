from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class DrawerCalcInput:
    depth_mm: float
    rear_clearance_mm: float = 10.0
    front_layout: str = "overlay"  # overlay | inset
    front_thickness_mm: float = 19.0
    tip_on: bool = False
    tip_on_clearance_mm: float = 20.0
    available_lengths_mm: List[int] = None


def pick_slide_length_mm(inp: DrawerCalcInput) -> int | None:
    depth = float(inp.depth_mm)
    rear = float(inp.rear_clearance_mm)
    front_t = float(inp.front_thickness_mm)
    tip = float(inp.tip_on_clearance_mm)

    avail = depth - rear
    if inp.front_layout == "inset":
        avail -= front_t
    if inp.tip_on:
        avail -= tip

    if inp.available_lengths_mm is None:
        # default: co 50mm
        lengths = list(range(250, 751, 50))
    else:
        lengths = sorted([int(x) for x in inp.available_lengths_mm])

    ok = [L for L in lengths if L <= avail]
    return max(ok) if ok else None