from __future__ import annotations

def hinges_count_for_door(height_mm: float, vendor: str = "generic") -> int:
    h = float(height_mm)
    # prosta regula startowa (bezpieczna):
    # do 850 -> 2, do 1500 -> 3, do 2000 -> 4, powyzej -> 5
    if h <= 850:
        return 2
    if h <= 1500:
        return 3
    if h <= 2000:
        return 4
    return 5