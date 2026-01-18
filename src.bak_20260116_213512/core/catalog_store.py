from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .materials_store import MaterialSpec, EdgeSpec, FittingSpec


@dataclass
class BoardSpec:
    """
    Płyta / płyta meblowa (stara struktura – zostawiamy, bo może Ci się przydać).
    Jeśli nie potrzebujesz osobno BoardSpec, później możemy to zmerge'ować z MaterialSpec.
    """
    name: str
    thickness_mm: float
    price_per_m2: float
    currency: str = "PLN"


@dataclass
class CatalogStore:
    """
    Wspólny magazyn słowników/parametrów.
    Inne zakładki czytają dane stąd (get_*), a edycja odbywa się w zakładce bazy.
    """

    # (legacy / opcjonalne)
    boards: List[BoardSpec] = field(default_factory=list)

    # NOWE wspólne bazy:
    materials: List[MaterialSpec] = field(default_factory=list)
    edges: List[EdgeSpec] = field(default_factory=list)
    fittings: List[FittingSpec] = field(default_factory=list)

    # ---------- Boards ----------
    def get_boards(self) -> List[BoardSpec]:
        return list(self.boards)

    def set_boards(self, items: List[BoardSpec]) -> None:
        self.boards = list(items)

    # ---------- Materials ----------
    def get_materials(self) -> List[MaterialSpec]:
        return list(self.materials)

    def set_materials(self, items: List[MaterialSpec]) -> None:
        self.materials = list(items)

    # ---------- Edges ----------
    def get_edges(self) -> List[EdgeSpec]:
        return list(self.edges)

    def set_edges(self, items: List[EdgeSpec]) -> None:
        self.edges = list(items)

    # ---------- Fittings ----------
    def get_fittings(self) -> List[FittingSpec]:
        return list(self.fittings)

    def set_fittings(self, items: List[FittingSpec]) -> None:
        self.fittings = list(items)
