from __future__ import annotations
from src.domain.module_models import ModuleDef

def calculate_front_weight_kg(module: ModuleDef, density_kg_m3: float = 750.0) -> float:
    """Calculates the weight of the front facade including handle allowance."""
    width_m = float(getattr(module, "width_mm", 0.0) or 0.0) / 1000.0
    height_m = float(getattr(module, "height_mm", 0.0) or 0.0) / 1000.0
    
    # Try to find 'front' part to get its specific thickness
    thickness_mm = 18.0
    parts = getattr(module, "parts", {}) or {}
    for key, part in parts.items():
        if "front" in str(key).lower():
            thickness_mm = float((part.dims_mm or {}).get("t", 18.0) or 18.0)
            break
            
    thickness_m = thickness_mm / 1000.0
    area_m2 = width_m * height_m
    
    weight_kg = area_m2 * thickness_m * density_kg_m3
    
    # Add handle weight (allowance 0.5kg)
    return weight_kg + 0.5

def select_blum_aventos_system(height_mm: float, weight_kg: float) -> dict[str, str] | None:
    """
    Selects a Blum Aventos power factor and mechanism based on PF = height * weight.
    This is a simplified professional heuristic for automated BOM selection.
    """
    if height_mm <= 0 or weight_kg <= 0:
        return None
        
    pf = height_mm * weight_kg
    
    # Simple HK-S (Stay Lift) ranges
    if height_mm < 600:
        if 200 <= pf <= 500:
            return {"type": "HK-S", "pf_class": "A", "label": "Aventos HK-S (20K2B00)"}
        if 501 <= pf <= 1015:
            return {"type": "HK-S", "pf_class": "B", "label": "Aventos HK-S (20K2C00)"}
        if 1016 <= pf <= 2200:
            return {"type": "HK-S", "pf_class": "C", "label": "Aventos HK-S (20K2E00)"}
            
    # Larger HK top
    if 480 <= pf <= 1500:
        return {"type": "HK-top", "pf_class": "20K2300", "label": "Aventos HK-top (Low)"}
    if 1501 <= pf <= 4500:
        return {"type": "HK-top", "pf_class": "20K2500", "label": "Aventos HK-top (Medium)"}
    if 4501 <= pf <= 12000:
        return {"type": "HK-top", "pf_class": "20K2700", "label": "Aventos HK-top (High)"}

    return {"type": "Generic Lift", "pf_class": "N/A", "label": "Siłownik gazowy (GTV/Inne)"}
