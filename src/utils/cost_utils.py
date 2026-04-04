from __future__ import annotations

from typing import List, Tuple

from src.domain.service_models import ServiceComponentDef


def calc_material_and_work_costs(components: List[ServiceComponentDef]) -> Tuple[float, float]:
    """Calculate total material cost and total work hours from a list of components.

    - material components contribute to material_cost via estimated_cost
    - work components contribute to work_hours; units 'h' or 'min' supported
    - service components contribute their estimated_cost as material cost
    - for unknown types, ignored
    
    Returns: (material_cost, work_hours)
    """
    material_cost = 0.0
    work_hours = 0.0
    for comp in components or []:
        t = (comp.component_type or "").lower()
        if t == "material":
            material_cost += float(comp.estimated_cost or 0.0)
        elif t == "work":
            unit = (comp.unit or "").lower()
            if unit == "h":
                work_hours += float(comp.quantity or 0.0)
            elif unit == "min":
                work_hours += float(comp.quantity or 0.0) / 60.0
            else:
                work_hours += float(comp.quantity or 0.0)
        elif t == "service":
            material_cost += float(comp.estimated_cost or 0.0)
        else:
            # Unknown type - ignore for now
            pass
    return material_cost, work_hours
