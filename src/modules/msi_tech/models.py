"""
Modele domenowe MSI Tech Module.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

# Grupy formatek w BOM
PartGroup = Literal[
    "carcass",          # korpus: boki, góra, dno
    "back",             # plecy HDF/MDF
    "shelf",            # półki
    "door",             # drzwi
    "drawer_bottom",    # dno szuflady
    "drawer_rear",      # plecy szuflady
    "hardware",         # okucia (zawiasy, prowadnice)
    "other",
]


@dataclass
class TechModule:
    """Parametry wejściowe modułu meblowego."""
    id: str
    name: str

    # Wymiary zewnętrzne [mm]
    width_mm: float
    height_mm: float
    depth_mm: float

    # Materiał
    material_thickness_mm: float = 18.0
    back_thickness_mm: float = 3.0         # HDF plecy

    # Zawartość
    num_drawers: int = 0
    drawer_system: str = "blum_antaro"
    drawer_height_key: str = "M"           # N/M/K/C/F dla Blum

    num_shelves: int = 1
    has_door: bool = False
    door_type: str = "overlay"             # overlay / inset / half_overlay
    num_doors: int = 1

    # TODO: dodać obsługę mechanizmów górnounoszących (lifts.py)
    has_lift: bool = False

    # Okleinowanie
    edge_banding_front: str = "abs_2mm"    # abs_2mm / cpl_045 / none
    edge_banding_visible: str = "abs_2mm"

    # Metadane
    notes: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class PartSpec:
    """Specyfikacja pojedynczej formatki."""
    name: str
    width_mm: float
    height_mm: float
    thickness_mm: float
    quantity: int = 1
    group: PartGroup = "other"
    edge_front: bool = False
    edge_back: bool = False
    edge_left: bool = False
    edge_right: bool = False


@dataclass
class BomLine:
    """Linia listy materiałów (Bill of Materials)."""
    part_name: str
    width_mm: float
    height_mm: float
    thickness_mm: float
    quantity: int
    group: PartGroup
    edge_banding: str = ""

    # TODO: uzupełnić po integracji z cennikiem (material_store_json.py)
    unit_cost: Decimal = field(default_factory=lambda: Decimal("0.00"))

    @property
    def area_m2(self) -> float:
        return round(self.width_mm * self.height_mm / 1_000_000 * self.quantity, 4)

    @property
    def total_cost(self) -> Decimal:
        return self.unit_cost * self.quantity
