from __future__ import annotations

from dataclasses import dataclass

from src.core.rules.hinges import hinges_count_for_door
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

    if module_type in ("legs", "legs_plinth", "corner"):
        leg_qty = 6.0 if width_mm >= 900.0 or module_type == "corner" else 4.0
        out.append(
            HardwareRequirement(
                category="cabinet_leg",
                manufacturer="generic",
                quantity=leg_qty,
                unit="szt",
                note="nogi meblowe",
            )
        )

    if module_type == "legs_plinth":
        out.append(
            HardwareRequirement(
                category="plinth_clip",
                manufacturer="generic",
                quantity=2.0,
                unit="szt",
                note="cokol",
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

    return out
