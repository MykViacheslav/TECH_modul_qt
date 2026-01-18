from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MaterialSpec:
    """
    Materiał bazowy (płyta, MDF, sklejka, HPL, itp.)
    price_unit: np. m2, szt, mb
    """
    name: str
    category: str                # np. "Płyta", "MDF", "Sklejka", "HPL"
    thickness_mm: float
    price: float                 # cena za unit
    unit: str = "m²"
    currency: str = "PLN"


@dataclass
class EdgeSpec:
    """
    Krawędź / okleina (ABS, fornir, itp.)
    """
    name: str
    thickness_mm: float
    height_mm: float
    price_per_mb: float
    currency: str = "PLN"


@dataclass
class FittingSpec:
    """
    Okucie (zawias, prowadnica, podnośnik, łącznik, itp.)
    """
    name: str
    category: str                # np. "Zawias", "Prowadnica", "Podnośnik"
    price_per_piece: float
    currency: str = "PLN"
