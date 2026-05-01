"""
TechModuleService — logika biznesowa modułu MSI Tech.

Oblicza BOM (listę formatek i okuć) na podstawie parametrów modułu.
Korzysta z silnika reguł w src/core/rules/.
"""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from src.core.rules.drawers import (
    DrawerCalcInput,
    calculate_drawer_parts,
    pick_slide_length_mm,
)
from src.core.rules.hinges import hinges_count_for_door
from .config import (
    SHELF_PINS_PER_SHELF,
)
from .models import BomLine, PartSpec, TechModule

if TYPE_CHECKING:
    pass


class TechModuleService:
    """Serwis obliczeniowy dla modułu meblowego."""

    def calculate_bom(self, module: TechModule) -> list[BomLine]:
        """Zwraca pełną listę materiałów (BOM) dla danego modułu."""
        bom: list[BomLine] = []
        bom.extend(self._carcass_parts(module))
        bom.extend(self._back_part(module))
        bom.extend(self._shelf_parts(module))
        bom.extend(self._drawer_parts(module))
        bom.extend(self._door_parts(module))
        bom.extend(self._hardware_lines(module))
        # TODO: dodać obsługę mechanizmów górnounoszących — lifts.py
        return bom

    # --- korpus ---

    def _carcass_parts(self, m: TechModule) -> list[BomLine]:
        t = m.material_thickness_mm
        inner_w = m.width_mm - 2 * t
        inner_h = m.height_mm - 2 * t
        depth = m.depth_mm - m.back_thickness_mm

        return [
            BomLine("Bok lewy",   depth, m.height_mm, t, 2, "carcass", "abs_2mm"),
            BomLine("Bok prawy",  depth, m.height_mm, t, 2, "carcass", "abs_2mm"),
            BomLine("Góra",       inner_w, depth, t, 1, "carcass", "abs_2mm"),
            BomLine("Dno",        inner_w, depth, t, 1, "carcass", "abs_2mm"),
        ]

    def _back_part(self, m: TechModule) -> list[BomLine]:
        t = m.material_thickness_mm
        return [
            BomLine(
                "Plecy HDF",
                m.width_mm - 2 * t,
                m.height_mm - 2 * t,
                m.back_thickness_mm,
                1,
                "back",
            )
        ]

    # --- półki ---

    def _shelf_parts(self, m: TechModule) -> list[BomLine]:
        if m.num_shelves <= 0:
            return []
        t = m.material_thickness_mm
        inner_w = m.width_mm - 2 * t
        depth = m.depth_mm - m.back_thickness_mm - 20  # 20mm luzu od frontu
        return [
            BomLine("Półka", inner_w, depth, t, m.num_shelves, "shelf", "abs_2mm")
        ]

    # --- szuflady ---

    def _drawer_parts(self, m: TechModule) -> list[BomLine]:
        if m.num_drawers <= 0:
            return []
        t = m.material_thickness_mm
        inp = DrawerCalcInput(depth_mm=m.depth_mm)
        slide_len = pick_slide_length_mm(inp)

        raw_parts = calculate_drawer_parts(
            module_width=m.width_mm,
            side_thickness=t,
            slide_length=slide_len,
            system_id=m.drawer_system,
            height_key=m.drawer_height_key,
        )

        lines: list[BomLine] = []
        for part in raw_parts:
            lines.append(
                BomLine(
                    part_name=part.name,
                    width_mm=part.w,
                    height_mm=part.h,
                    thickness_mm=part.t,
                    quantity=m.num_drawers,
                    group=part.group,  # type: ignore[arg-type]
                )
            )
        return lines

    # --- drzwi ---

    def _door_parts(self, m: TechModule) -> list[BomLine]:
        if not m.has_door:
            return []
        t = m.material_thickness_mm
        door_w = (m.width_mm / m.num_doors) + 4  # 2mm nałożenia z każdej strony
        door_h = m.height_mm + 4
        return [
            BomLine(
                "Drzwi",
                door_w,
                door_h,
                t,
                m.num_doors,
                "door",
                "abs_2mm",
            )
        ]

    # --- okucia (tylko metadane — bez kosztu) ---

    def _hardware_lines(self, m: TechModule) -> list[BomLine]:
        lines: list[BomLine] = []

        # Zawiasy
        if m.has_door:
            hinges = self._count_hinges(m.height_mm)
            lines.append(
                BomLine("Zawias 35mm", 0, 0, 0, hinges * m.num_doors, "hardware")
            )

        # Prowadnice szuflad
        if m.num_drawers > 0:
            inp = DrawerCalcInput(depth_mm=m.depth_mm)
            slide_len = pick_slide_length_mm(inp)
            lines.append(
                BomLine(
                    f"Prowadnica {slide_len}mm",
                    0, 0, 0,
                    m.num_drawers * 2,   # para
                    "hardware",
                )
            )

        # Kołki półkowe
        if m.num_shelves > 0:
            lines.append(
                BomLine(
                    "Kołek półkowy Ø5",
                    0, 0, 0,
                    m.num_shelves * SHELF_PINS_PER_SHELF,
                    "hardware",
                )
            )

        return lines

    def _count_hinges(self, door_height_mm: float) -> int:
        return hinges_count_for_door(door_height_mm)

    # --- wycena ---

    def calculate_price(self, bom: list[BomLine]) -> Decimal:
        """
        TODO: podpiąć rzeczywisty cennik z material_store_json.py.
        Aktualnie zwraca sumę unit_cost (domyślnie 0).
        """
        return sum((line.total_cost for line in bom), Decimal("0.00"))
