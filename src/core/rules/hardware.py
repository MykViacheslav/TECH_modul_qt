from __future__ import annotations

from dataclasses import dataclass

from src.core.rules.hinges import hinges_count_for_door
from src.core.rules.lifts import calculate_front_weight_kg, select_blum_aventos_system
from src.domain.module_models import ModuleDef, normalize_module_type


@dataclass(frozen=True)
class HardwareRequirement:
    category: str
    manufacturer: str
    quantity: float
    unit: str
    note: str = ""


def _count_parts(module: ModuleDef, prefix: str, fallback: int = 0) -> int:
    parts = dict(getattr(module, "parts", {}) or {})
    if parts:
        return sum(1 for key in parts.keys() if str(key).startswith(prefix))
    return max(0, int(fallback or 0))


def estimate_module_hardware_requirements(
    module: ModuleDef,
    auto_double_front_width_mm: float = 600.0,
) -> list[HardwareRequirement]:
    out: list[HardwareRequirement] = []

    width_mm = float(getattr(module, "width_mm", 0.0) or 0.0)
    height_mm = float(getattr(module, "height_mm", 0.0) or 0.0)
    cabinet_kind = str(getattr(module, "cabinet_kind", "lower") or "lower").strip().lower()
    facade_mode = str(getattr(module, "facade_mode", "doors") or "doors").strip().lower()
    hinge_vendor = str(getattr(module, "hinge_vendor", "generic") or "generic").strip().lower() or "generic"
    drawer_vendor = str(getattr(module, "drawer_vendor", "generic") or "generic").strip().lower() or "generic"
    drawer_tip_on = bool(getattr(module, "drawer_tip_on", False))
    module_type = normalize_module_type(getattr(module, "module_type", "legacy"))

    front_present = "front" in set(getattr(module, "visible_parts", set()) or set())

    auto_double_width = max(100.0, float(auto_double_front_width_mm or 600.0))

    if facade_mode == "doors" and front_present:
        door_count = 2 if width_mm >= auto_double_width else 1
        hinge_qty = door_count * hinges_count_for_door(height_mm, hinge_vendor)
        if hinge_qty > 0:
            out.append(
                HardwareRequirement(
                    category="hinge",
                    manufacturer=hinge_vendor,
                    quantity=float(hinge_qty),
                    unit="szt",
                    note=f"drzwi x {door_count}",
                )
            )
            
    if facade_mode in ("lift", "tilt") and front_present:
        weight = calculate_front_weight_kg(module)
        lift_sys = select_blum_aventos_system(height_mm, weight)
        if lift_sys:
            out.append(
                HardwareRequirement(
                    category="lift_system",
                    manufacturer="blum",
                    quantity=1.0,
                    unit="kpl",
                    note=f"{lift_sys['label']} (W={weight:.1f}kg, PF={height_mm*weight:.0f})",
                )
            )
        else:
            out.append(
                HardwareRequirement(
                    category="lift_gas_strut",
                    manufacturer="generic",
                    quantity=2.0,
                    unit="szt",
                    note="Standard gas strut",
                )
            )

    drawer_count = int(getattr(module, "drawer_count", 0) or 0)
    if facade_mode in ("drawers", "mixed") and drawer_count > 0:
        out.append(
            HardwareRequirement(
                category="drawer_system",
                manufacturer=drawer_vendor,
                quantity=float(drawer_count),
                unit="kpl",
                note=f"szuflady x {drawer_count}",
            )
        )
        if drawer_tip_on:
            out.append(
                HardwareRequirement(
                    category="drawer_tip_on",
                    manufacturer=drawer_vendor,
                    quantity=float(drawer_count),
                    unit="szt",
                    note="push-to-open",
                )
            )

    shelf_count = _count_parts(module, "shelf_", getattr(module, "shelf_count", 0))
    if shelf_count > 0:
        out.append(
            HardwareRequirement(
                category="shelf_support",
                manufacturer="generic",
                quantity=float(shelf_count * 4),
                unit="szt",
                note=f"polki x {shelf_count}",
            )
        )

    divider_count = _count_parts(module, "divider_", getattr(module, "divider_count", 0))
    if divider_count > 0:
        out.append(
            HardwareRequirement(
                category="divider_connector",
                manufacturer="generic",
                quantity=float(divider_count * 4),
                unit="szt",
                note=f"piony x {divider_count}",
            )
        )

    if cabinet_kind == "upper" or module_type == "hanging":
        out.append(
            HardwareRequirement(
                category="wall_hanger",
                manufacturer="generic",
                quantity=2.0,
                unit="szt",
                note="szafka wiszaca",
            )
        )

    if cabinet_kind == "lower":
        # Professional leg counting logic (Corpus-inspired)
        leg_qty = 4.0
        if width_mm >= 900.0 or module_type == "corner":
            leg_qty = 6.0
        
        leg_type = str(getattr(module, "leg_type", "plastic_std") or "plastic_std")
        leg_h = float(getattr(module, "legs_height_mm", 100.0) or 100.0)
        
        out.append(
            HardwareRequirement(
                category="cabinet_leg",
                manufacturer=leg_type, # Using leg_type as a key for hardware find
                quantity=leg_qty,
                unit="szt",
                note=f"H={leg_h} mm",
            )
        )
        if leg_type == "plastic_std":
            out.append(
                HardwareRequirement(
                    category="plinth_clip",
                    manufacturer="generic",
                    quantity=2.0,
                    unit="szt",
                    note="zaczepy cokołu",
                )
            )

    if module_type == "corner":
        out.append(
            HardwareRequirement(
                category="corner_connector",
                manufacturer="generic",
                quantity=1.0,
                unit="kpl",
                note="szafka narozna",
            )
        )

    # region INTERNAL_ACCESSORIES
    rod_count = int(getattr(module, "hanging_rods_count", 0) or 0)
    if rod_count > 0:
        out.append(
            HardwareRequirement(
                category="hanging_rod",
                manufacturer="generic",
                quantity=float(rod_count),
                unit="szt",
                note=f"drążek L={width_mm - 36:.0f}mm", # assume 18mm sides
            )
        )

    int_drawer_count = int(getattr(module, "internal_drawers_count", 0) or 0)
    if int_drawer_count > 0:
        out.append(
            HardwareRequirement(
                category="drawer_system",
                manufacturer=drawer_vendor,
                quantity=float(int_drawer_count),
                unit="kpl",
                note="szuflada wewnętrzna",
            )
        )
    
    if bool(getattr(module, "led_lighting_active", False)):
        out.append(
            HardwareRequirement(
                category="led_strip",
                manufacturer="generic",
                quantity=1.0,
                unit="kpl",
                note="oświetlenie wnętrza",
            )
        )
    # endregion

    return out
